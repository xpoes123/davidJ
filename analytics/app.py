"""Minimal analytics for djiang.xyz.

Stores events in SQLite. Exposes:
  POST /event      record any event (pageview, duration, scroll, cube_click, label_click)
  GET  /stats      aggregate stats for the dashboard
  GET  /recent     recent event feed
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

DB_PATH = os.environ.get("ANALYTICS_DB", "analytics.db")
ALLOWED_ORIGINS = os.environ.get("ANALYTICS_ORIGINS", "https://djiang.xyz,http://localhost:4747").split(",")


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                ts INTEGER NOT NULL,
                sid TEXT,
                type TEXT NOT NULL,
                page TEXT,
                ref TEXT,
                ua TEXT,
                ip_hash TEXT,
                data TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_ts ON events(ts)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sid ON events(sid)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_type ON events(type)")


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


init_db()

app = FastAPI(title="davidJ analytics")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class Event(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    sid: str
    page: str
    ref: Optional[str] = ""
    ts: int


@app.post("/event")
async def record(event: Event, request: Request) -> dict[str, bool]:
    ua = (request.headers.get("user-agent") or "")[:240]
    # x-forwarded-for set by Caddy; first IP in the chain
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else ""

    known = {"type", "sid", "page", "ref", "ts"}
    extras: dict[str, Any] = {k: v for k, v in event.model_dump().items() if k not in known}
    data_json = json.dumps(extras) if extras else None

    with _conn() as c:
        c.execute(
            "INSERT INTO events (ts, sid, type, page, ref, ua, ip_hash, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (event.ts, event.sid, event.type, event.page, event.ref or "", ua, ip_hash, data_json),
        )
    return {"ok": True}


@app.get("/stats")
async def stats() -> dict[str, Any]:
    now = int(time.time() * 1000)
    day = 24 * 60 * 60 * 1000

    with _conn() as c:
        def count(where: str, args: tuple = ()) -> int:
            return c.execute(f"SELECT COUNT(*) FROM events WHERE {where}", args).fetchone()[0]

        total_pv = count("type='pageview'")
        unique_sid = c.execute("SELECT COUNT(DISTINCT sid) FROM events").fetchone()[0]
        unique_ip = c.execute("SELECT COUNT(DISTINCT ip_hash) FROM events WHERE ip_hash != ''").fetchone()[0]
        pv_24h = count("type='pageview' AND ts > ?", (now - day,))
        pv_7d = count("type='pageview' AND ts > ?", (now - 7 * day,))
        pv_30d = count("type='pageview' AND ts > ?", (now - 30 * day,))

        # Top pages
        top_pages = [dict(r) for r in c.execute(
            "SELECT page, COUNT(*) AS views FROM events WHERE type='pageview' GROUP BY page ORDER BY views DESC LIMIT 25"
        )]

        # Top referrers (non-empty, exclude self-referrers from our own domain)
        top_referrers = [dict(r) for r in c.execute(
            """SELECT ref, COUNT(*) AS count FROM events
               WHERE type='pageview' AND ref != '' AND ref NOT LIKE '%djiang.xyz%'
               GROUP BY ref ORDER BY count DESC LIMIT 15"""
        )]

        # Cube clicks (decode data JSON's `cube` field)
        cube_clicks = [dict(r) for r in c.execute(
            """SELECT json_extract(data, '$.cube') AS cube,
                      json_extract(data, '$.stack') AS stack,
                      COUNT(*) AS count
               FROM events WHERE type='cube_click' AND data IS NOT NULL
               GROUP BY cube ORDER BY count DESC LIMIT 30"""
        )]

        # Label clicks
        label_clicks = [dict(r) for r in c.execute(
            """SELECT json_extract(data, '$.stack') AS stack, COUNT(*) AS count
               FROM events WHERE type='label_click' AND data IS NOT NULL
               GROUP BY stack ORDER BY count DESC"""
        )]

        # Average and median duration per page (in seconds)
        duration_per_page = [dict(r) for r in c.execute(
            """SELECT page,
                      AVG(CAST(json_extract(data, '$.ms') AS REAL))/1000.0 AS avg_sec,
                      MAX(CAST(json_extract(data, '$.ms') AS REAL))/1000.0 AS max_sec,
                      COUNT(*) AS samples
               FROM events WHERE type='duration' AND data IS NOT NULL
               GROUP BY page ORDER BY samples DESC LIMIT 25"""
        )]

        # Average scroll depth per page (only for content pages)
        scroll_per_page = [dict(r) for r in c.execute(
            """SELECT page,
                      AVG(CAST(json_extract(data, '$.scroll') AS REAL)) AS avg_scroll,
                      COUNT(*) AS samples
               FROM events WHERE type='duration'
                 AND CAST(json_extract(data, '$.scroll') AS REAL) > 0
                 AND (page LIKE '%post.html%' OR page LIKE '%book.html%')
               GROUP BY page ORDER BY samples DESC LIMIT 25"""
        )]

        # Hourly pageviews for last 7 days (for sparkline)
        hourly = [dict(r) for r in c.execute(
            """SELECT (ts / (1000 * 60 * 60)) * (1000 * 60 * 60) AS hour, COUNT(*) AS views
               FROM events WHERE type='pageview' AND ts > ?
               GROUP BY hour ORDER BY hour""",
            (now - 7 * day,),
        )]

    return {
        "total_pageviews": total_pv,
        "unique_visitors": unique_sid,
        "unique_ips": unique_ip,
        "pv_24h": pv_24h,
        "pv_7d": pv_7d,
        "pv_30d": pv_30d,
        "top_pages": top_pages,
        "top_referrers": top_referrers,
        "cube_clicks": cube_clicks,
        "label_clicks": label_clicks,
        "duration_per_page": duration_per_page,
        "scroll_per_page": scroll_per_page,
        "hourly": hourly,
    }


@app.get("/recent")
async def recent(limit: int = 100) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, type, page, ref, sid, data FROM events ORDER BY ts DESC LIMIT ?",
            (min(limit, 500),),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

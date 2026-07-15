"""Minimal analytics for djiang.xyz.

Stores events in SQLite. Exposes:
  POST /event      record any event (pageview, duration, scroll, cube_click, label_click)
  GET  /stats      aggregate stats for the dashboard
  GET  /sessions   recent sessions with event timelines
  GET  /recent     recent event feed
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Iterator, Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

DB_PATH = os.environ.get("ANALYTICS_DB", "analytics.db")
ALLOWED_ORIGINS = os.environ.get("ANALYTICS_ORIGINS", "https://djiang.xyz,http://localhost:4747").split(",")

_geo_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _geo_client
    _geo_client = httpx.AsyncClient(timeout=2.0)
    yield
    await _geo_client.aclose()


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

        # Geo columns — added later; safe to run every startup
        for col in ("geo_country TEXT", "geo_city TEXT", "geo_org TEXT"):
            try:
                c.execute(f"ALTER TABLE events ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass

        c.execute(
            """CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                ts INTEGER NOT NULL,
                source TEXT,
                ip_hash TEXT,
                ua TEXT,
                confirmed INTEGER DEFAULT 1
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub_ts ON subscribers(ts)")


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


async def lookup_geo(ip: str) -> dict[str, str]:
    if not ip or ip in ("127.0.0.1", "::1") or not _geo_client:
        return {}
    try:
        r = await _geo_client.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,org")
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                return {
                    "country": d.get("country") or "",
                    "city": d.get("city") or "",
                    "org": d.get("org") or "",
                }
    except Exception:
        pass
    return {}


init_db()

app = FastAPI(title="davidJ analytics", lifespan=lifespan)
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
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else ""

    geo = await lookup_geo(ip)

    known = {"type", "sid", "page", "ref", "ts"}
    extras: dict[str, Any] = {k: v for k, v in event.model_dump().items() if k not in known}
    data_json = json.dumps(extras) if extras else None

    with _conn() as c:
        c.execute(
            """INSERT INTO events
               (ts, sid, type, page, ref, ua, ip_hash, data, geo_country, geo_city, geo_org)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.ts, event.sid, event.type, event.page, event.ref or "",
                ua, ip_hash, data_json,
                geo.get("country"), geo.get("city"), geo.get("org"),
            ),
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

        top_pages = [dict(r) for r in c.execute(
            "SELECT page, COUNT(*) AS views FROM events WHERE type='pageview' GROUP BY page ORDER BY views DESC LIMIT 25"
        )]

        top_referrers = [dict(r) for r in c.execute(
            """SELECT ref, COUNT(*) AS count FROM events
               WHERE type='pageview' AND ref != '' AND ref NOT LIKE '%djiang.xyz%'
               GROUP BY ref ORDER BY count DESC LIMIT 15"""
        )]

        cube_clicks = [dict(r) for r in c.execute(
            """SELECT json_extract(data, '$.cube') AS cube,
                      json_extract(data, '$.stack') AS stack,
                      COUNT(*) AS count
               FROM events WHERE type='cube_click' AND data IS NOT NULL
               GROUP BY cube ORDER BY count DESC LIMIT 30"""
        )]

        label_clicks = [dict(r) for r in c.execute(
            """SELECT json_extract(data, '$.stack') AS stack, COUNT(*) AS count
               FROM events WHERE type='label_click' AND data IS NOT NULL
               GROUP BY stack ORDER BY count DESC"""
        )]

        duration_per_page = [dict(r) for r in c.execute(
            """SELECT page,
                      AVG(CAST(json_extract(data, '$.ms') AS REAL))/1000.0 AS avg_sec,
                      MAX(CAST(json_extract(data, '$.ms') AS REAL))/1000.0 AS max_sec,
                      COUNT(*) AS samples
               FROM events WHERE type='duration' AND data IS NOT NULL
               GROUP BY page ORDER BY samples DESC LIMIT 25"""
        )]

        scroll_per_page = [dict(r) for r in c.execute(
            """SELECT page,
                      AVG(CAST(json_extract(data, '$.scroll') AS REAL)) AS avg_scroll,
                      COUNT(*) AS samples
               FROM events WHERE type='duration'
                 AND CAST(json_extract(data, '$.scroll') AS REAL) > 0
                 AND (page LIKE '%post.html%' OR page LIKE '%book.html%')
               GROUP BY page ORDER BY samples DESC LIMIT 25"""
        )]

        hourly = [dict(r) for r in c.execute(
            """SELECT (ts / (1000 * 60 * 60)) * (1000 * 60 * 60) AS hour, COUNT(*) AS views
               FROM events WHERE type='pageview' AND ts > ?
               GROUP BY hour ORDER BY hour""",
            (now - 7 * day,),
        )]

        top_countries = [dict(r) for r in c.execute(
            """SELECT geo_country AS country, COUNT(DISTINCT ip_hash) AS visitors, COUNT(*) AS pageviews
               FROM events WHERE type='pageview' AND geo_country IS NOT NULL AND geo_country != ''
               GROUP BY geo_country ORDER BY visitors DESC LIMIT 15"""
        )]

        top_cities = [dict(r) for r in c.execute(
            """SELECT geo_city AS city, geo_country AS country,
                      COUNT(DISTINCT ip_hash) AS visitors, COUNT(*) AS pageviews
               FROM events WHERE type='pageview' AND geo_city IS NOT NULL AND geo_city != ''
               GROUP BY geo_city ORDER BY visitors DESC LIMIT 15"""
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
        "top_countries": top_countries,
        "top_cities": top_cities,
    }


@app.get("/sessions")
async def sessions(limit: int = 30) -> list[dict[str, Any]]:
    """Recent sessions with their full event timelines."""
    with _conn() as c:
        sids = [r[0] for r in c.execute(
            """SELECT sid FROM events WHERE sid IS NOT NULL AND sid != ''
               GROUP BY sid ORDER BY MAX(ts) DESC LIMIT ?""",
            (max(1, min(limit, 100)),),
        ).fetchall()]

        result = []
        for sid in sids:
            evts = [dict(r) for r in c.execute(
                """SELECT ts, type, page, ref, ua, geo_country, geo_city, geo_org, data
                   FROM events WHERE sid = ? ORDER BY ts""",
                (sid,),
            ).fetchall()]
            if not evts:
                continue
            first = evts[0]
            result.append({
                "sid": sid[:8],
                "first_ts": first["ts"],
                "last_ts": evts[-1]["ts"],
                "country": first.get("geo_country") or "",
                "city": first.get("geo_city") or "",
                "org": first.get("geo_org") or "",
                "ua": first.get("ua") or "",
                "ref": first.get("ref") or "",
                "events": [
                    {
                        "ts": e["ts"],
                        "type": e["type"],
                        "page": e["page"],
                        "data": e["data"],
                    }
                    for e in evts
                ],
            })
    return result


@app.get("/recent")
async def recent(limit: int = 100) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, type, page, ref, sid, data FROM events ORDER BY ts DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Email subscriptions ---

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class Subscribe(BaseModel):
    email: str
    source: Optional[str] = ""


@app.post("/subscribe")
async def subscribe(s: Subscribe, request: Request) -> dict[str, Any]:
    email = s.email.strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        return {"ok": False, "msg": "Looks like that email isn't quite right."}

    ua = (request.headers.get("user-agent") or "")[:240]
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else ""
    now = int(time.time() * 1000)

    with _conn() as c:
        existing = c.execute("SELECT id FROM subscribers WHERE email = ?", (email,)).fetchone()
        if existing:
            return {"ok": True, "msg": "You're already on the list. Welcome back."}
        c.execute(
            "INSERT INTO subscribers (email, ts, source, ip_hash, ua) VALUES (?, ?, ?, ?, ?)",
            (email, now, s.source or "", ip_hash, ua),
        )
    return {"ok": True, "msg": "Thanks — you're on the list."}


@app.get("/subscribers")
async def subscribers_count() -> dict[str, Any]:
    """Aggregate subscriber stats (no PII)."""
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        recent_rows = c.execute(
            "SELECT ts, source FROM subscribers ORDER BY ts DESC LIMIT 20"
        ).fetchall()
    return {
        "total": total,
        "recent": [{"ts": r["ts"], "source": r["source"]} for r in recent_rows],
    }


# --- external stat proxies for the /me page --------------------------------
# WCA blocks cross-origin requests, and Last.fm needs a server-side key, so the
# browser can't call them directly. Small in-memory TTL cache keeps us well under
# any rate limits (the page is low-traffic).
_proxy_cache: dict[str, tuple[float, Any]] = {}


async def _cached_get(key: str, url: str, ttl: float, params: Optional[dict] = None) -> Any:
    now = time.time()
    hit = _proxy_cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "davidj-stats/1.0"}) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    _proxy_cache[key] = (now, data)
    return data


# These proxies exist only to feed the /me page, so they serve exactly one
# identifier each — an allowlist, not arbitrary user input. That bounds the
# cache to a handful of keys and prevents using them to amplify outbound
# requests to arbitrary WCA/Last.fm resources.
WCA_ID = "2016JIAN13"


@app.get("/wca/{wca_id}")
async def wca(wca_id: str) -> Any:
    if wca_id != WCA_ID:
        return {"error": "not found"}
    try:
        return await _cached_get(
            f"wca:{wca_id}",
            f"https://www.worldcubeassociation.org/api/v0/persons/{wca_id}",
            ttl=6 * 3600,
        )
    except Exception:
        return {"error": "wca fetch failed"}


LASTFM_KEY = os.environ.get("LASTFM_API_KEY", "")
LASTFM_USER = "xpoes"


@app.get("/lastfm/{user}")
async def lastfm(user: str) -> Any:
    if not LASTFM_KEY:
        return {"disabled": True}
    if user != LASTFM_USER:
        return {"error": "not found"}
    base = "https://ws.audioscrobbler.com/2.0/"
    common = {"api_key": LASTFM_KEY, "format": "json", "user": user}
    try:
        recent = await _cached_get(
            f"lfm:recent:{user}", base, ttl=120,
            params={**common, "method": "user.getrecenttracks", "limit": 5})
        top = await _cached_get(
            f"lfm:top:{user}", base, ttl=3600,
            params={**common, "method": "user.gettopartists", "period": "1month", "limit": 5})
    except Exception:
        return {"error": "lastfm fetch failed"}
    rt = (recent.get("recenttracks", {}) or {}).get("track", [])
    if isinstance(rt, dict):
        rt = [rt]
    ta = (top.get("topartists", {}) or {}).get("artist", [])
    return {
        "recent": [{
            "name": t.get("name"),
            "artist": (t.get("artist") or {}).get("#text"),
            "nowplaying": (t.get("@attr") or {}).get("nowplaying") == "true",
        } for t in rt],
        "top_artists": [{"name": a.get("name"), "playcount": a.get("playcount")} for a in ta],
    }

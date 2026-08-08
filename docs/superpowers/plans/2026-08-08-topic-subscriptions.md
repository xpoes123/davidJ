# Topic Subscriptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let visitors subscribe to per-topic email lists (double opt-in) and let David send newsletters to those lists from the existing analytics backend.

**Architecture:** Extend `analytics/app.py` (FastAPI + SQLite, runs on `localhost:8001`, Caddy-proxied at `/api/analytics/*`). Add topics, a subscriptions junction table, double-opt-in tokens, confirm/unsubscribe pages, and a token-gated send endpoint that delivers via the Resend HTTP API over the existing `httpx` dep. Frontend: a `subscribe.html` hub plus contextual forms on writing pages.

**Tech Stack:** Python 3.12, FastAPI, SQLite (stdlib `sqlite3`), `httpx` (already a dep), `secrets` (stdlib), Resend HTTP API. Static HTML/CSS/JS for the frontend. `pytest` for tests.

## Global Constraints

- Timestamps are epoch **milliseconds**: `int(time.time() * 1000)` (matches existing rows).
- DB access only via the existing `_conn()` context manager; migrations use the `ALTER TABLE … except sqlite3.OperationalError` pattern already in `init_db()`.
- Endpoint responses stay **non-enumerating**: never reveal whether an email/token exists; reuse the existing friendly `{"ok": bool, "msg": str}` shape for `/subscribe`.
- Email regex: reuse existing `EMAIL_RE`; max email length 254.
- Fail closed: if `RESEND_API_KEY` is unset, sending is refused with a clear message but signups are still recorded.
- Topic ids (the ONE canonical list): `sciencebowl, sports, games, markets, writing, music, content, everything`. `everything` subscribers are included in every send.
- Frontend API base: `location.hostname` local → `http://localhost:8001/<path>`, else `/api/analytics/<path>` (existing pattern in `analytics.js` and `post.html`).
- Site base URL for links: `SITE_URL` env, default `https://djiang.xyz`. Confirm/unsub links point at `${SITE_URL}/api/analytics/confirm|unsubscribe?token=…`.
- Commit after every task. No new pip dependency (Resend is called over `httpx`).

---

### Task 1: Topics constant + DB migration

**Files:**
- Modify: `analytics/app.py` (add topics constant; extend `init_db()`)
- Test: `analytics/test_subscriptions.py` (new)

**Interfaces:**
- Produces: `TOPICS: list[tuple[str,str,str]]`, `TOPIC_IDS: set[str]`; tables `subscriptions(email,topic,ts)`, `campaigns(id,topic,subject,sent_ts,n)`; columns `subscribers.confirm_token`, `subscribers.unsub_token`.

- [ ] **Step 1: Write the failing test**

```python
# analytics/test_subscriptions.py
import importlib, os, sqlite3, tempfile

def _fresh_app():
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd)
    os.environ["ANALYTICS_DB"] = path
    os.environ["STATS_TOKEN"] = "testtoken"
    import analytics.app as app
    importlib.reload(app)
    return app, path

def test_migration_creates_tables_and_columns():
    app, path = _fresh_app()
    c = sqlite3.connect(path)
    cols = {r[1] for r in c.execute("PRAGMA table_info(subscribers)")}
    assert {"confirm_token", "unsub_token"} <= cols
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"subscriptions", "campaigns"} <= tables
    assert app.TOPIC_IDS == {"sciencebowl","sports","games","markets","writing","music","content","everything"}
    c.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd analytics && python -m pytest test_subscriptions.py::test_migration_creates_tables_and_columns -v`
Expected: FAIL (`AttributeError: module 'analytics.app' has no attribute 'TOPIC_IDS'`)

- [ ] **Step 3: Add topics constant near the top of `app.py`** (after the `STATS_TOKEN` line, ~line 30)

```python
# Canonical subscribe topics: (id, label, blurb). Mirrored in subscribe.html.
TOPICS = [
    ("sciencebowl", "Science Bowl",        "SciBowl.Live, LeBot, NSBA"),
    ("sports",      "Sports Betting",       "SharpLab, CLV, odds & quant lab"),
    ("games",       "Games",                "games.djiang.xyz, card-game builds"),
    ("markets",     "Markets / Prediction", "Vigil, NSBA Markets, Kalshi work"),
    ("writing",     "Writing / Essays",     "new posts & essays"),
    ("music",       "Music",                "albums, playlists, scrobble notes"),
    ("content",     "Content / Making",     "videos, streams, share.djiang.xyz drops"),
    ("everything",  "Everything",           "just email me when I do anything"),
]
TOPIC_IDS = {t[0] for t in TOPICS}
SITE_URL = os.environ.get("SITE_URL", "https://djiang.xyz")
```

- [ ] **Step 4: Extend `init_db()`** — inside the `with _conn() as c:` block, after the existing `subscribers` table/index creation, add:

```python
        for col in ("confirm_token TEXT", "unsub_token TEXT"):
            try:
                c.execute(f"ALTER TABLE subscribers ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass
        c.execute(
            """CREATE TABLE IF NOT EXISTS subscriptions (
                email TEXT NOT NULL,
                topic TEXT NOT NULL,
                ts INTEGER NOT NULL,
                UNIQUE(email, topic)
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_subx_topic ON subscriptions(topic)")
        c.execute(
            """CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                subject TEXT,
                sent_ts INTEGER NOT NULL,
                n INTEGER NOT NULL
            )"""
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd analytics && python -m pytest test_subscriptions.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add analytics/app.py analytics/test_subscriptions.py
git commit -m "feat(subscribe): topics constant + subscriptions/campaigns migration"
```

---

### Task 2: Rewrite `/subscribe` for topics + double opt-in

**Files:**
- Modify: `analytics/app.py` (replace the `Subscribe` model + `subscribe()` handler, ~lines 414-439)
- Test: `analytics/test_subscriptions.py`

**Interfaces:**
- Consumes: `TOPIC_IDS`, `EMAIL_RE`, `_conn`.
- Produces: `POST /subscribe {email, topics: list[str], source}` → `{ok, msg}`; new subscribers get `confirmed=0`, a `confirm_token`, a stable `unsub_token`, and rows in `subscriptions`. Helper `_send_confirmation(email, token)` is defined in Task 3 (import-safe stub allowed until then).

- [ ] **Step 1: Write the failing test**

```python
def test_subscribe_creates_pending_subscriber_and_topics(monkeypatch):
    app, path = _fresh_app()
    monkeypatch.setattr(app, "_send_confirmation", lambda *a, **k: None)
    from fastapi.testclient import TestClient
    client = TestClient(app.app)
    r = client.post("/subscribe", json={"email": "A@X.com", "topics": ["games", "bogus", "everything"]})
    assert r.json()["ok"] is True
    c = __import__("sqlite3").connect(path)
    row = c.execute("SELECT email, confirmed, unsub_token, confirm_token FROM subscribers").fetchone()
    assert row[0] == "a@x.com" and row[1] == 0 and row[2] and row[3]
    topics = {t[0] for t in c.execute("SELECT topic FROM subscriptions WHERE email='a@x.com'")}
    assert topics == {"games", "everything"}   # bogus dropped
    c.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd analytics && python -m pytest test_subscriptions.py::test_subscribe_creates_pending_subscriber_and_topics -v`
Expected: FAIL (topics not stored / attribute error)

- [ ] **Step 3: Add `import secrets` at the top of `app.py`** (with the other stdlib imports).

- [ ] **Step 4: Replace the `Subscribe` model and `subscribe()` handler**

```python
class Subscribe(BaseModel):
    email: str
    topics: list[str] = []
    source: Optional[str] = ""


def _upsert_subscription(c, email: str, topic: str, now: int) -> None:
    c.execute(
        "INSERT OR IGNORE INTO subscriptions (email, topic, ts) VALUES (?, ?, ?)",
        (email, topic, now),
    )


@app.post("/subscribe")
async def subscribe(s: Subscribe, request: Request) -> dict[str, Any]:
    email = s.email.strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        return {"ok": False, "msg": "Looks like that email isn't quite right."}
    topics = [t for t in s.topics if t in TOPIC_IDS] or ["everything"]

    ua = (request.headers.get("user-agent") or "")[:240]
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else ""
    now = int(time.time() * 1000)

    with _conn() as c:
        row = c.execute(
            "SELECT confirmed, confirm_token, unsub_token FROM subscribers WHERE email = ?",
            (email,),
        ).fetchone()
        if row is None:
            confirm_token = secrets.token_urlsafe(24)
            unsub_token = secrets.token_urlsafe(24)
            c.execute(
                "INSERT INTO subscribers (email, ts, source, ip_hash, ua, confirmed, confirm_token, unsub_token) "
                "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
                (email, now, s.source or "", ip_hash, ua, confirm_token, unsub_token),
            )
            for t in topics:
                _upsert_subscription(c, email, t, now)
            already_confirmed = False
        else:
            already_confirmed = bool(row["confirmed"])
            confirm_token = row["confirm_token"] or secrets.token_urlsafe(24)
            if not row["unsub_token"]:
                c.execute("UPDATE subscribers SET unsub_token = ? WHERE email = ?",
                          (secrets.token_urlsafe(24), email))
            if not row["confirm_token"]:
                c.execute("UPDATE subscribers SET confirm_token = ? WHERE email = ?",
                          (confirm_token, email))
            for t in topics:
                _upsert_subscription(c, email, t, now)

    if already_confirmed:
        return {"ok": True, "msg": "Added those topics — you're all set."}
    _send_confirmation(email, confirm_token)
    return {"ok": True, "msg": "Almost there — check your inbox to confirm."}
```

- [ ] **Step 5: Add a temporary stub** so the module imports before Task 3 (place above the handler; Task 3 replaces its body):

```python
def _send_confirmation(email: str, token: str) -> None:
    pass  # implemented in Task 3
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd analytics && python -m pytest test_subscriptions.py -v`
Expected: PASS (both tests)

- [ ] **Step 7: Commit**

```bash
git add analytics/app.py analytics/test_subscriptions.py
git commit -m "feat(subscribe): topic-aware double-opt-in signup"
```

---

### Task 3: Resend email helper + confirmation email

**Files:**
- Modify: `analytics/app.py` (add `send_email` + real `_send_confirmation`)
- Test: `analytics/test_subscriptions.py`

**Interfaces:**
- Consumes: `SITE_URL`, `httpx`.
- Produces: `send_email(to: str, subject: str, html: str, list_unsub: str | None = None) -> bool`; `_send_confirmation(email, token)` posts a confirm email. Reads `RESEND_API_KEY`, `MAIL_FROM` (default `David <david@djiang.xyz>`).

- [ ] **Step 1: Write the failing test**

```python
def test_send_email_posts_to_resend(monkeypatch):
    app, _ = _fresh_app()
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    import analytics.app as a; import importlib; importlib.reload(a)
    calls = {}
    class FakeResp:
        status_code = 200
        def json(self): return {"id": "x"}
    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json=None, headers=None):
            calls["url"] = url; calls["json"] = json; calls["headers"] = headers
            return FakeResp()
    monkeypatch.setattr(a.httpx, "Client", FakeClient)
    ok = a.send_email("z@y.com", "Hi", "<p>hi</p>", list_unsub="https://djiang.xyz/u?token=t")
    assert ok is True
    assert calls["url"] == "https://api.resend.com/emails"
    assert calls["json"]["to"] == ["z@y.com"]
    assert "List-Unsubscribe" in calls["headers"]

def test_send_email_fails_closed_without_key(monkeypatch):
    app, _ = _fresh_app()
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    import analytics.app as a; import importlib; importlib.reload(a)
    assert a.send_email("z@y.com", "Hi", "<p>hi</p>") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd analytics && python -m pytest test_subscriptions.py::test_send_email_posts_to_resend -v`
Expected: FAIL (`send_email` not defined)

- [ ] **Step 3: Add the mail config + helper** (near the topics constant)

```python
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "David <david@djiang.xyz>")


def send_email(to: str, subject: str, html: str, list_unsub: Optional[str] = None) -> bool:
    """Send one email via Resend. Returns False (and sends nothing) if unconfigured."""
    if not RESEND_API_KEY:
        return False
    headers = {"Authorization": f"Bearer {RESEND_API_KEY}"}
    if list_unsub:
        headers["List-Unsubscribe"] = f"<{list_unsub}>"
        headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    payload = {"from": MAIL_FROM, "to": [to], "subject": subject, "html": html}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post("https://api.resend.com/emails", json=payload, headers=headers)
            return r.status_code < 300
    except Exception:
        return False
```

- [ ] **Step 4: Replace the `_send_confirmation` stub with the real body**

```python
def _send_confirmation(email: str, token: str) -> None:
    link = f"{SITE_URL}/api/analytics/confirm?token={token}"
    html = (
        f"<p>Thanks for subscribing to David Jiang's updates.</p>"
        f"<p><a href=\"{link}\">Confirm your subscription</a> to start receiving emails.</p>"
        f"<p style=\"color:#888;font-size:12px\">If you didn't request this, ignore this email — "
        f"nothing happens without confirmation.</p>"
    )
    send_email(email, "Confirm your subscription", html)
```

- [ ] **Step 5: Run tests**

Run: `cd analytics && python -m pytest test_subscriptions.py -v`
Expected: PASS (all)

- [ ] **Step 6: Commit**

```bash
git add analytics/app.py analytics/test_subscriptions.py
git commit -m "feat(subscribe): Resend email helper + confirmation email"
```

---

### Task 4: `/confirm` endpoint + confirmed page

**Files:**
- Modify: `analytics/app.py` (add `_page()` helper + `/confirm`)
- Test: `analytics/test_subscriptions.py`

**Interfaces:**
- Produces: `GET /confirm?token=` → `HTMLResponse`; single-use (clears `confirm_token`, sets `confirmed=1`). Helper `_page(title, body) -> HTMLResponse`.

- [ ] **Step 1: Write the failing test**

```python
def test_confirm_flips_confirmed_and_is_single_use(monkeypatch):
    app, path = _fresh_app()
    monkeypatch.setattr(app, "_send_confirmation", lambda *a, **k: None)
    from fastapi.testclient import TestClient
    client = TestClient(app.app)
    client.post("/subscribe", json={"email": "c@x.com", "topics": ["writing"]})
    import sqlite3; c = sqlite3.connect(path)
    tok = c.execute("SELECT confirm_token FROM subscribers WHERE email='c@x.com'").fetchone()[0]
    c.close()
    r1 = client.get(f"/confirm?token={tok}")
    assert r1.status_code == 200 and "confirmed" in r1.text.lower()
    c = sqlite3.connect(path)
    row = c.execute("SELECT confirmed, confirm_token FROM subscribers WHERE email='c@x.com'").fetchone()
    assert row[0] == 1 and (row[1] is None or row[1] == "")
    c.close()
    r2 = client.get(f"/confirm?token={tok}")   # reused → expired
    assert "expired" in r2.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd analytics && python -m pytest test_subscriptions.py::test_confirm_flips_confirmed_and_is_single_use -v`
Expected: FAIL (404, no `/confirm`)

- [ ] **Step 3: Add `from fastapi.responses import HTMLResponse`** to the imports.

- [ ] **Step 4: Add the page helper + endpoint**

```python
def _page(title: str, body: str) -> HTMLResponse:
    html = (
        f"<!doctype html><html><head><meta charset=utf-8>"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title><style>"
        f"body{{background:#14131a;color:#e8e3d8;font-family:system-ui,sans-serif;"
        f"display:grid;place-items:center;height:100vh;margin:0;text-align:center}}"
        f"a{{color:#d4a955}} .box{{max-width:460px;padding:24px}}</style></head>"
        f"<body><div class=box><h1>{title}</h1>{body}"
        f"<p><a href='{SITE_URL}'>← djiang.xyz</a></p></div></body></html>"
    )
    return HTMLResponse(html)


@app.get("/confirm")
async def confirm(token: str = Query(default="")) -> HTMLResponse:
    if token:
        with _conn() as c:
            row = c.execute("SELECT email FROM subscribers WHERE confirm_token = ?", (token,)).fetchone()
            if row:
                c.execute(
                    "UPDATE subscribers SET confirmed = 1, confirm_token = NULL WHERE confirm_token = ?",
                    (token,),
                )
                return _page("You're confirmed", "<p>You'll get emails on the topics you picked.</p>")
    return _page("Link expired", "<p>That confirmation link is invalid or already used.</p>")
```

- [ ] **Step 5: Run tests**

Run: `cd analytics && python -m pytest test_subscriptions.py -v`
Expected: PASS (all)

- [ ] **Step 6: Commit**

```bash
git add analytics/app.py analytics/test_subscriptions.py
git commit -m "feat(subscribe): /confirm endpoint + confirmed page"
```

---

### Task 5: `/unsubscribe` endpoint + page

**Files:**
- Modify: `analytics/app.py` (add `/unsubscribe`)
- Test: `analytics/test_subscriptions.py`

**Interfaces:**
- Produces: `GET /unsubscribe?token=[&topic=]` → `HTMLResponse`. With `topic`, removes that one subscription; without, removes all. Idempotent.

- [ ] **Step 1: Write the failing test**

```python
def test_unsubscribe_all_and_per_topic(monkeypatch):
    app, path = _fresh_app()
    monkeypatch.setattr(app, "_send_confirmation", lambda *a, **k: None)
    from fastapi.testclient import TestClient
    import sqlite3
    client = TestClient(app.app)
    client.post("/subscribe", json={"email": "u@x.com", "topics": ["games", "writing", "everything"]})
    c = sqlite3.connect(path)
    tok = c.execute("SELECT unsub_token FROM subscribers WHERE email='u@x.com'").fetchone()[0]
    c.close()
    client.get(f"/unsubscribe?token={tok}&topic=games")
    c = sqlite3.connect(path)
    left = {r[0] for r in c.execute("SELECT topic FROM subscriptions WHERE email='u@x.com'")}
    assert left == {"writing", "everything"}
    c.close()
    r = client.get(f"/unsubscribe?token={tok}")   # all
    assert r.status_code == 200
    c = sqlite3.connect(path)
    n = c.execute("SELECT COUNT(*) FROM subscriptions WHERE email='u@x.com'").fetchone()[0]
    assert n == 0
    c.close()
    assert client.get(f"/unsubscribe?token={tok}").status_code == 200  # idempotent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd analytics && python -m pytest test_subscriptions.py::test_unsubscribe_all_and_per_topic -v`
Expected: FAIL (404)

- [ ] **Step 3: Add the endpoint**

```python
@app.get("/unsubscribe")
async def unsubscribe(token: str = Query(default=""), topic: str = Query(default="")) -> HTMLResponse:
    if token:
        with _conn() as c:
            row = c.execute("SELECT email FROM subscribers WHERE unsub_token = ?", (token,)).fetchone()
            if row:
                email = row["email"]
                if topic:
                    c.execute("DELETE FROM subscriptions WHERE email = ? AND topic = ?", (email, topic))
                    what = f"the {topic} list"
                else:
                    c.execute("DELETE FROM subscriptions WHERE email = ?", (email,))
                    what = "all lists"
                return _page("Unsubscribed", f"<p>You've been removed from {what}.</p>")
    return _page("Unsubscribed", "<p>You're unsubscribed.</p>")
```

- [ ] **Step 4: Run tests**

Run: `cd analytics && python -m pytest test_subscriptions.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add analytics/app.py analytics/test_subscriptions.py
git commit -m "feat(subscribe): /unsubscribe endpoint (all + per-topic)"
```

---

### Task 6: `/send` endpoint (token-gated broadcast)

**Files:**
- Modify: `analytics/app.py` (add `/send` + recipient selection)
- Test: `analytics/test_subscriptions.py`

**Interfaces:**
- Consumes: `send_email`, `require_token`, `TOPIC_IDS`.
- Produces: `POST /send {topic, subject, html}` (token-gated) → `{ok, n}`. Recipients = confirmed subscribers on `topic` OR `everything`, deduped; each gets an appended per-recipient unsubscribe link + `List-Unsubscribe` header; logs a `campaigns` row.

- [ ] **Step 1: Write the failing test**

```python
def test_send_selects_everything_and_dedupes(monkeypatch):
    app, path = _fresh_app()
    monkeypatch.setattr(app, "_send_confirmation", lambda *a, **k: None)
    sent = []
    monkeypatch.setattr(app, "send_email", lambda to, subj, html, list_unsub=None: sent.append(to) or True)
    from fastapi.testclient import TestClient
    import sqlite3
    client = TestClient(app.app)
    # a: games only, b: everything only, c: games + everything (dup risk), d: unconfirmed
    for email, topics in [("a@x.com", ["games"]), ("b@x.com", ["everything"]),
                          ("c@x.com", ["games", "everything"]), ("d@x.com", ["games"])]:
        client.post("/subscribe", json={"email": email, "topics": topics})
    conn = sqlite3.connect(path)
    conn.execute("UPDATE subscribers SET confirmed=1 WHERE email!='d@x.com'"); conn.commit(); conn.close()
    r = client.post("/send", json={"topic": "games", "subject": "Hi", "html": "<p>x</p>"},
                    headers={"X-Stats-Token": "testtoken"})
    body = r.json()
    assert body["ok"] is True and body["n"] == 3            # a,b,c ; d excluded (unconfirmed)
    assert sorted(sent) == ["a@x.com", "b@x.com", "c@x.com"] # deduped
    r2 = client.post("/send", json={"topic": "games", "subject": "Hi", "html": "<p>x</p>"})
    assert r2.status_code == 401                            # token required
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd analytics && python -m pytest test_subscriptions.py::test_send_selects_everything_and_dedupes -v`
Expected: FAIL (404)

- [ ] **Step 3: Add the model + endpoint**

```python
class SendReq(BaseModel):
    topic: str
    subject: str
    html: str


@app.post("/send", dependencies=[Depends(require_token)])
async def send(req: SendReq) -> dict[str, Any]:
    if req.topic not in TOPIC_IDS:
        return {"ok": False, "msg": "unknown topic"}
    if not RESEND_API_KEY:
        return {"ok": False, "msg": "sending not configured (RESEND_API_KEY unset)"}
    now = int(time.time() * 1000)
    with _conn() as c:
        rows = c.execute(
            """SELECT DISTINCT s.email, s.unsub_token
               FROM subscribers s JOIN subscriptions x ON x.email = s.email
               WHERE s.confirmed = 1 AND x.topic IN (?, 'everything')""",
            (req.topic,),
        ).fetchall()
    n = 0
    for row in rows:
        unsub = f"{SITE_URL}/api/analytics/unsubscribe?token={row['unsub_token']}&topic={req.topic}"
        html = req.html + (
            f"<hr><p style='color:#888;font-size:12px'>"
            f"<a href='{unsub}'>Unsubscribe from {req.topic}</a></p>"
        )
        if send_email(row["email"], req.subject, html, list_unsub=unsub):
            n += 1
    with _conn() as c:
        c.execute("INSERT INTO campaigns (topic, subject, sent_ts, n) VALUES (?, ?, ?, ?)",
                  (req.topic, req.subject, now, n))
    return {"ok": True, "n": n}
```

- [ ] **Step 4: Run tests**

Run: `cd analytics && python -m pytest test_subscriptions.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add analytics/app.py analytics/test_subscriptions.py
git commit -m "feat(subscribe): token-gated /send broadcast with campaign log"
```

---

### Task 7: Admin compose page + topic counts

**Files:**
- Create: `analytics/newsletter.html` (served by the app)
- Modify: `analytics/app.py` (add `GET /newsletter` HTML route + `GET /topic-stats` token-gated)
- Test: `analytics/test_subscriptions.py`

**Interfaces:**
- Produces: `GET /topic-stats` (token-gated) → `{topic: confirmed_count}` incl. an `everything`-inclusive count; `GET /newsletter` → the compose page HTML. The page prompts for the stats token, calls `/topic-stats` and `/send` with it.

- [ ] **Step 1: Write the failing test**

```python
def test_topic_stats_counts_confirmed(monkeypatch):
    app, path = _fresh_app()
    monkeypatch.setattr(app, "_send_confirmation", lambda *a, **k: None)
    from fastapi.testclient import TestClient
    import sqlite3
    client = TestClient(app.app)
    client.post("/subscribe", json={"email": "a@x.com", "topics": ["games"]})
    client.post("/subscribe", json={"email": "b@x.com", "topics": ["everything"]})
    conn = sqlite3.connect(path); conn.execute("UPDATE subscribers SET confirmed=1"); conn.commit(); conn.close()
    r = client.get("/topic-stats", headers={"X-Stats-Token": "testtoken"})
    d = r.json()
    assert d["games"] == 2      # games subscriber + everything subscriber
    assert d["music"] == 1      # only the everything subscriber
    assert client.get("/topic-stats").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd analytics && python -m pytest test_subscriptions.py::test_topic_stats_counts_confirmed -v`
Expected: FAIL (404)

- [ ] **Step 3: Add `from fastapi.responses import FileResponse`** to imports (alongside `HTMLResponse`).

- [ ] **Step 4: Add the routes**

```python
@app.get("/topic-stats", dependencies=[Depends(require_token)])
async def topic_stats() -> dict[str, int]:
    with _conn() as c:
        ev = c.execute(
            "SELECT COUNT(DISTINCT x.email) FROM subscriptions x JOIN subscribers s ON s.email=x.email "
            "WHERE s.confirmed=1 AND x.topic='everything'"
        ).fetchone()[0]
        out = {}
        for tid, _label, _blurb in TOPICS:
            base = c.execute(
                "SELECT COUNT(DISTINCT x.email) FROM subscriptions x JOIN subscribers s ON s.email=x.email "
                "WHERE s.confirmed=1 AND x.topic IN (?, 'everything')",
                (tid,),
            ).fetchone()[0]
            out[tid] = base if tid != "everything" else ev
    return out


@app.get("/newsletter")
async def newsletter_page() -> FileResponse:
    return FileResponse(os.path.join(os.path.dirname(__file__), "newsletter.html"))
```

- [ ] **Step 5: Create `analytics/newsletter.html`** (token in a field, kept only in memory)

```html
<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Newsletter</title>
<style>body{background:#14131a;color:#e8e3d8;font-family:system-ui;max-width:640px;margin:40px auto;padding:0 16px}
input,textarea,select,button{width:100%;padding:8px;margin:6px 0;background:#1c1b25;color:#e8e3d8;border:1px solid #333;border-radius:4px;font:inherit}
button{background:#d4a955;color:#14131a;cursor:pointer;font-weight:600}#out{white-space:pre-wrap;color:#a8a39a}</style>
</head><body><h1>Send a newsletter</h1>
<input id=tok type=password placeholder="stats token">
<select id=topic></select>
<div id=count style="color:#a8a39a;font-size:13px"></div>
<input id=subj placeholder="subject">
<textarea id=body rows=12 placeholder="HTML body"></textarea>
<button onclick=doSend()>Send</button><div id=out></div>
<script>
const base = location.hostname==='localhost'?'http://localhost:8001':'/api/analytics';
const TOPICS=["sciencebowl","sports","games","markets","writing","music","content","everything"];
const sel=document.getElementById('topic');
TOPICS.forEach(t=>{const o=document.createElement('option');o.value=o.textContent=t;sel.appendChild(o)});
async function counts(){const t=document.getElementById('tok').value;if(!t)return;
  const r=await fetch(base+'/topic-stats',{headers:{'X-Stats-Token':t}});if(!r.ok){return}
  const d=await r.json();window._c=d;showCount()}
function showCount(){if(window._c)document.getElementById('count').textContent=(window._c[sel.value]||0)+' confirmed recipients'}
sel.onchange=showCount;document.getElementById('tok').onchange=counts;
async function doSend(){const t=document.getElementById('tok').value;
  const r=await fetch(base+'/send',{method:'POST',headers:{'Content-Type':'application/json','X-Stats-Token':t},
    body:JSON.stringify({topic:sel.value,subject:document.getElementById('subj').value,html:document.getElementById('body').value})});
  document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2)}
</script></body></html>
```

- [ ] **Step 6: Run tests**

Run: `cd analytics && python -m pytest test_subscriptions.py -v`
Expected: PASS (all)

- [ ] **Step 7: Commit**

```bash
git add analytics/app.py analytics/newsletter.html analytics/test_subscriptions.py
git commit -m "feat(subscribe): admin compose page + topic-stats endpoint"
```

---

### Task 8: `subscribe.html` hub

**Files:**
- Create: `subscribe.html` (repo root)

**Interfaces:**
- Consumes: `POST /subscribe {email, topics[], source}`.

- [ ] **Step 1: Create `subscribe.html`** (matches site fonts/vars; topic list mirrors the backend `TOPICS`)

```html
<!doctype html><html lang=en><head><meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Subscribe</title>
<link rel=icon href="/favicon.ico">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=Space+Grotesk:wght@500&family=JetBrains+Mono&display=swap" rel=stylesheet>
<style>
:root{--bg:#14131a;--fg:#e8e3d8;--soft:#a8a39a;--dim:#6b6862;--accent:#d4a955}
body{background:var(--bg);color:var(--fg);font-family:Inter,sans-serif;max-width:620px;margin:0 auto;padding:56px 20px;line-height:1.5}
h1{font-family:'Space Grotesk';font-weight:500;letter-spacing:.02em}
.sub{color:var(--soft);margin-bottom:28px}
.topic{display:flex;gap:12px;align-items:flex-start;padding:12px;border:1px solid #262530;border-radius:6px;margin:8px 0;cursor:pointer}
.topic:hover{border-color:#3a3947}.topic input{margin-top:3px}
.topic .label{font-weight:500}.topic .blurb{color:var(--dim);font-size:13px}
.row{display:flex;gap:8px;margin-top:20px}
input[type=email]{flex:1;padding:11px;background:#1c1b25;color:var(--fg);border:1px solid #333;border-radius:4px;font:inherit}
button{padding:11px 20px;background:var(--accent);color:var(--bg);border:0;border-radius:4px;font-weight:600;cursor:pointer}
button:disabled{opacity:.5}#msg{margin-top:14px;color:var(--soft);min-height:20px}#msg.error{color:#d68a8a}
a{color:var(--accent)}.foot{margin-top:32px;font-size:12px;color:var(--dim);font-family:'JetBrains Mono'}
</style></head><body>
<h1>What are you curious about?</h1>
<p class="sub">Pick any topics — I'll email you when there's something new. Occasional, unsubscribe anytime.</p>
<form id=f><div id=topics></div>
<div class=row><input type=email id=email placeholder="you@example.com" required autocomplete=email>
<button type=submit>Subscribe</button></div></form>
<div id=msg></div>
<p class="foot"><a href="/">← djiang.xyz</a> &middot; <a href="https://share.djiang.xyz">share</a></p>
<script>
const TOPICS=[["sciencebowl","Science Bowl","SciBowl.Live, LeBot, NSBA"],
["sports","Sports Betting","SharpLab, CLV, odds & quant lab"],
["games","Games","games.djiang.xyz, card-game builds"],
["markets","Markets / Prediction","Vigil, NSBA Markets, Kalshi work"],
["writing","Writing / Essays","new posts & essays"],
["music","Music","albums, playlists, scrobble notes"],
["content","Content / Making","videos, streams, share.djiang.xyz drops"],
["everything","Everything","just email me when I do anything"]];
const box=document.getElementById('topics');
const pre=new URLSearchParams(location.search).get('topic');
TOPICS.forEach(([id,label,blurb])=>{const l=document.createElement('label');l.className='topic';
l.innerHTML=`<input type=checkbox value="${id}" ${id===pre?'checked':''}><span><span class=label>${label}</span><br><span class=blurb>${blurb}</span></span>`;box.appendChild(l)});
const base=location.hostname==='localhost'||location.hostname==='127.0.0.1'?'http://localhost:8001':'/api/analytics';
document.getElementById('f').addEventListener('submit',async e=>{e.preventDefault();
const email=document.getElementById('email').value.trim();
const topics=[...document.querySelectorAll('#topics input:checked')].map(i=>i.value);
const msg=document.getElementById('msg');msg.className='';
if(!email){return}if(!topics.length){msg.className='error';msg.textContent='Pick at least one topic.';return}
const btn=e.target.querySelector('button');btn.disabled=true;
try{const r=await fetch(base+'/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({email,topics,source:'hub'})});const d=await r.json();
msg.className=d.ok?'':'error';msg.textContent=d.msg;if(d.ok)document.getElementById('email').value='';}
catch(err){msg.className='error';msg.textContent="Couldn't reach the server.";}finally{btn.disabled=false}});
</script></body></html>
```

- [ ] **Step 2: Verify locally** — start the API (`cd analytics && uvicorn app:app --port 8001`), open `subscribe.html` at `http://localhost:8001`-served or via a static server on the repo root, check topics render and a submit hits the endpoint (expect the "check your inbox" message).

- [ ] **Step 3: Commit**

```bash
git add subscribe.html
git commit -m "feat(subscribe): topic hub page"
```

---

### Task 9: Contextual forms + nav/footer links

**Files:**
- Modify: `post.html:434` (add `topics` to the POST body + confirmation copy)
- Modify: `writing.html`, `reading.html` (add the compact inline form)
- Modify: `archive.html` (add a plain link to `subscribe.html`)
- Modify: `index.html:429` (add `subscribe` to the contact strip)

**Interfaces:**
- Consumes: `POST /subscribe`.

- [ ] **Step 1: Update `post.html` submit body** — change the `body:` line (currently `JSON.stringify({ email, source: \`post:${slug}\` })`) to include the writing topic:

```javascript
        body: JSON.stringify({ email, topics: ['writing'], source: `post:${slug}` }),
```

  And the success copy (line ~438) already uses `data.msg`, which now returns the confirm-your-inbox message — no change needed.

- [ ] **Step 2: Add `subscribe` to the homepage contact strip** — in `index.html`, after the `stats` link (line ~429):

```html
      <span class="sep">&middot;</span>
      <a href="subscribe.html">subscribe</a>
```

- [ ] **Step 3: Add a compact inline form to `writing.html` and `reading.html`** — before the closing `</body>` (or after the list), insert (set `TOPIC` to `writing` on both):

```html
<section style="max-width:600px;margin:40px auto;padding:20px;border-top:1px solid #262530">
  <p style="color:#a8a39a;font-family:Inter,sans-serif">Get new writing in your inbox.</p>
  <form id="ctx-sub" style="display:flex;gap:8px">
    <input type="email" id="ctx-email" placeholder="you@example.com" required
      style="flex:1;padding:9px;background:#1c1b25;color:#e8e3d8;border:1px solid #333;border-radius:4px">
    <button type="submit" style="padding:9px 16px;background:#d4a955;border:0;border-radius:4px;font-weight:600;cursor:pointer">Subscribe</button>
  </form>
  <div id="ctx-msg" style="margin-top:8px;color:#a8a39a;font-size:13px"></div>
</section>
<script>
(function(){var TOPIC='writing';
var base=location.hostname==='localhost'||location.hostname==='127.0.0.1'?'http://localhost:8001':'/api/analytics';
var f=document.getElementById('ctx-sub');if(!f)return;
f.addEventListener('submit',async function(e){e.preventDefault();
var email=document.getElementById('ctx-email').value.trim();var msg=document.getElementById('ctx-msg');
if(!email)return;var btn=f.querySelector('button');btn.disabled=true;
try{var r=await fetch(base+'/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({email:email,topics:[TOPIC],source:'ctx:'+location.pathname})});var d=await r.json();
msg.textContent=d.msg;if(d.ok)document.getElementById('ctx-email').value='';}
catch(err){msg.textContent="Couldn't reach the server.";}finally{btn.disabled=false}});})();
</script>
```

- [ ] **Step 4: Add a link to `archive.html`** — before `</body>`, a plain pointer (no inline form, since archive spans multiple stacks):

```html
<p style="text-align:center;margin:32px 0;font-family:'JetBrains Mono',monospace;font-size:12px">
  <a href="subscribe.html" style="color:#d4a955">get email updates on topics you care about →</a>
</p>
```

- [ ] **Step 5: Verify** — load each page locally, confirm the form posts and returns the confirm message; confirm the homepage strip shows `subscribe`.

- [ ] **Step 6: Commit**

```bash
git add index.html post.html writing.html reading.html archive.html
git commit -m "feat(subscribe): contextual forms + nav/footer links"
```

---

### Task 10: Docs + deploy notes

**Files:**
- Modify: `analytics/README.md`

**Interfaces:** none.

- [ ] **Step 1: Document the new endpoints, env vars, and DNS step** — append to `analytics/README.md`:

```markdown
## Email subscriptions (topics)

Endpoints (all under the Caddy `/api/analytics/` proxy):
- `POST /subscribe` `{email, topics[], source}` — double opt-in; sends a confirmation email.
- `GET /confirm?token=` — confirm (single-use).
- `GET /unsubscribe?token=[&topic=]` — remove all or one topic.
- `POST /send` `{topic, subject, html}` (token-gated) — broadcast; `everything` subscribers always included.
- `GET /topic-stats` (token-gated) — confirmed count per topic.
- `GET /newsletter` — admin compose page.

Env vars:
- `RESEND_API_KEY` — Resend API key (sending fails closed without it).
- `MAIL_FROM` — default `David <david@djiang.xyz>`.
- `SITE_URL` — default `https://djiang.xyz`.

One-time deliverability setup (do this or mail lands in spam):
1. Add the domain `djiang.xyz` in the Resend dashboard.
2. Add the DKIM + SPF (and a DMARC) DNS records Resend shows you, at your DNS host.
3. Wait for verification, then set `RESEND_API_KEY` and restart `davidj-analytics`.
```

- [ ] **Step 2: Commit**

```bash
git add analytics/README.md
git commit -m "docs(subscribe): endpoints, env vars, Resend DNS setup"
```

---

## Self-Review

**Spec coverage:**
- Topics single source of truth → Task 1 (`TOPICS`/`TOPIC_IDS`) + mirrored in Tasks 7/8.
- Data model (subscribers cols, subscriptions, campaigns) → Task 1.
- `POST /subscribe` topic-aware double opt-in → Task 2.
- Resend transport + confirmation email → Task 3.
- `/confirm` → Task 4. `/unsubscribe` (+List-Unsubscribe) → Tasks 5 (page/delete) & 3/6 (header on sends).
- `/send` recipient selection incl. `everything`, dedupe, campaign log → Task 6.
- Admin compose page + counts → Task 7.
- `subscribe.html` hub → Task 8. Contextual forms (post/writing/reading) + archive link + contact-strip link → Task 9.
- Share/blog surfacing (footer links, writing topic) → Tasks 8 & 9.
- Error handling (fail-closed no key, non-enumerating) → Tasks 2–6. Testing minimum → Tasks 1–7 tests. Deploy/DNS → Task 10.
- Existing-subscriber migration note: existing flat rows keep `confirmed` as-is; they simply have no `subscriptions` rows until they re-subscribe. `ponytail:` acceptable — the legacy flat list was tiny; backfill to `everything` only if David wants (one UPDATE), not worth a task.

**Placeholder scan:** none — every code step is concrete.

**Type consistency:** `send_email(to, subject, html, list_unsub=None)` used identically in Tasks 3/6; `_send_confirmation(email, token)` stub (Task 2) → real (Task 3); `_page(title, body)` defined Task 4, reused Task 5; `TOPIC_IDS`/`TOPICS` consistent across tasks; `{ok, msg}` / `{ok, n}` response shapes consistent.

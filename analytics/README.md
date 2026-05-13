# davidJ analytics

Tiny self-hosted analytics for djiang.xyz. FastAPI + SQLite.

## What it tracks

- **Pageviews** — page path, referrer, user-agent, hashed IP (for unique-visitor estimate)
- **Duration** — how long the page was open (sent on tab hide / page unload)
- **Scroll depth** — max % scrolled (most useful for posts/books)
- **Cube clicks** — which cube was opened on the partition
- **Label clicks** — which column label was opened

No cookies. Session/visitor ID is stored in localStorage as a random UUID. Raw IP is not stored — only a 16-char SHA-256 hash, used to approximate unique visitors when localStorage is cleared.

## Endpoints

- `POST /event` — record an event (called by `analytics.js`)
- `GET /stats` — aggregated stats JSON (consumed by `/stats.html`)
- `GET /recent?limit=100` — recent event feed
- `GET /health` — liveness check
- `POST /subscribe` — newsletter signup (`{email, source}`); dedupes on email
- `GET /subscribers` — subscriber count + recent (no PII)

## Newsletter

Email collection only — no sending built in. To send a post:

```sh
sqlite3 /opt/davidJ/analytics/analytics.db \
  "SELECT email FROM subscribers ORDER BY ts" | xclip
```

then BCC from Gmail (500/day limit) or paste into Buttondown / Resend when ready
to migrate. The signup form lives on every blog post and at the bottom of
`writing.html`.

## Local development

```sh
cd analytics
python -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app:app --reload --port 8001
```

Then run the static site (e.g. `python -m http.server 4747` from the repo root) and hit `http://localhost:4747/`. The `analytics.js` client posts to `/api/analytics/event`, which Caddy proxies to `localhost:8001` in production. For local dev, see the local-dev shim at the bottom of `analytics.js`.

## VPS deploy

1. **First-time setup on the VPS** (one-time, requires SSH or Sentinel admin):
   ```sh
   cd /opt/davidJ/analytics
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   sudo cp davidj-analytics.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now davidj-analytics
   ```

2. **Caddyfile** — add to the `djiang.xyz` block:
   ```caddy
   djiang.xyz {
       root * /opt/davidJ
       file_server

       handle /api/analytics/* {
           uri strip_prefix /api/analytics
           reverse_proxy localhost:8001
       }
   }
   ```
   Reload Caddy: `sudo systemctl reload caddy`.

3. **Optionally protect /stats.html** with basic auth:
   ```caddy
   @stats path /stats.html
   basicauth @stats {
       david $bcrypt_hash_here
   }
   ```
   Generate the hash with `caddy hash-password`.

4. **Future deploys** — `git push` then `/deploy davidJ` in Discord. Sentinel syncs files; if `app.py` or `requirements.txt` changed, also run `sudo systemctl restart davidj-analytics` (since davidJ is registered as a static-site deploy, the service doesn't auto-restart on file sync — TODO: register `service_name=davidj-analytics` for the analytics deploy path).

## Backups

The SQLite DB lives at `/opt/davidJ/analytics/analytics.db`. To back up:
```sh
sqlite3 /opt/davidJ/analytics/analytics.db ".backup '/path/to/backup.db'"
```

## Privacy

Cookieless. IP is hashed and only used to estimate unique visitors. No third-party scripts, no fingerprinting beyond user-agent (truncated to 240 chars). GDPR-friendly by default.

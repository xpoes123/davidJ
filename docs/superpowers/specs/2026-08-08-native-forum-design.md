# Native Forum with Google Login

**Date:** 2026-08-08
**Status:** Approved design, ready for planning

## Goal

A small, on-site forum for discussion around the topics David cares about
(the same eight subscribe topics). Google login to post; open reading. Built
and owned end-to-end — no third-party embed. Kept deliberately minimal.

This is a **separate project** from the topic-subscriptions layer
(`2026-08-08-topic-subscriptions-design.md`). They share the topic list and
one integration point (below) but ship independently.

## Decisions locked

- **Ownership:** native forum, not Giscus/Discord. David owns the data.
- **Auth:** Google OAuth (OpenID Connect) via `authlib`. No passwords. Signed-
  cookie session via Starlette `SessionMiddleware`. Reading open to all;
  posting requires login.
- **Moderation / openness:** **first-post approval.** A new user's first post
  is held until David approves them; after approval they post freely. David is
  sole moderator (delete any thread/post). Rate-limit as the second wall.
- **Backend home:** extend the existing `analytics/app.py` service +
  `analytics.db` SQLite. No new service.
- **Rendering:** server-rendered HTML pages at `djiang.xyz/forum` (real,
  linkable, indexable URLs), not a JS SPA.
- **Categories:** the eight subscribe topics, reused verbatim.

## Non-goals (deferred)

- Rich-text/WYSIWYG editor (plain text + light markdown only).
- Notifications, DMs, upvotes/reactions, nested/threaded replies.
- User profiles beyond name + avatar from Google.
- Report queue / automated moderation (David deletes reactively; first-post
  approval + rate limit is the spam wall until volume demands more).
- Search (browser Ctrl-F / small volume is fine at first).

## Background (reused infrastructure)

- `analytics/app.py` — FastAPI + SQLite, runs as `davidj-analytics.service`
  on `localhost:8001`. Caddy proxies `/api/analytics/*` → `:8001`.
- Token-gated admin pattern already exists (`require_token` / `STATS_TOKEN`)
  and a stats dashboard — the forum's approval/moderation queue extends it.
- The eight topics are defined by the subscriptions project; the forum imports
  the same list (keep them in one place in the backend so both features read
  it).

## Code organization

`analytics/app.py` is already ~530 lines. Adding a forum + OAuth + rendered
pages inline would make it do too much, so split by concern into modules
mounted on the **same** FastAPI app / same service (still one deploy):
`analytics/forum.py` (routes + auth), and pull the subscribe/email code into
`analytics/subscribe.py` when that project lands. Shared bits (DB `_conn`,
topic list, token gate) live in a small common module both import. This keeps
each file focused without adding a second service.

## Data model (extend `analytics.db`)

Same in-place `ALTER TABLE … except OperationalError` migration pattern.

- `users(google_sub TEXT PRIMARY KEY, email TEXT, name TEXT, avatar TEXT,
  approved INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0, created_ts INTEGER)`
  — identity from Google. `approved=0` until David approves; `is_admin=1` for
  David (seeded by his Google `sub`/email).
- `threads(id INTEGER PK, topic TEXT, title TEXT, author_sub TEXT,
  ts INTEGER, deleted INTEGER DEFAULT 0)`
- `posts(id INTEGER PK, thread_id INTEGER, author_sub TEXT, body TEXT,
  ts INTEGER, deleted INTEGER DEFAULT 0, pending INTEGER DEFAULT 0)`
  — `pending=1` while the author is unapproved; hidden from public views,
  shown in the admin queue. Thread's own visibility follows its first post.

Visibility rule: a thread is public iff it has at least one non-deleted,
non-pending post. Approving a user flips all their `pending` posts to
`pending=0` in one action.

## Auth flow (Google OIDC via authlib)

- `GET /forum/login` → redirect to Google consent.
- `GET /forum/auth/callback` → exchange code, upsert `users` row (keyed on
  Google `sub`), set signed-cookie session, redirect back.
- `GET /forum/logout` → clear session.
- Env: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`. Redirect
  URI `https://djiang.xyz/forum/auth/callback`. Google email arrives verified,
  so it's trustworthy for the subscribe integration below.
- Fail closed: if Google creds are unset, login is disabled and the forum is
  read-only with a "sign-in unavailable" notice.

## Pages (server-rendered under `/forum`)

- `/forum` — the eight topics with thread counts + a recent-threads list.
- `/forum/t/{topic}` — threads in a topic (newest first) + "new thread" (login
  required).
- `/forum/thread/{id}` — thread title, posts in order, reply form (login
  required). Author sees edit/delete on own posts; admin sees delete on all.
- Header shows login/logout + avatar. Minimal inline CSS matching the site
  (Inter / Space Grotesk / JetBrains Mono, existing CSS variables).

## Posting endpoints

- `POST /forum/thread` `{topic, title, body}` — login required; validate topic
  in the known set. If author `approved=0`, the thread's first post is written
  `pending=1` (not publicly visible) and enters the approval queue.
- `POST /forum/thread/{id}/reply` `{body}` — login required; same pending rule
  for unapproved authors.
- `POST /forum/post/{id}/edit` / `POST /forum/post/{id}/delete` — author-only
  (soft delete), or admin for any.
- **Rate limit:** per-user cap (e.g. N posts / minute) as the second spam
  wall. `ponytail:` fixed in-code constant; make it env-tunable only if abused.

## Admin (extends the token-gated dashboard)

- Pending queue: users awaiting first-post approval, with the post preview →
  **approve user** (flips `approved=1` + reveals their pending posts) or
  **delete** the content.
- Delete any thread/post.
- `ponytail:` optional one-line Discord ping via the existing `notify` path
  when a new pending post lands, so David isn't polling the queue. Deferred
  unless he wants it.

## Integration with the subscribe layer (the free win)

On any forum page, a logged-in user sees a one-click "email me about {topic}"
toggle. Because Google already verified their email, this calls the
subscriptions `/subscribe` and marks them **confirmed immediately** (skip the
double-opt-in email for Google-authenticated sessions only). Logged-out
visitors still use the normal `subscribe.html` hub with double opt-in. The two
systems share the topic list; neither depends on the other to function.

## Error handling

- Posting while logged out → redirect to login, not a 500.
- Unknown topic → reject with a friendly message.
- Google callback errors (denied consent, expired code) → back to `/forum`
  with a notice, no stack trace.
- Missing OAuth/session env → read-only forum, clear notice; existing
  analytics + subscribe features unaffected.
- Deletes are soft (`deleted=1`) so nothing is truly lost.

## Testing (ponytail minimum)

One runnable backend self-check (pytest, Google exchange stubbed, offline):

- unapproved user's first post is stored `pending=1` and absent from public
  thread/topic views;
- approving that user flips their posts to visible in one action;
- posting endpoints reject logged-out requests;
- soft-delete hides a post/thread from public views;
- rate limit triggers after the cap;
- unknown topic rejected; thread public only once it has a visible post.

## Rollout / deploy (manual)

- Add the Caddy route `/forum/*` → `localhost:8001` (alongside the existing
  `/api/analytics/*` proxy).
- Google Cloud: create OAuth consent screen + credentials, set the redirect
  URI (one-time manual step).
- Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`; seed
  David's row as `is_admin=1`.
- `pip install authlib` (new dep), smoke-test imports, `systemctl restart
  davidj-analytics`. Branch → PR → squash-merge → pull on VPS per repo
  convention.

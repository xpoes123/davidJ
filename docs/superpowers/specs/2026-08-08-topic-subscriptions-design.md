# Topic Subscriptions + Self-Hosted Newsletter

**Date:** 2026-08-08
**Status:** Approved design, ready for planning

## Goal

Make djiang.xyz interactive by letting visitors subscribe to per-topic email
lists based on what they're curious about (games, science bowl, markets,
sports, and more), and let David compose + send newsletters to those lists
from his own backend. Secondary: use the *Writing* topic + per-post opt-in to
make the blog more prevalent, and surface `share.djiang.xyz` without building
a parallel feed.

The homepage stays deliberately full — this adds an interactive *layer*
(subscribe + surfacing), not new homepage real estate. Only one homepage
change: a single `subscribe` link in the contact strip.

## Non-goals (deferred)

- Auto-notify the *Content* list when a `share.djiang.xyz` drop is published
  (future one-line call from the share app to `POST /send`).
- Markdown-in-browser preview for the composer (plain HTML body box first).
- Open/click-rate analytics.
- Own SMTP/MTA on the VPS (delivery goes through Resend).
- **User login / accounts.** No concrete "save X" use case yet, and it's a
  large security surface. If a real need appears, the lazy path is an email
  magic-link reusing the subscriber emails (no passwords) or `localStorage`
  for device-local state — added only when the use case is nameable.

## Decisions locked

- **Delivery:** self-hosted — David's backend composes and sends.
- **Transport:** Resend API (over the existing `httpx` dep), not a self-run
  MTA. Sending from `david@djiang.xyz`.
- **Opt-in:** double opt-in (confirmation email before a subscriber is
  active). `ponytail:` this is the one place with meaningful extra code;
  downgrade path to single opt-in is a smaller build if ever wanted.
- **Placement:** hub page + contextual prompts on topic pages (both).
- **Backend home:** extend the existing `analytics/app.py` FastAPI service
  (`davidj-analytics.service`), not a new service.

## Background (what already exists)

- `analytics/app.py` — FastAPI + SQLite (`analytics.db`), runs as
  `davidj-analytics.service`. Already has:
  - `subscribers(email UNIQUE, ts, source, ip_hash, ua, confirmed DEFAULT 1)`
  - `POST /subscribe` `{email, source}` — flat list, single opt-in, dedupes
    on email.
  - `GET /subscribers` — token-gated count + recent (no PII).
  - Token gating via `require_token` / `STATS_TOKEN`.
  - A stats dashboard reading `/stats`, and `httpx` already a dependency.
- `post.html` — a `.newsletter` block already styled and present, currently
  `display:none`, with a `#subscribe-form`.
- Homepage (`index.html`) contact strip has links incl. `stats` (`me.html`).

## Topics (single source of truth)

Eight lists, each `{id, label, blurb}`:

| id | label | blurb source |
|----|-------|--------------|
| `sciencebowl` | Science Bowl | SciBowl.Live, LeBot, NSBA |
| `sports` | Sports Betting | SharpLab, CLV, odds/quant lab |
| `games` | Games | games.djiang.xyz, card-game builds |
| `markets` | Markets / Prediction | Vigil, NSBA Markets, Kalshi work |
| `writing` | Writing / Essays | new blog posts + essays |
| `music` | Music | albums, playlists, scrobble notes |
| `content` | Content / Making | videos, streams, share.djiang.xyz drops |
| `everything` | Everything | catch-all |

Defined once as a JS array (frontend) and mirrored as a validation set
(backend). `everything` is shorthand: a send to any topic **also** includes
`everything` subscribers. No shared-config loader — one JS array + one Python
set, kept in sync by hand (`ponytail:` promote to a `/topics` endpoint only
if a third consumer appears).

## Data model (extend `analytics.db`)

Migrate in place using the codebase's existing
`ALTER TABLE … except sqlite3.OperationalError` pattern.

- `subscribers` — add `confirm_token TEXT`, `unsub_token TEXT`. New signups
  start `confirmed=0`. Existing rows: set `confirmed=1`, backfill an
  `unsub_token`, and (optional) subscribe them to `everything` so the flat
  legacy list isn't stranded.
- `subscriptions(email, topic, ts, UNIQUE(email, topic))` — which lists each
  email is on. Deleting a row = unsubscribed from that topic.
- `campaigns(id, topic, subject, sent_ts, n)` — log of sends, for the admin
  history view.

Tokens: `confirm_token` and `unsub_token` are random URL-safe strings
(`secrets.token_urlsafe`). `unsub_token` is stable per person (one link works
forever); `confirm_token` is one-shot and cleared on confirm.

## Backend endpoints (added to `app.py`)

- `POST /subscribe` `{email, topics: [...], source}`
  - Validate email (reuse `EMAIL_RE`) and that every topic is in the known
    set (ignore/drop unknowns).
  - Upsert subscriber: new → `confirmed=0` + fresh `confirm_token` +
    `unsub_token`; existing → keep state.
  - Upsert `subscriptions` rows (idempotent on `UNIQUE(email, topic)`).
  - If subscriber is unconfirmed, send **one** confirmation email via Resend
    containing the confirm link. If already confirmed, no email — just add the
    topics and return a friendly "added" message.
  - Rate-limit friendly: same idempotent, non-enumerating responses the
    current endpoint already returns.
- `GET /confirm?token=` — match `confirm_token`, set `confirmed=1`, clear the
  token, render a small "you're in" page. Unknown/used token → gentle
  "this link's expired" page (no enumeration).
- `GET /unsubscribe?token=[&topic=]` — match `unsub_token`; with `topic`
  delete that one subscription, without it delete all of the person's
  subscriptions. Idempotent. Also the target of the `List-Unsubscribe`
  header. Renders a confirmation page.
- `POST /send` (token-gated by `require_token`) `{topic, subject, html}`
  - Select confirmed subscribers where topic matches OR they're on
    `everything` (deduped by email).
  - Send via Resend, each message carrying a per-recipient unsubscribe link
    and a `List-Unsubscribe` header.
  - Insert a `campaigns` row with the recipient count.
  - Return `{ok, n}`.

### Sending — Resend

- `RESEND_API_KEY` env var (fail closed: if unset, `/send` refuses and the
  admin page shows "sending not configured").
- One-time DNS setup (documented in the plan + `analytics/README.md`): verify
  `djiang.xyz` in Resend, add the DKIM/SPF (and DMARC) records it provides.
  This is the deliverability guard. Volume is tiny → Resend free tier.
- Every outbound email includes: an unsubscribe link, `List-Unsubscribe` +
  `List-Unsubscribe-Post` headers, and a plaintext fallback.

## Admin compose page

Extend the existing stats dashboard (same `STATS_TOKEN` gate) or a sibling
`/newsletter` admin view served by the same app:

- Topic dropdown (shows live confirmed-subscriber count for the selection,
  incl. `everything`).
- Subject field + HTML body textarea (plain HTML first; no preview).
- **Send** button → `POST /send`, shows result count.
- `campaigns` history list (topic, subject, when, n).

## Frontend

### `subscribe.html` — the hub
- Eight topics as checkboxes with blurbs + an email field; posts to
  `/subscribe` with the checked topic ids.
- Styled to match the site (Inter / Space Grotesk / JetBrains Mono, the
  existing CSS variables).
- Success state explains the confirmation email ("check your inbox to
  confirm").
- Linked from the homepage contact strip as `subscribe` (next to `stats`) and
  a footer link on inner pages.

### Contextual prompts
Only on pages with a clean single-topic mapping (no forced/fragile mappings):
- `post.html` — reveal the existing hidden `.newsletter` block, pre-selected
  to `writing`. Every blog post ends with an opt-in.
- `writing.html` — same compact form, pre-checked `writing`.
- `reading.html` — same form, pre-checked `writing` (reviews are writing;
  there is no separate `reading` topic).
- `archive.html` is multi-stack (projects/research/social/life) with no clean
  single topic, so it gets a plain link to `subscribe.html`, **not** an inline
  form. Avoids inventing a stack→topic mapping that doesn't exist.

### Confirmed / unsubscribed pages
Tiny server-rendered HTML responses from the backend, styled to match (shared
minimal inline CSS). No new static files needed unless cleaner.

## Share + blog surfacing (thin)

- Blog prevalence = the `writing` topic + per-post opt-in + hub cross-link to
  `writing.html`. No homepage restructuring.
- `share.djiang.xyz` = a discoverable footer link + the hub's *Content/Making*
  blurb. No mirrored feed. Auto-notify deferred (see non-goals).

## Error handling

- Invalid email / unknown topics → friendly, non-enumerating messages (match
  the current `/subscribe` behavior).
- Resend failure on confirm/send → surface to the admin on `/send`; on
  `/subscribe` the subscriber row + topics are still written, so a retry or
  manual resend is possible (don't lose the signup because email hiccuped).
- Missing `RESEND_API_KEY` → endpoints that need it fail closed with a clear
  message; `/subscribe` still records the signup as unconfirmed.
- All token lookups fail closed and avoid revealing whether an email/token
  exists.

## Testing (ponytail minimum)

One runnable backend self-check (pytest, no fixtures/frameworks beyond what's
there) exercising the money/security-ish paths:

- subscribe → new subscriber is `confirmed=0`, topic rows created;
- confirm token flips `confirmed=1` and is single-use;
- unsubscribe (all and per-topic) removes the right rows and is idempotent;
- `/send` recipient selection includes `everything` subscribers and dedupes;
- unknown topics are dropped, bad emails rejected.

Resend calls are stubbed (no real network) so the check runs offline.

## Rollout / deploy (manual, per repo convention)

Branch → PR → squash-merge → SSH to VPS, `git pull` into the davidJ working
tree, `pip install` any new deps (none expected beyond stdlib + existing
`httpx`), set `RESEND_API_KEY`, add Resend DNS records, then
`systemctl restart davidj-analytics`. Static HTML deploys with the usual
davidJ push/scp flow.

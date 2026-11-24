# Cube Scavenger Hunt + Self-Healing Layout + Discovery Telemetry

**Date:** 2026-07-17
**Status:** Approved design, ready for planning

## Goal

Add a chained scavenger hunt to djiang.xyz, starting with a discoverable
"easy" egg on the isometric homepage. Along the way, make the cube layout
self-heal into a valid plane partition so adding/removing cubes never
requires manual grid math, and instrument egg discovery so David can see
who found it.

This build ships three components: **A** (layout), **B** (easy egg), and
**C** (telemetry). Medium/hard puzzles and the final `/found` reward page
are a later design cycle.

## Background

- Homepage (`index.html`) renders `window.STACKS` from `data.js` as an
  isometric plane partition. Each stack currently hardcodes its `i, j`
  grid position; heights (cube counts) are hand-tuned so heights are
  weakly decreasing in both `i` and `j` (the plane-partition rule).
- Interaction: horizontal drag spins the whole partition via a continuous
  angle `theta` (unbounded); clicking a cube focuses its content panel;
  scroll browses cubes.
- Analytics: `analytics.js` exposes `window.track(type, data)`, sending
  events tagged with a persistent visitor id (`sid`, localStorage), page,
  referrer, timestamp. Backend `analytics/app.py` (FastAPI + SQLite) also
  records user-agent, hashed IP, and geo (country/city/org). A dashboard
  reads `/stats`. `window.track` is already used for `cube_click` /
  `label_click`.

## A. Self-healing cube layout

**Problem:** hand-assigned `i, j` plus hand-tuned heights break the
plane-partition rule whenever cubes change.

**Solution:** compute positions at load from heights alone.

1. `data.js` stops specifying `i, j`. Each stack carries only content
   (`label`, `color`, `cubes`, `archiveHref`). A top-level `rows: [...]`
   config gives the cell *shape* — e.g. `rows: [4, 4]` means row 0 has 4
   cells, row 1 has 4 cells. `rows` must be weakly decreasing (a Young
   diagram). Total cells must equal the number of stacks.
2. At load: sort stacks by height (cube count) descending.
3. Enumerate grid cells `(i, j)` from `rows`, in `i+j` ascending order
   (ties broken by `i`). This order is a linear extension of the cell
   poset: every cell's left `(i-1, j)` and upper `(i, j-1)` neighbor comes
   before it.
4. Assign the height-sorted stacks to cells in that order. Because each
   cell's left/upper neighbor was assigned earlier (>= height), the result
   is always a valid plane partition. No solver, no backtracking.

**Ordering choice:** pure height-sort. Stacks may move between rows as
their heights change; the tallest always sits at the origin corner. The
old career-row / personal-row split is not preserved.

**Invariant / test:** after layout, assert for every occupied cell that
`height(i,j) >= height(i+1,j)` and `height(i,j) >= height(i,j+1)`. Ship a
runnable check that fails if the assignment ever violates this, across a
few `rows`/height fixtures.

## B. Easy egg — "Scavenger Hunt" cube

- Add a height-1 stack `{ label: 'Scavenger Hunt', ... , cubes: [one
  cube] }`. Being the shortest, layout auto-places it at the outer corner
  of the staircase — a lone cube, visually the odd one out. No existing
  project cube is displaced.
- The cube has no `href`. Clicking it opens the content panel showing:
  **"interact with the site to start."**
- Spin tracking: as `theta` accumulates, count full revolutions
  (`2*PI` of travel, either direction). Track cumulative revolutions since
  page load in a module variable.
  - 1 revolution: draw a hairline crack overlay on the Scavenger Hunt cube.
  - 2 revolutions: more cracks spread.
  - 3 revolutions: the cube shatters (shards animate out) and a reveal
    overlay fades in: **"you solved the easy puzzle"** + the first clue.
- Persistence: hunt state lives in `localStorage` under a single `hunt`
  key, e.g. `{ easy: { solved: true, at: <ts> } }`. On load, if
  `hunt.easy.solved`, render the cube pre-shattered and skip re-triggering
  the reveal. State updates are idempotent.
- First clue text teases the (not-yet-built) medium puzzle without
  strictly resolving, e.g. *"the next one hides where you keep score."*
  (points loosely at the stats page; finalized when tier 2 is designed.)

**State machine (per session, backed by localStorage):**
`untouched -> cracked(1) -> cracked(2) -> shattered/solved`. Only advances;
never regresses. Reaching `shattered` writes `hunt.easy.solved` once.

## C. Discovery telemetry + "who did it"

Fire through existing `window.track` (auto-tagged with `sid`):

- `hunt_view` — Scavenger Hunt cube clicked (first time per load).
- `hunt_spin` — `{ tier: 'easy', rev: <n> }` on each new revolution
  crossing (rev 1..3).
- `hunt_solved` — `{ tier: 'easy', ms_since_view, spins }`.

Reward moment offers an optional **"sign it"**: a small input for a
name/handle + short note. On submit, fire `hunt_signed`
`{ tier: 'easy', name, note }`. Purely opt-in; skipping is fine.

**Dashboard panel** ("Scavenger Hunt"): for each tier, list finders with
their fingerprint already in the DB (city · org · device · referrer ·
timing) joined by `sid`, plus any signatures. Backend adds a query over
`type IN ('hunt_view','hunt_solved','hunt_signed')`; no schema change
(custom fields already land in the `data` JSON column).

## Out of scope (next design cycle)

- Medium and hard puzzles (mechanics TBD).
- The `/found` final reward page and full-chain completion state.
- Any change to raw-IP handling (stays hashed).

## Risks / notes

- Layout reshuffle changes cube positions users may have learned. Acceptable
  for a personal site; it is the point of the feature.
- Revolution counting uses cumulative *absolute* angular travel: sum
  `|dtheta|` across drags; every `2*PI` of travel = one revolution. Any
  active spinning advances it (forgiving, matches "you might do it by
  accident"); only sub-pixel jitter is ignored via the existing
  `dragDistance > 3` threshold. Covered by the state-machine test.
- Shatter/crack is an SVG overlay on one cube; must not interfere with the
  depth-sorted render or the focus/scroll handlers.

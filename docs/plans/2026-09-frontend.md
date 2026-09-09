# Plan: Front end for players who don't use a terminal

**Status:** active (implementation in progress)
**Owner:** Alec + Claude session
**Created:** 2026-09-09
**Last updated:** 2026-09-09

## Goal

A PoE player with a Path of Building build opens one page, pastes their
build code (or imports a character), says what they want more of, waits about
a minute, and gets back a new build code plus a clear picture of what changed
and why. No terminal, no flags, no Python knowledge.

## Evidence

- The CLI works well now (v0.10: ~1 minute for a 10-step greedy run, results
  verified against PoB) but its surface is 20 flags and a JSON summary.
  `docs/USER_GUIDE.md` is the current onboarding and it is still a CLI guide.
- The optimizer already produces everything a UI needs: before/after stats
  on the PoB-desktop scale (`RelativeEvaluation`), a per-iteration list of
  applied changes with node names and marginal gains
  (`OptimizationResult.modifications_applied`), the final node set, and the
  output code. Node coordinates for drawing the tree exist in
  `src/pob/tree_positions.py` (parsed from PoB's `tree.lua`).
- A PyQt desktop GUI was shelved at v0.5 (`src/gui/`, `docs/archive/GUI_TESTING_GUIDE.md`).
  Its tree canvas logic (zoom, pan, node classes) is a useful reference but
  the toolkit is wrong for reach: nobody installs a Qt app to try a tool.
- `src/web/` is an empty stub; `fastapi` and `uvicorn` are already listed in
  `requirements.txt`.
- Mockup: rendered in the pell visual scratchpad on 2026-09-09 using the real
  result of the fixture run (Cyclone Slayer, +42.1% DPS at 119 points), two
  layouts, with click-back questions on layout, hosting and style.

## Design

### Decisions so far

- **Layout: A, narrative** (single page top-to-bottom). Chosen from the
  scratchpad mockup on 2026-09-09. Workbench-style side rail may return as a
  desktop-only enhancement later.
- **Runs locally only** (`poe-optimizer web` on 127.0.0.1). No hosted
  version planned; the API boundary stays clean anyway so the option is not
  closed off, but no queueing, auth, or abuse controls are in scope.
- **First beat leads with account import**; paste is the secondary path
  (scratchpad click, 2026-09-09).
- **Visual direction as mocked**: PoE materials (void, ember path orange, gilt,
  parchment, blood for removals), Cinzel / Alegreya / IBM Plex Mono, tree
  diff as the single signature element.

### The experience (four beats)

1. **Your build.** Leads with account import: account name, then a list of
   that account's characters to pick from (this is what a player already
   knows, and needs no PoB round-trip). "Paste a Path of Building code" is
   the second, smaller path for private profiles and for builds that only
   exist in PoB. Private accounts need a POESESSID; the page explains where
   to find it and stores it only for the session. The page then shows a
   build card: class, level, main skill, DPS / life / EHP, points used,
   jewels found. This is the moment of trust: the numbers must match what
   the player sees in PoB.

   Caveat to design for: an imported character has no PoB config (enemy
   level, buffs, main skill selection) and no accurate PlayerStats in its
   XML, so the baseline comes from the headless engine rather than PoB
   desktop and absolute numbers may differ from what the player expects.
   The card should say "estimated" for imports and "from Path of Building"
   for pasted codes. Relative gains are sound either way.
2. **What do you want more of.** Three big choices: Damage, Survivability,
   Both. One folded row of guard-rails in plain words: "keep at least N
   life", "don't add points". Everything else (workers, iterations, swap
   candidates) stays hidden behind "more options".
3. **Working.** A live ticker of applied changes as they happen ("Swapped
   Vigour for Attack Speed and Accuracy, +3.6%"), a progress meter, the
   candidate count. Runs are ~1 minute, so this is short but must feel alive.
4. **Result.** The tree diff is the hero: real tree geometry, removed nodes
   ghosted, added nodes glowing on the path, the headline gain as one big
   number. Below it: four stats before/after, "Copy new build code", the
   ordered list of changes, and an honest note when something got worse
   ("Life dropped 8.6%. Re-run with Survivability or a life floor").

### Visual direction

Taken from the subject's own materials rather than a generic dark dashboard:
the tree's void background, PoB's allocated-path orange, PoE's gold trim and
parchment text, PoE's rarity red for removals. Cinzel small caps for
headings (the Fontin SmallCaps feel), Alegreya for body, IBM Plex Mono for
numbers and codes. One signature element: the tree diff. Everything else
quiet.

### Architecture

Keep a hard boundary between the optimizer and the UI so the same front end
works locally today and hosted later.

```
browser (static SPA, no build step)  <-- HTTP/SSE -->  FastAPI app (src/web)
                                                           |
                                                     JobRunner (thread)
                                                           |
                                              GreedyTreeOptimizer + IncrementalCalculator
                                                           |
                                                     PoBWorkerPool (luajit x N)
```

API (all JSON):

| Method | Path | Purpose |
|---|---|---|
| `GET /api/accounts/{name}/characters` | optional `X-POESESSID` header | List characters (name, class, level, league) for the picker. |
| `POST /api/builds` | body: `{account, character}` or `{code}` or `{xml}` | Import/decode, return build card (class, level, skill, stats, points, jewels, tree version, `stats_source`: "pob" or "estimated") and a `build_id`. |
| `POST /api/jobs` | `{build_id, objective, min_life?, allow_point_change?, max_point_change?, iterations?}` | Start an optimisation. Returns `job_id`. One job at a time locally; a queue when hosted. |
| `GET /api/jobs/{id}/events` | SSE | `iteration` events (`{n, name, removed, added, masteries, marginal_pct, cumulative_pct, points}`), `candidates` counts, `done`, `error`. |
| `GET /api/jobs/{id}` | | Final result: before/after stats, changes, node sets, `pob_code`, `xml`. |
| `GET /api/tree/{version}` | | Node positions + edges + names/types for drawing, cached, gzipped. |
| `POST /api/jobs/{id}/cancel` | | Stop early; the best tree so far is still returned. |

Optimizer changes needed (small, and useful to the CLI too):

- A progress callback on `GreedyTreeOptimizer.optimize(...)` (`on_iteration`,
  `on_candidates`) instead of only tqdm; the CLI's progress bar becomes one
  subscriber.
- A `cancel` flag checked between iterations.
- `OptimizationResult` gains `final_nodes`, `final_masteries` and, per
  modification, the resolved `removed`/`added` node ids and names (the data is
  already in `DeltaEvaluation`, it just isn't kept).
- Life / EHP floors enforced in candidate selection (top of `docs/BACKLOG.md`
  already); the UI's "keep at least N life" needs it.

Front end: a single `index.html` + one JS module + one CSS file served by
FastAPI from `src/web/static/`. No bundler, no Node toolchain, so it ships
inside the Python package and `pip install -e .` is the whole install. The
tree is an SVG built client-side from `/api/tree/{version}` (about 3,400
nodes; fine for SVG with a viewBox and pan/zoom). If the SPA outgrows this,
moving to Vite + Preact is a contained change behind the same API.

Launch: `poe-optimizer web` starts uvicorn on 127.0.0.1, prints the URL and
opens the browser. Workers start lazily on the first job so the page is up in
under a second.

### Hosting

Out of scope (decided 2026-09-09). If it ever comes back, the additions would
be a job queue with per-IP limits (each run pins ~6 cores for a minute),
build-code size limits, and result expiry. PoB is MIT, so a server-side
engine would be fine licence-wise.

### Alternatives considered

- **Revive the PyQt GUI.** Rejected: install burden, no path to hosted, and
  the tree canvas would have to be redone anyway for the new result model.
- **Electron/Tauri bundle.** Rejected for now: packaging Python + luajit +
  the PoB data (~150 MB) is a project of its own; a local web app gives the
  same UX to anyone who can `pip install`.
- **Full React/Vite SPA from day one.** Rejected: a build step and a Node
  toolchain for three screens. Revisit if the UI grows (tree editing,
  multiple specs).

## Interface contracts

```python
# src/optimizer/tree_optimizer.py
class GreedyTreeOptimizer:
    def optimize(
        self, build_xml: str, objective: str = "dps",
        allow_point_increase: bool = True,
        on_iteration: Optional[Callable[[IterationEvent], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> OptimizationResult: ...

@dataclass
class IterationEvent:
    iteration: int
    name: str
    removed: List[Tuple[int, str]]   # (node_id, name)
    added: List[Tuple[int, str]]
    masteries: Dict[int, int]
    marginal_pct: float
    cumulative_pct: float
    points_used: int
    candidates_evaluated: int
    elapsed_s: float
```

```python
# src/web/app.py
def create_app(pob_path: Optional[Path] = None, workers: Optional[int] = None) -> FastAPI: ...
# src/web/jobs.py
class JobRunner:
    def submit(self, build_xml: str, options: JobOptions) -> str
    def events(self, job_id: str) -> Iterator[dict]   # SSE source
    def result(self, job_id: str) -> Optional[JobResult]
    def cancel(self, job_id: str) -> None
```

## Work breakdown and file ownership

| Step / stream | Owns (may modify) | Depends on | Verification |
|---|---|---|---|
| A. Optimizer events + cancel + richer result | `src/optimizer/tree_optimizer.py`, `tests/test_incremental_optimizer.py` | - | existing tests + one test asserting events fire with names |
| B. Tree data endpoint model | `src/pob/tree_positions.py` (add edge/name export), `src/web/tree_data.py`, `tests/test_tree_data.py` | - | JSON for 3_29 has 3,396 nodes, all with x/y |
| C. Web app + job runner | `src/web/app.py`, `src/web/jobs.py`, `tests/test_web_app.py` | A contract | TestClient: submit fixture, stream events, fetch result |
| D. Static front end | `src/web/static/*` | B, C contracts | manual run on the fixture; screenshot in the plan |
| Integration | `src/cli/commands/web.py`, `src/cli/main.py`, `README.md`, `docs/USER_GUIDE.md` | A-D | `poe-optimizer web` end to end on the 3.29 fixture |

A and B are independent and can run as parallel streams. C depends only on
A's contract; D on B's and C's. Integration is serial.

## Verification

- `venv/bin/pytest tests/test_web_app.py tests/test_tree_data.py -q`
- `poe-optimizer web` -> paste `tests/fixtures/builds/cyclone_slayer.txt`
  -> Damage -> result within ~90 s showing +40% and the tree diff; the copied
  code imports into PoB desktop and matches the hover deltas.
- Phone width (400px): Layout A stacks; the tree is pannable.

## Status log

- 2026-09-09: created. Mockup with two layouts rendered in the visual
  scratchpad from real fixture data.
- 2026-09-09: layout A (narrative), local-only hosting, and the mocked visual
  direction all chosen via scratchpad clicks. Plan is active; next step is
  stream A (optimizer events + cancel) and stream B (tree data endpoint) in
  parallel.
- 2026-09-09: account import chosen as the leading input (paste secondary).
- 2026-09-09: "go build it" clicked. Streams A and B started as parallel
  agents; C and D written against the contracts in the orchestrating session.

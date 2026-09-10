# Architecture

## Overview

```
                 +-----------------------------+
   PoB code /    |  CLI  (src/cli)             |
   XML / GGG --->|  optimize / analyze / diff  |
   account       |  jewels / encode / decode   |
                 +--------------+--------------+
                                |
                 +--------------v--------------+
                 |  Optimizers (src/optimizer) |
                 |  GreedyTreeOptimizer        |   candidates as TreeDelta
                 |  GeneticTreeOptimizer       |   (add / remove / masteries)
                 |  ConstraintSet              |
                 +--------------+--------------+
                                |
                 +--------------v--------------+
                 |  IncrementalCalculator      |   ratio extrapolation ->
                 |  (src/pob)                  |   RelativeEvaluation
                 +--------------+--------------+
                                |
                 +--------------v--------------+
                 |  PoBWorkerPool              |   idle-queue of N workers
                 |  PoBWorker x N              |   raw pipe, own line reader
                 +--------------+--------------+
                                |  stdin/stdout, one JSON line per request
                 +--------------v--------------+
                 |  luajit evaluator_batch.lua |   PoB HeadlessWrapper,
                 |  (cwd PathOfBuilding/src)   |   build loaded once per worker
                 +-----------------------------+
```

Supporting data comes from the PoB submodule at import time:
`src/pob/tree_parser.py` builds a `PassiveTreeGraph` (3,287 nodes for 3.27, 3,396 for 3.29) from
`PathOfBuilding/src/TreeData/<version>/tree.lua`; `mastery_optimizer.py`
builds the mastery database from the same file; `tree_version.py` picks the
version from the build XML or the newest available.

## Evaluation: why ratios

Headless PoB calculates some builds differently from the desktop app (the
fixture build reports 4.08M Lua DPS vs 3.55M in the XML's PlayerStats). The
*relative* effect of a tree change is reliable, so every evaluation is:

```
estimated_stat = accurate_stat_from_xml * (candidate_lua / baseline_lua)
```

`RelativeEvaluation` (in `relative_calculator.py`) carries the baseline, the
ratios, the extrapolated values and the percent changes. The optimizers only
ever compare percent changes.

## Session protocol (`src/pob/evaluator_batch.lua`)

One request line in, one JSON line out. PoB's console output is redirected to
stderr so stdout is protocol-only.

| Request | Cost | Effect |
|---|---|---|
| `LOAD <base64 xml>` | 1.5-2 s (PoB 2.67); 3-5 s (2.60) | Parse the build, make its tree the *session base*, build PoB's misc calculator. Reply includes `stats`, `pointsUsed`, `nodes`. |
| `DELTA {"add":[..],"remove":[..],"masteries":{id:effect}}` | 0.04-0.1 s warm (up to 0.3 s on 2.60) | Evaluate a change to the base **without applying it**. `remove` takes the node and every node that depends on it for connectivity (`node.depends`, same as unallocating in the UI). `add` allocates the node and its shortest path. Masteries are patched in temporarily. Reply includes `stats`, `pointsUsed`, `added`, `removed`, `nodes`. |
| `SET {"nodes":[..],"masteries":{..}}` | 0.15-0.5 s | Replace the base tree in place (`PassiveSpec:ImportFromNodeList`) and evaluate it. |
| `<base64 xml>` | 1-5 s | Legacy full reload and evaluation. Replaces the session build. |
| `IMPORT <base64 json>` | 2-5 s | Feed a character object (`name, class, league, level, equipment, jewels, passives`) to PoB's own ImportTab; reply carries PoB's serialised XML (base64) and stats. Used for account imports so jewels, cluster nodes, tattoos and bloodlines match PoB desktop. |
| `PING` / `EXIT` | - | Health check / clean shutdown. |

`DELTA` uses `CalcsTab:GetMiscCalculator()`, the code path that powers PoB's
node hover tooltips: a fresh `calcs.initEnv(build, "CALCULATOR", override)`
with `addNodes` / `removeNodes` overrides, no XML parsing, no item or gem
reprocessing. Results are identical to a full reload for the same tree
(verified in `tests/test_worker_pool.py`).

## Python side

### `worker_pool.py`

- `PoBWorker` owns one `luajit` subprocess. Its stdout is read as raw bytes
  with an internal buffer and `select()` on the file descriptor. (The earlier
  implementation combined `select()` with a buffered text pipe, which lost
  lines: the buffer slurped several lines, `select` then saw an empty fd, the
  request timed out, and the next request read the previous reply.)
- On timeout or protocol error the worker is killed rather than reused, so a
  late reply can never be attributed to a later request.
- `PoBWorkerPool` hands workers out through an idle `Queue`; `evaluate_deltas`,
  `evaluate_trees`, `evaluate_batch` fan out over a `ThreadPoolExecutor` sized
  to the number of workers. `load_session` and `set_tree` broadcast to every
  worker so they share a base tree. Dead workers are restarted and the session
  (`LOAD` + `SET`) replayed onto them.

### `incremental_calculator.py`

`IncrementalCalculator` wraps the pool with optimisation semantics:

- `load(xml)` -> baseline; remembers accurate XML stats and Lua baseline.
- `evaluate_deltas({name: TreeDelta})` -> `{name: DeltaEvaluation}` where the
  evaluation's baseline is the **current** base tree (so `dps_change_percent`
  is the marginal effect) and `nodes` / `points_used` describe the resulting
  tree.
- `commit(nodes, masteries)` -> makes a candidate the new base (SET on all
  workers).
- `evaluate_trees` (GA) and `evaluate_xmls` (jewel/item candidates, full
  reload) share the same pool.
- `evaluate_current_vs_original()` for the final report.

### Optimizers

**Greedy** (`tree_optimizer.py::_optimize_incremental`), per iteration:

1. Candidates: every alternative effect on allocated mastery nodes; removal
   of every removable node (not class start, ascendancy, protected jewel or
   cluster nodes); allocation of every unallocated neighbour (masteries with
   each effect).
2. Evaluate all in parallel (~250 deltas, 2-3 s on 8 workers).
3. Pair the `swap_candidates` best removals with the best additions into
   remove+add swaps (point-neutral), evaluate those.
4. Filter by point budget (`points_used` from PoB, `ConstraintSet`), pick the
   best marginal improvement, `commit` it, repeat until the best candidate is
   below `min_improvement`.
5. Jewel socket / Thread of Hope / cluster candidates (opt-in) are XML
   candidates evaluated with a full reload; if one wins, the session is
   reloaded from that XML.

The legacy loop (`--no-incremental`) builds one XML per candidate and reloads
PoB for each; it is kept as a fallback and for comparison.

**Genetic** (`genetic_optimizer.py`): individuals are XML strings; in
incremental mode only their node list and mastery map are sent (`SET`). With
`optimize_jewel_sockets` the XMLs differ in items too, so full reloads are
used instead.

### Constraints (`constraints.py`)

`PointBudgetConstraint.from_level(level)` allows `level + 23` points
(level-1 from levelling, 22 quest, 2 bandit). Point counting excludes class
start and ascendancy nodes (`PassiveTreeGraph.count_passive_points`), matching
PoB's "points used". The incremental path uses PoB's own `pointsUsed`.

## Web UI (`src/web`)

`create_app()` builds a FastAPI app: `POST /api/builds` (code / XML /
account import -> build card), `GET /api/accounts/{name}/characters`,
`POST /api/jobs`, `GET /api/jobs/{id}/events` (Server-Sent Events replayed
from a per-job history so a reconnecting tab misses nothing), `GET
/api/jobs/{id}`, `POST /api/jobs/{id}/cancel`, `GET /api/tree/{version}`.
`JobRunner` runs one optimisation at a time on a background thread, adapting
`optimize(on_iteration=..., should_cancel=...)` to the job model. The page in
`static/` is plain HTML/CSS/JS; the tree is an SVG built in the browser from
the tree-data export, clipped to the build's bounding box with pan/zoom.
Loopback only, no auth, by design.

## Import configuration (`src/ggg/config_rules.py`)

An account import has no PoB config. `apply_default_config` writes one the
way poe.ninja does (https://poe.ninja/poe1/builds/pob-rules, transcribed
as 92 `Rule` entries): pinnacle boss and active flasks unconditionally,
then each config variable only when a *source* line for it exists in the
build's item mods, gem names, allocated passive names/stats, mastery
effects or ascendancy; a few are "everyone" rules (crit recently, enemy
chilled/ignited/bleeding, one nearby enemy). Rules can carry numeric
values (Rage 100, Wither 15, Virulence 40) or list values (Pride MAX), an
`unless` clause (crit recently unless Resolute Technique) and `requires`
(cold snap bypass needs frenzy charges). Lines that only apply on kill are ignored. Each applied
assumption carries its source line; the web UI shows them as toggles and
re-evaluates on change.

## Build representation

- `codec.py`: PoB import code <-> XML (zlib + base64url).
- `modifier.py`: `modify_passive_tree_nodes` (incremental edits),
  `set_passive_tree` (write a complete node set + masteries),
  `get_passive_tree_summary`.
- `xml_parser.py`: PlayerStats from the XML (accurate baseline).
- `jewel/`: `JewelRegistry.from_build_xml` classifies jewels (timeless
  including Heroic Tragedy and the Abyss ones, cluster, unique) and returns
  protected node ids; `socket_optimizer.py`
  enumerates socket moves; `cluster_subgraph.py` models cluster jewel graphs.

## Known limitations of the engine

- Abyss timeless jewels (3.29) conquer nodes by a socket-keyed table that
  PoB rebuilds in `BuildAllDependsAndPaths`. `SET` and `LOAD` reflect them
  exactly; `DELTA` reuses the base tree's conquests, so a removal that
  changes the path from Zorath's socket to the class start is only exact once
  committed. The greedy loop commits every accepted move, so the final result
  is exact.

- Timeless jewel notable transformations: PoB prints `Missing LUT` for
  Lethal Pride on the fixture build; notable rerolls are therefore not
  reflected. Small-node transformations are.
- Headless absolute values are wrong for some mechanics (accuracy, triggers);
  ratios are used for that reason. Gem optimisation is the most affected (see
  `docs/BACKLOG.md`).
- The mastery database misses a few nodes (`Mastery node N not found in
  database` warnings); PoB still applies the effect.

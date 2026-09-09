# poe-optimizer — Claude Code project guide

Path of Exile passive-tree optimizer that drives Path of Building's real Lua
calculation engine from Python. Read this first; it is the entry point for
every agent session. Deeper material is linked at the end.

## What the tool does

`poe-optimizer optimize build.xml` takes an existing PoB build, loads it into a
pool of persistent PoB worker processes, and greedily (or genetically) searches
for passive-tree changes that improve DPS / life / EHP, scoring every candidate
with PoB's own incremental calculator. Output is an importable PoB code.

## Ground rules

- **Never edit `PathOfBuilding/`.** It is a git submodule (currently
  v2.67.2, trees through 3.29). Update it only by checking out a release tag
  and running the full suite; PoB API changes surface as Lua errors in
  `tests/test_worker_pool.py`. Any behaviour we
  need from PoB is achieved from our Lua evaluators in `src/pob/*.lua` or from
  Python. Check `git status PathOfBuilding/` is clean before committing.
- **Use the venv.** `venv/bin/python3`, `venv/bin/pytest`. There is no bare
  `python` on this machine.
- **Update the README changelog before every push.** `README.md`, section
  `## Changelog`. Add a version entry or extend the current one.
- **Keep the fast path fast.** Anything on the per-candidate evaluation path
  (`evaluator_batch.lua`, `worker_pool.py`, `incremental_calculator.py`,
  candidate generation in the optimizers) must be measured before and after
  a change. See `docs/PERFORMANCE.md` for the numbers and how to reproduce them.
- **No emojis in code, CLI output, or docs** unless asked.

## Commands

```bash
venv/bin/pytest tests/ -q                       # full suite (~4 min, spawns luajit workers)
venv/bin/pytest tests/test_constraints.py -q    # fast unit subset
venv/bin/python3 -m src.cli.main optimize tests/fixtures/builds/cyclone_slayer.xml --iterations 5
venv/bin/python3 -m src.cli.main analyze build.xml
venv/bin/python3 -m src.cli.main setup          # verify luajit + submodule
```

Tests that need luajit and the submodule are skipped automatically when either
is missing (`needs_pob` marker in `tests/test_worker_pool.py`).

## Architecture in one screen

```
CLI (src/cli)  ->  Optimizers (src/optimizer)  ->  IncrementalCalculator (src/pob)
                                                          |
                                              PoBWorkerPool: N x luajit
                                              running src/pob/evaluator_batch.lua
                                              (PoB HeadlessWrapper, build loaded once)
```

- **Session protocol** (`evaluator_batch.lua`): `LOAD <xml>` once, then
  `DELTA {add,remove,masteries}` (~0.05-0.2 s, PoB's node-hover calculator) or
  `SET {nodes,masteries}` (~0.15-0.5 s, commits a new base tree). Legacy bare-XML
  lines still do a full reload (1-5 s). Details: `docs/ARCHITECTURE.md`.
- **Ratio extrapolation**: headless PoB gets absolute numbers wrong for some
  builds, so every result is `xml_accurate_stat * (candidate_lua / baseline_lua)`.
  `RelativeEvaluation` carries both the ratio and the extrapolated values.
- **Greedy optimizer** (`tree_optimizer.py`, `_optimize_incremental`): per
  iteration evaluates every mastery alternative, every removable node, every
  adjacent addition, then pairs the best removals with the best additions into
  point-neutral swaps. Point budget comes from `constraints.py`.
- **Genetic optimizer** (`genetic_optimizer.py`): individuals are node lists;
  scored with `SET` on the same worker pool.
- **Legacy paths** (`RelativeCalculator`, `BatchCalculator`, ProcessPool
  reload) still exist behind `--no-incremental` and for the gem optimizer.

## Where things live

| Area | Files |
|---|---|
| Lua bridge | `src/pob/evaluator_batch.lua`, `src/pob/worker_pool.py`, `src/pob/incremental_calculator.py` |
| Build XML | `src/pob/codec.py` (PoB code <-> XML), `src/pob/modifier.py`, `src/pob/xml_parser.py` |
| Tree data | `src/pob/tree_parser.py` (graph from PoB `tree.lua`), `src/pob/tree_version.py`, `src/pob/mastery_optimizer.py` |
| Jewels | `src/pob/jewel/` (registry, timeless, cluster, radius, socket optimizer) |
| Optimizers | `src/optimizer/tree_optimizer.py`, `genetic_optimizer.py`, `constraints.py`, `gem_optimizer.py` |
| CLI | `src/cli/main.py`, `src/cli/commands/*.py` |
| GGG import | `src/ggg/` |
| Fixture builds | `tests/fixtures/builds/cyclone_slayer.xml` (level 96 Slayer, 119 points, Lethal Pride, 3.27 tree) and `cyclone_slayer_3_29.xml` (same build on the newest tree) |

Dead or dormant: `src/gui/` (shelved PyQt GUI), `src/web/`, `src/ml/`,
`src/analyzer/`, `src/models/` are empty stubs.

## How we work (agentic workflow)

The full process is in `docs/DEVELOPMENT.md`. The short version:

1. **Orient**: read this file, `git status`, `git log --oneline -10`,
   `docs/BACKLOG.md`. Recalled memories are hints, not facts; verify.
2. **Plan before non-trivial work**: write or update a plan in `docs/plans/`
   using `docs/plans/TEMPLATE.md` (goal, evidence, interface contracts, file
   ownership, verification). Small fixes do not need a plan.
3. **Measure, then change**: for performance work, capture a baseline with the
   scripts in `docs/PERFORMANCE.md` before touching code.
4. **Small verified steps**: run the relevant tests after each step; run the
   full suite before committing.
5. **Parallel agents** only for independent streams with disjoint file
   ownership declared in the plan; integration into `tree_optimizer.py` /
   `genetic_optimizer.py` / CLI is done serially afterwards.
6. **Review**: `/code-review` (or the `/review` skill) on the diff before a PR;
   record open findings in `docs/BACKLOG.md`, not in ad-hoc files.
7. **Ship**: changelog entry, conventional commit, push only when asked.

## Docs map

- `docs/README.md` — index of all docs and which are current
- `docs/ARCHITECTURE.md` — modules, data flow, worker protocol
- `docs/DEVELOPMENT.md` — agentic workflow, testing, conventions
- `docs/PERFORMANCE.md` — measured timings, bottleneck history, how to benchmark
- `docs/BACKLOG.md` — open work, known issues, open review findings
- `docs/USER_GUIDE.md`, `docs/TROUBLESHOOTING.md`, `docs/CONFIGURATION.md` — user-facing
- `docs/archive/` — completed plans and reviews, kept for history

# Performance

All numbers below were measured on the fixture build
(`tests/fixtures/builds/cyclone_slayer.xml`: level 96 Slayer, 119 passive
points, Lethal Pride timeless jewel) on an Apple Silicon Mac (M4, 4P+6E
cores), LuaJIT 2.1, using `scripts/benchmark_evaluation.py`. Re-run that
script before quoting new figures.

## Per-evaluation cost (one worker)

Two PoB versions, same machine (load average ~4 during the 2.67.2 runs):

| Operation | PoB v2.60.0 | PoB v2.67.2 | Notes |
|---|---|---|---|
| luajit worker start (PoB init, tree data) | ~2.0 s | 1.3-2.2 s | once per worker, all workers start in parallel |
| Full reload of a build XML (legacy path) | 3.3-4.5 s | 1.1-2.2 s | reparses items, gems, tree, config |
| `LOAD` (session base) | ~4.5 s cold, ~2.5 s warm | 1.5-2.0 s | once per optimisation run |
| `DELTA` add / remove / mastery | 0.17-0.23 s cold, ~0.05-0.1 s warm | 0.04-0.08 s | PoB's incremental "misc calculator" |
| `SET` (commit a new base tree) | ~0.5 s | 0.13-0.16 s | once per accepted improvement |

PoB 2.61-2.67 made tree processing and full loads roughly 2-3x cheaper on
their own; keep the submodule current.

## Pool throughput (8 workers)

| Operation | Wall time | Effective |
|---|---|---|
| 40 `DELTA`s | 0.5 s | ~13 ms per candidate |
| 80 `DELTA`s, 4 / 6 / 10 workers | 1.1 / 0.83 / 0.80 s | 14 / 10 / 10 ms per candidate: no gain past the performance cores |
| 8 full reloads | 1.8 s | ~225 ms per build |
| Greedy iteration, ~250 single candidates + 64 swaps | 3-5 s | |

## End-to-end (CLI defaults, greedy, `--iterations 10`, 8 workers)

| | Time | Result on fixture |
|---|---|---|
| v0.10 incremental path, PoB 2.60.0 | **54 s** total (incl. ~8 s start-up) | +42% DPS at constant points |
| v0.10 incremental path, PoB 2.67.2, fixture on the 3.29 tree | 91 s (load average 4) | +41.6% DPS at constant points |
| v0.9.1 default path (ProcessPool, fresh luajit per candidate) | 41 s per iteration, **0 candidates succeed** | one cold evaluation is 13.5 s; ten in parallel overrun the 30 s subprocess timeout |
| v0.9.1 `use_batch_evaluation=True` | >60 min per iteration (estimated from 3.5 s x ~1,100 reloads) and results misattributed | see "History" |

Variance: the same 10-iteration CLI run measured 52 s, 175 s and 361 s on the
same day. The slow runs coincided with another process pinning a core (Steam
at 100%) and load averages of 8-9 on a 4P+6E core M4. Quote numbers from an
idle machine, and do not expect more workers than performance cores to help.

## What made it slow (history, for future reference)

Measured while diagnosing v0.9.1; kept here so nobody re-introduces them.

1. **Serialised "parallel" pool.** `PoBWorkerPool.evaluate` held a pool-wide
   lock around the whole evaluation, so N workers gave 1x throughput.
2. **Lost responses.** `select()` on a *buffered* text pipe: the buffer read
   several lines at once, `select` then reported nothing to read, the request
   timed out after 30 s, and the *next* request consumed the stale reply.
   Every batch-mode result was attributed to the previous candidate.
3. **Mastery brute force per candidate.** In batch mode each of ~40 tree
   candidates re-evaluated every mastery effect (~26 full reloads), so one
   greedy iteration was ~1,100 full reloads.
4. **Full reload per candidate.** 3-5 s each, when PoB's own hover calculator
   does the same comparison in ~0.2 s without touching the XML.
5. **Wrong point counting.** The constraint system counted class-start and
   ascendancy nodes as passive points, so the fixture build "violated" its
   own budget and every candidate was rejected.
6. **Subprocess timeout too tight.** The one-shot evaluator (`caller.py`)
   used a 30 s timeout while a cold luajit + evaluation takes ~13 s alone;
   with `os.cpu_count()` of them in parallel, all timed out. Now 120 s.
7. **Arbitrary candidate set.** Only the first 20 allocated nodes / first 20
   neighbours were tried, no point-neutral swaps, and improvements were
   measured against the original build instead of the current tree.

## Where the time goes now

For a greedy run on 8 workers: ~2 s worker start, ~2.5 s `LOAD`, then per
iteration ~250 `DELTA`s (~2.5 s), ~64 swap `DELTA`s (~0.8 s), one `SET`
(~0.5 s) and a little Python. Python-side XML work (`modify_passive_tree_nodes`
~6 ms, `get_passive_tree_summary` ~2 ms) is negligible.

Remaining levers, roughly in order of value:

- **Fewer, better candidates.** Removals of interior path nodes are almost
  always terrible (they prune whole branches); ranking removals by `removed`
  count or pruning by a cheap heuristic would cut ~40% of deltas.
- **Reuse hover results across iterations.** Most single-node deltas are
  unchanged after a swap elsewhere on the tree; caching by (node, base tree
  hash) would skip most of the ~250 re-evaluations.
- **Cheaper `DELTA`.** `calcs.initEnv` rebuilds the environment on every call
  (~150 ms floor). PoB's `getNodeCalculator` with `accelerate` flags can reuse
  cached player/enemy DBs; not yet tried.
- **Worker count.** Workers are CPU-bound; more workers than physical cores
  does not help. `--workers` defaults to `os.cpu_count()`.

## Reproducing the numbers

```bash
venv/bin/python3 scripts/benchmark_evaluation.py --workers 8
time venv/bin/python3 -m src.cli.main optimize tests/fixtures/builds/cyclone_slayer.xml --iterations 10
venv/bin/python3 scripts/compare_optimizers.py       # greedy vs genetic on the fixture
```

Accuracy: the incremental path returns exactly the values PoB shows on node
hover. A change of `+X%` here is `+X%` in PoB desktop for the same tree edit,
subject to the headless-engine caveats in `docs/ARCHITECTURE.md`.

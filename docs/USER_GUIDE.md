# User Guide

How to install and use `poe-optimizer` from the command line. For what the
tool does and does not do, see the README; for how it works, see
`ARCHITECTURE.md`.

## Install

```bash
git clone --recursive https://github.com/alecrivet/poe-optimizer.git
cd poe-optimizer
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -e .
brew install luajit                 # macOS; Ubuntu: sudo apt install luajit
poe-optimizer setup                 # verifies luajit + PoB submodule
```

If you cloned without `--recursive`: `git submodule update --init --recursive`.

## Get a build in

Any of these work as the `INPUT` argument:

- a PoB XML file (`build.xml`)
- a PoB import code, pasted or in a text file
- `-` to read from stdin
- a GGG account character: `poe-optimizer account import MyAccount MyChar -o build.xml` (`poe-optimizer account list MyAccount` shows characters)

Export from PoB: Import/Export Build tab, "Generate" a code, copy it.

The build should be complete (gear, gems, config, main skill selected). The
optimizer only changes the passive tree; everything else is held fixed.

## Optimize

```bash
poe-optimizer optimize build.xml -o optimized.xml
```

What happens:

1. PoB workers start (one per CPU core, ~2 s) and load the build.
2. Each iteration scores every mastery alternative, every removable node,
   every adjacent unallocated node, and remove+add swaps between the best of
   those, then applies the single best change.
3. It stops when no change improves the objective by at least 0.1%, or after
   `--iterations` improvements (default 50).
4. The result is written as XML and printed as a PoB code.

A 10-iteration run on a level 96 build takes about a minute on 8 cores.

### Options you will actually use

| Flag | Meaning |
|---|---|
| `--objective dps\|life\|ehp\|balanced` | What to maximise. `balanced` averages the three. |
| `--iterations N` | Max number of improvements to apply (greedy). |
| `--allow-point-change` | Let the point count grow above the current build (off by default; swaps still happen). |
| `--max-point-change N` | How far the point count may move from the original (default 5). |
| `--max-points N` / `--disable-constraints` | Override or disable the level-based point budget. |
| `--no-masteries` | Leave mastery selections alone. |
| `--workers N` | PoB worker processes (default: CPU count; more than physical cores does not help). |
| `--algorithm genetic --generations G --population-size P` | Population search instead of greedy (experimental). |
| `--pob-code` | Print only the PoB code (for piping). |
| `--json` | Machine-readable output. |
| `poe-optimizer -v optimize ...` | Verbose: per-iteration candidate scores. |

Legacy path: `--no-incremental` reloads the build XML for every candidate
(minutes per iteration). Only useful for comparison.

### Reading the output

```
Optimizing: 10/10 ... improvement: +42.12%
Iter 1: applied Swap: Remove node 1325 (Golem's Blood) / Add node 56355 (Melee Critical Strike Chance)
```

Each applied modification names the nodes involved. The final summary shows
DPS / life / EHP before and after on the PoB desktop scale (the headless
engine's ratio applied to the XML's own stats). Import the printed code into
PoB and confirm; the tool's numbers are PoB's node-hover numbers, so they
should match the tooltip deltas exactly.

If the result trades away defence you care about, re-run with
`--objective balanced` or `life`. Per-stat floors (`--min-life`) are on the
backlog and currently have no effect.

## Other commands

```bash
poe-optimizer analyze build.xml            # stats, allocated nodes, masteries
poe-optimizer jewels build.xml             # jewel types and protected nodes
poe-optimizer diff original.xml optimized.xml
poe-optimizer decode "<code>" -o build.xml
poe-optimizer encode build.xml
```

Add `--json` to any of them for scripting.

## Things to know

- **Jewels are protected.** Sockets holding jewels, cluster jewel subgraphs
  and timeless-jewel areas are never deallocated. Socket moves are opt-in in
  the Python API (`optimize_jewel_sockets=True`) and cost a full reload each.
- **Point budget.** The cap is `level + 23` (level-ups, 22 quest points, 2
  bandit points) counting only regular passives. A build already at the cap
  can still improve through swaps.
- **Timeless jewel notables.** Headless PoB cannot load the notable lookup
  table for some timeless jewels (`Missing LUT` on stderr), so notable rerolls
  are not reflected. Small-node changes are.
- **Ascendancy** is never changed.
- **Empty trees** are not supported as a starting point; the search is local.

## Troubleshooting

See `TROUBLESHOOTING.md`, "Worker pool" section, for the common failures
(`luajit` missing, budget filtering everything, slow legacy fallback).

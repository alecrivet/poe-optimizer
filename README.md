# Path of Exile Build Optimizer

A passive tree optimization tool for Path of Exile that uses Path of Building's calculation engine to automatically improve character builds.

## Overview

This tool takes a Path of Building export code, analyzes the passive tree, and uses optimization algorithms to find better node allocations. It leverages PoB's actual calculation engine for accurate DPS/defense numbers, supports jewel mechanics (timeless, cluster, unique), and outputs an optimized PoB code you can import directly.

**Key Features:**
- Uses PoB's real calculation engine (not approximations)
- Fast: the build is loaded into persistent PoB workers once, then every
  candidate is scored with PoB's own incremental calculator (~0.2 s each,
  in parallel). A 10-iteration greedy run takes about a minute.
- Two optimization algorithms: Greedy (default) and Genetic (experimental)
- Point-neutral swaps (remove one node, add another) so builds at max level
  still improve
- Supports timeless jewels, cluster jewels, and unique jewels
- Protects jewel-modified nodes from optimizer changes
- CLI tool for scripting and automation
- Outputs importable PoB codes

## What This Does / What This Doesn't Do

| What it does | What it doesn't do |
|---|---|
| Optimize passive node allocation on an existing tree | Create builds from scratch |
| Use PoB's real Lua calculation engine for accurate stats | Approximate stats with its own formulas |
| Protect jewel sockets, cluster subgraphs, and timeless jewels | Optimize jewel contents or timeless seeds |
| Select optimal mastery effects per node | Optimize ascendancy choices |
| Import characters directly from GGG's API | Interact with the game client |
| Auto-detect tree version from PoB data | Require manual version updates each patch |
| Output importable PoB codes and XML | Optimize items, gems, or skill links |

## Best Use Case

**This tool is designed for optimizing existing builds, not creating new ones from scratch.**

The optimizer works best when you have:
- An existing character build with an allocated passive tree
- A working PoB setup with gear, gems, and configuration
- A desire to find incremental improvements to your current tree

The algorithms analyze your current node allocations and search for better alternatives by adding, removing, or swapping nodes while maintaining tree connectivity.

**Note:** The tool has not been tested or validated with empty/minimal passive trees as a starting point. Starting from scratch would require exploring an exponentially larger search space and may not produce meaningful results. For new builds, we recommend using existing build guides or PoB's manual planning, then using this tool to fine-tune the result.

## Installation

```bash
# Clone with submodules (required for PoB engine)
git clone --recursive https://github.com/alecrivet/poe-optimizer.git
cd poe-optimizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install package
pip install -e .

# Verify installation
poe-optimizer setup
```

### Requirements

- Python 3.9+
- LuaJIT (required for PoB calculations)
- Git (for submodules)

**macOS:**
```bash
brew install luajit
```

**Ubuntu/Debian:**
```bash
sudo apt install luajit
```

**Windows:**
Download LuaJIT from https://luajit.org/download.html

## Quick Start

### In the browser

```bash
poe-optimizer web
```

Opens `http://127.0.0.1:8765`: import a character from your account or paste a
Path of Building code, choose Damage / Survivability / Both, watch the
changes land, then copy the new build code back into PoB. Everything runs on
your machine.

### From the terminal

```bash
# Analyze a build
poe-optimizer analyze build.xml

# Optimize for DPS (default)
poe-optimizer optimize build.xml -o optimized.xml

# Optimize for life
poe-optimizer optimize build.xml --objective life

# View jewel information
poe-optimizer jewels build.xml

# Compare two builds
poe-optimizer diff original.xml optimized.xml

# Get JSON output for scripting
poe-optimizer analyze build.xml --json
```

### Using PoB Codes Directly

```bash
# Decode a PoB code to XML
poe-optimizer decode "eNrtfVuT4siS..." -o build.xml

# Or pipe directly
echo "eNrtfVuT4siS..." | poe-optimizer decode - | poe-optimizer analyze -

# Encode back to PoB code
poe-optimizer encode optimized.xml
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `optimize` | Run genetic algorithm optimization on a build |
| `analyze` | Display build statistics and passive tree info |
| `diff` | Compare two builds side-by-side |
| `jewels` | Show jewel information and protected nodes |
| `encode` | Convert XML to PoB import code |
| `decode` | Convert PoB code to XML |
| `setup` | Verify installation and dependencies |
| `web` | Start the local browser UI |

### Optimization Options

```bash
poe-optimizer optimize build.xml \
  --objective dps \           # dps, life, ehp, balanced
  --algorithm greedy \        # greedy (default) or genetic
  --iterations 50 \           # Greedy: max improvements to apply
  --workers 8 \               # PoB worker processes (default: CPU count)
  --allow-point-change \      # Let the point count grow (default: no)
  --max-point-change 5 \      # Max points added/removed vs original
  --output optimized.xml \    # Output file
  --json                      # JSON output for scripting
```

`--no-incremental` falls back to reloading the build XML for every candidate
(slow; kept for comparison and as a fallback if the worker pool cannot start).

## How It Works

1. **Parse Build:** Decode PoB code and extract passive tree, jewels, items
2. **Build Graph:** Create connectivity graph of 3,287 passive nodes
3. **Identify Constraints:** Protect jewel sockets and cluster jewel subgraphs
4. **Evolve Population:** Genetic algorithm mutates and selects builds
5. **Evaluate Fitness:** Call PoB's Lua engine for accurate stat calculations
6. **Output Result:** Generate optimized PoB code

### How candidates are evaluated

The build is loaded once into a pool of persistent `luajit` processes running
PoB's headless engine. Each candidate tree change is then sent as a small
delta (`add` / `remove` / `masteries`) and scored with the same incremental
calculator PoB uses for its node hover tooltips, without reparsing the build.
Absolute numbers are extrapolated from the XML's own PlayerStats using the
Lua ratio, so results are on the PoB desktop scale. See
`docs/ARCHITECTURE.md` and `docs/PERFORMANCE.md`.

### Optimization Algorithms

**Greedy Optimizer (default)**
- Each iteration evaluates every mastery alternative, every removable node,
  every adjacent addition, and remove+add swaps built from the best singles
- Picks the best marginal improvement, commits it, repeats until nothing
  clears `min_improvement`
- Respects the level-based point budget and jewel/cluster protection
- Typical runtime: ~5 s per iteration on 8 workers, about 1 minute for 10
  iterations

**Genetic Algorithm (experimental)**
- Population-based evolution (configurable population/generations)
- Individuals are scored on the same worker pool by node list
- Explores a broader search space; current mutation operators are crude
  (see `docs/BACKLOG.md`)

## Jewel Support

The optimizer understands Path of Exile's jewel mechanics:

### Timeless Jewels
- Parses seed and variant from jewel names
- Loads PoB's legion data for node transformations
- Protects jewel socket from removal

### Cluster Jewels
- Identifies cluster jewel subgraphs (nodes with ID >= 65536)
- Protects entire subgraph from optimizer modification
- Preserves notable allocations

### Unique Jewels
- Recognizes 178 unique jewel types
- Protects socketed locations
- Passes through to PoB for effect calculation

```bash
# View all jewels and protected nodes
poe-optimizer jewels build.xml --json
```

## Utility Scripts

The `scripts/` directory contains useful utilities:

```bash
# Reproduce the evaluation timings in docs/PERFORMANCE.md
venv/bin/python3 scripts/benchmark_evaluation.py --workers 8

# Compare greedy vs genetic optimizer performance
venv/bin/python3 scripts/compare_optimizers.py

# Quick genetic optimizer test
venv/bin/python3 scripts/test_genetic_optimizer.py
```

All optimization scripts automatically save results to the `output/` directory with timestamps, including both XML files and PoB import codes.

## Project Structure

```
poe-optimizer/
├── src/
│   ├── cli/                    # Command-line interface
│   │   ├── commands/           # CLI commands (optimize, analyze, etc.)
│   │   └── formatters/         # Output formatting (console, JSON)
│   ├── pob/                    # Path of Building interface
│   │   ├── jewel/              # Jewel parsing (timeless, cluster, unique)
│   │   ├── codec.py            # PoB code encode/decode
│   │   ├── caller.py           # Python → Lua bridge
│   │   ├── worker_pool.py      # Persistent Lua worker pool for batch eval
│   │   ├── tree_parser.py      # Passive tree graph
│   │   └── modifier.py         # Build modification
│   ├── optimizer/              # Optimization algorithms
│   │   ├── genetic_optimizer.py  # Genetic algorithm with parallel eval
│   │   ├── tree_optimizer.py     # Greedy optimizer with batch eval
│   │   └── multi_objective_optimizer.py
│   ├── web/                    # Local web UI: FastAPI app, job runner, static page
│   └── visualization/          # Plotting and analysis
├── PathOfBuilding/             # PoB submodule (calculation engine)
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
└── output/                     # Optimization results (auto-generated)
```

## Development

Start with `CLAUDE.md` (project guide for agents and humans) and
`docs/DEVELOPMENT.md` (workflow). Index of all docs: `docs/README.md`.

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (integration tests need luajit + the submodule; skipped otherwise)
venv/bin/pytest tests/ -q

# Hot-path tests only
venv/bin/pytest tests/test_worker_pool.py tests/test_incremental_optimizer.py -q

# Format code
black src/ tests/
isort src/ tests/
```

## Limitations

- **Existing Builds Only:** Designed for optimizing existing builds; not tested with empty trees
- **Items/Gems:** Currently fixed; optimizer only modifies passive tree
- **Keystones:** May produce invalid builds if keystones conflict
- **Ascendancy:** Not currently optimized
- **Jewel Contents:** Can swap jewel locations but doesn't optimize jewel contents or timeless seeds

## Changelog

### v0.11.0
- **Local web UI** (`poe-optimizer web`): one page for players who don't use
  a terminal. Import a character from your account (character picker,
  POESESSID for private profiles) or paste a PoB code; choose Damage,
  Survivability or Both; watch each applied change stream in; get the tree
  drawn from real node positions with removed nodes ghosted and added nodes
  lit, before/after stats, an ordered change list, and a copy button for the
  new code. FastAPI + a static page, no build step, loopback only.
- Optimizer: `optimize()` accepts `on_iteration` (named removed/added nodes,
  marginal and cumulative gain, points, candidates, elapsed) and
  `should_cancel`; results carry `final_nodes`, `final_masteries`,
  `cancelled`, and per-change node lists.
- Tree data export (`src/web/tree_data.py`): 2,994 drawable nodes with
  positions, edges, types and class starts for 3.29, ~70 KB gzipped.
- New dependencies: fastapi, uvicorn, requests (runtime); httpx (tests).

### v0.10.0
- **PoB submodule updated to v2.67.2** (from v2.60.0): 3.28 and 3.29 trees,
  gems and uniques. `SET` now works with PoB's new `ImportFromNodeList`
  signature (and still with the old one). Added a 3.29 copy of the fixture
  build and a regression test that loads it.
- **New timeless jewels recognised**: Heroic Tragedy (3.28, Kalguur) with its
  three keystones and LUT data, and the five 3.29 Abyss timeless jewels
  (Festering Vengeance, Extinguishing Grasp, Baleful Dominion, Destructive
  Aspiration, Reclaimed Malevolence). They are classified as timeless, their
  sockets are protected, and PoB applies their transformations.
- **Incremental evaluation.** New `LOAD` / `SET` / `DELTA` session protocol
  in `evaluator_batch.lua`: the build is loaded into each PoB worker once and
  candidates are scored with PoB's node-hover calculator (~0.2 s vs 3-5 s per
  candidate). Greedy runs went from tens of minutes to about a minute.
- **Worker pool rewrite.** True N-way parallelism (the old pool serialised
  every evaluation behind one lock) and a raw-pipe reader that fixes lost /
  misattributed responses caused by `select()` on a buffered pipe.
- **Greedy optimizer.** Evaluates all removals, all adjacent additions, all
  mastery alternatives and point-neutral remove+add swaps each iteration;
  improvements are measured against the current tree, not the original.
- **Genetic optimizer** scores individuals on the same worker session.
- **Constraints.** Passive point counting now excludes class-start and
  ascendancy nodes (previously every candidate on a max-level build was
  rejected as over budget); level budget is `level + 23`.
- CLI: `--workers`, `--incremental/--no-incremental`; workers are shut down
  on exit. `--max-point-change` is now passed through to the optimizers.
- Docs restructured: `CLAUDE.md`, `docs/ARCHITECTURE.md`, rewritten
  `DEVELOPMENT.md` / `PERFORMANCE.md` / `BACKLOG.md`, plan template in
  `docs/plans/`, completed plans moved to `docs/archive/`.
- 21 new tests (worker protocol, incremental calculator, candidate
  generation, point counting).

### v0.9.2
- Replace silent `or "3_27"` fallbacks with `get_latest_tree_version_or_raise()` across 6 call sites
- Fail loudly with a clear submodule-init message when tree data is missing
- Make tests version-agnostic so they don't break each league

### v0.9.1
- Integrate constraint system into greedy and genetic optimizers
- Auto-detect point budget from character level in build XML
- Reject/penalise over-budget candidates during optimization search
- Add `--max-points` and `--disable-constraints` CLI options
- 19 new constraint unit tests

### v0.9.0
- Import characters directly from GGG's API (`account import`)
- Auto-detect passive tree version from PoB submodule data
- Update PoB submodule to v2.60.0 (adds 3.27 alternate trees)
- Eliminate all hardcoded tree version references

### v0.8.0
- Mastery effect optimization with context-aware scoring
- Jewel socket swapping (greedy + genetic)
- Thread of Hope ring analysis and node allocation
- Cluster jewel notable reallocation
- Build context extraction for smarter scoring

### v0.7.0
- Parallel candidate evaluation across CPU cores
- Batch evaluation with persistent Lua worker pool (~2x speedup)
- Real-time progress bars for optimization and evaluation
- Optimizer comparison scripts

### v0.6.0
- Full CLI tool (`optimize`, `analyze`, `diff`, `jewels`, `encode`, `decode`, `setup`)
- Timeless jewel parsing with legion data loading
- Cluster jewel subgraph detection and protection
- Unique jewel recognition (178 types)

## Roadmap

- [x] **v0.4** - Genetic algorithm, multi-objective optimization
- [x] **v0.5** - Desktop GUI (shelved, see `feature/gui-development`)
- [x] **v0.6** - Jewel support and CLI tool
- [x] **v0.7** - Parallel/batch evaluation, progress bars, performance optimization
- [x] **v0.8** - Mastery optimization, jewel socket swapping, cluster notable reallocation
- [x] **v0.9** - GGG account import, dynamic tree version detection
- [x] **v0.10** - Incremental PoB evaluation, real parallelism, swap moves
- [x] **v0.11** - Local web UI
- [ ] **v0.12** - Life/EHP floors in the greedy loop, candidate caching, timeless LUT fix
- [ ] **v1.0** - Item optimization, gem links, production ready

## Contributing

See `docs/CONTRIBUTING.md` and `docs/DEVELOPMENT.md`.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

## License

MIT License.

This project uses [Path of Building Community](https://github.com/PathOfBuildingCommunity/PathOfBuilding) as a submodule (MIT License).

## Acknowledgments

- **Path of Building Community** - Calculation engine and build data
- **Grinding Gear Games** - Path of Exile

---

*This is a third-party tool and is not affiliated with Grinding Gear Games.*

# Path of Exile Build Optimizer

A passive tree optimization tool for Path of Exile that uses Path of Building's calculation engine to automatically improve character builds.

## Overview

This tool takes a Path of Building export code, analyzes the passive tree, and uses optimization algorithms to find better node allocations. It leverages PoB's actual calculation engine for accurate DPS/defense numbers, supports jewel mechanics (timeless, cluster, unique), and outputs an optimized PoB code you can import directly.

**Key Features:**
- Uses PoB's real calculation engine (not approximations)
- Two optimization algorithms: Greedy (fast) and Genetic (thorough)
- Parallel evaluation with batch processing for faster optimization
- Progress bars for real-time optimization visibility
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

### Optimization Options

```bash
poe-optimizer optimize build.xml \
  --objective dps \           # dps, life, ehp, balanced
  --generations 50 \          # Evolution generations
  --population 30 \           # Population size
  --output optimized.xml \    # Output file
  --json                      # JSON output for scripting
```

## How It Works

1. **Parse Build:** Decode PoB code and extract passive tree, jewels, items
2. **Build Graph:** Create connectivity graph of 3,287 passive nodes
3. **Identify Constraints:** Protect jewel sockets and cluster jewel subgraphs
4. **Evolve Population:** Genetic algorithm mutates and selects builds
5. **Evaluate Fitness:** Call PoB's Lua engine for accurate stat calculations
6. **Output Result:** Generate optimized PoB code

### Optimization Algorithms

**Greedy Optimizer (recommended)**
- Iterative local search that evaluates all candidate modifications each round
- Analyzes each node's marginal impact and picks the best improvement
- Supports parallel evaluation across multiple CPU cores
- Batch evaluation mode with persistent worker pool for ~2x speedup
- Progress bars show real-time optimization status
- Best for reliable, incremental improvements
- Typical runtime: 5-10 minutes (with batch evaluation)

**Genetic Algorithm (experimental)**
- Population-based evolution (configurable population/generations)
- Crossover and mutation operators respect tree connectivity
- Explores broader search space, may find non-obvious combinations
- Supports parallel/batch evaluation like greedy optimizer
- Better for exploring alternative solutions
- Typical runtime: 2-5 minutes (faster but may find different local optima)

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
# Compare greedy vs genetic optimizer performance
python scripts/compare_optimizers.py

# Quick genetic optimizer test
python scripts/test_genetic_optimizer.py

# Benchmark batch evaluation
python scripts/benchmark_batch_evaluation.py
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
│   └── visualization/          # Plotting and analysis
├── PathOfBuilding/             # PoB submodule (calculation engine)
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
└── output/                     # Optimization results (auto-generated)
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_pob_caller.py -v

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
- [ ] **v1.0** - Item optimization, gem links, production ready

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

## License

MIT License. See [LICENSE](LICENSE) for details.

This project uses [Path of Building Community](https://github.com/PathOfBuildingCommunity/PathOfBuilding) as a submodule (MIT License).

## Acknowledgments

- **Path of Building Community** - Calculation engine and build data
- **Grinding Gear Games** - Path of Exile

---

*This is a third-party tool and is not affiliated with Grinding Gear Games.*

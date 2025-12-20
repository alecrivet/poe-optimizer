# Path of Exile Build Optimizer

A passive tree optimization tool for Path of Exile that uses genetic algorithms and Path of Building's calculation engine to automatically improve character builds.

## Overview

This tool takes a Path of Building export code, analyzes the passive tree, and uses optimization algorithms to find better node allocations. It leverages PoB's actual calculation engine for accurate DPS/defense numbers, supports jewel mechanics (timeless, cluster, unique), and outputs an optimized PoB code you can import directly.

**Key Features:**
- Uses PoB's real calculation engine (not approximations)
- Genetic algorithm explores the massive build space intelligently
- Supports timeless jewels, cluster jewels, and unique jewels
- Protects jewel-modified nodes from optimizer changes
- CLI tool for scripting and automation
- Outputs importable PoB codes

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

**Genetic Algorithm (default)**
- Population-based evolution (30 individuals, 50 generations)
- Crossover and mutation operators respect tree connectivity
- Discovers non-obvious node combinations
- Typical runtime: 5-15 minutes

**Greedy Optimizer (fast)**
- Iterative local search
- Analyzes each node's marginal impact
- Best for quick improvements
- Typical runtime: 1-3 minutes

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
│   │   ├── tree_parser.py      # Passive tree graph
│   │   └── modifier.py         # Build modification
│   ├── optimizer/              # Optimization algorithms
│   │   ├── genetic_optimizer.py
│   │   ├── tree_optimizer.py   # Greedy optimizer
│   │   └── multi_objective_optimizer.py
│   └── visualization/          # Plotting and analysis
├── PathOfBuilding/             # PoB submodule (calculation engine)
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
└── examples/                   # Example builds and workflows
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

- **Items/Gems:** Currently fixed; optimizer only modifies passive tree
- **Keystones:** May produce invalid builds if keystones conflict
- **Ascendancy:** Not currently optimized
- **Accuracy:** ~5-10% variance from PoB due to calculation method

## Roadmap

- [x] **v0.4** - Genetic algorithm, multi-objective optimization
- [x] **v0.5** - Desktop GUI (shelved, see `feature/gui-development`)
- [x] **v0.6** - Jewel support and CLI tool
- [ ] **v0.7** - Performance optimization, expanded test coverage
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

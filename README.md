# Path of Exile Build Optimizer

An intelligent build optimization tool for Path of Exile that uses genetic algorithms and Path of Building's calculation engine to automatically generate optimized character builds.

## 🎯 Project Goals

- **100% Calculation Accuracy:** Uses Path of Building's battle-tested calculation engine
- **Intelligent Optimization:** Genetic algorithms to explore the massive build space
- **Multi-Objective:** Balance DPS, survivability, and budget constraints
- **Community Integration:** Compatible with PoB import/export format

## 🚀 Quick Start

```bash
# Clone with submodules
git clone --recursive https://github.com/alecrivet/poe-optimizer.git
cd poe-optimizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the optimizer on example build
python tests/test_optimizer.py

# Analyze passive tree nodes
python scripts/analysis/analyze_tree.py

# Test relative calculator
python tests/test_relative_calculator.py
```

**Note:** Core optimizer is working! Currently optimizes by removing inefficient passive tree nodes. Place your PoB code in `examples/build1` to optimize your own builds.

## 📋 Implementation Progress

This project is being built in 4 phases:

- [x] **Phase 1:** PoB Integration ✅
  - XML codec (encode/decode PoB builds)
  - XML parser (extract stats)
  - XML modifier (modify builds)
  - Lua calculation interface

- [x] **Phase 2:** Relative Calculator ✅
  - Ratio-based extrapolation
  - Tree modification detection
  - Multi-stat evaluation (DPS, Life, EHP)

- [x] **Phase 3:** Tree Optimizer ✅
  - Greedy optimization algorithm
  - Node impact analysis
  - Objective functions (DPS, Life, EHP, balanced)

- [x] **Phase 4:** Advanced Optimization ✅
  - Genetic algorithm (evolution-based optimization)
  - Multi-objective optimization (Pareto frontier)
  - Node addition capability (3,287 nodes parsed)
  - Mastery optimization (213 mastery nodes)
  - NSGA-II algorithm components

**Current Status:** ~95% Complete (All 4 phases finished!)

## 🏗️ Architecture

```
poe-optimizer/
├── PathOfBuilding/              # Git submodule - PoB source
├── src/
│   ├── pob/                     # PoB interface layer ✅
│   │   ├── codec.py             # Encode/decode PoB codes
│   │   ├── xml_parser.py        # Parse pre-calculated stats
│   │   ├── modifier.py          # Modify builds (tree/gems/level)
│   │   ├── relative_calculator.py # Ratio extrapolation
│   │   ├── caller.py            # Python → Lua interface
│   │   ├── tree_parser.py       # Passive tree graph (3,287 nodes)
│   │   ├── mastery_optimizer.py # Mastery selection (213 masteries)
│   │   ├── evaluator_manual_tree.lua # Manual tree loading workaround
│   │   └── evaluator.lua        # Original evaluator
│   └── optimizer/               # Optimization algorithms ✅
│       ├── tree_optimizer.py    # Greedy tree optimizer
│       ├── genetic_optimizer.py # Genetic algorithm (evolution-based)
│       └── multi_objective_optimizer.py # Pareto frontier optimization
├── tests/                       # Test suite ✅
│   ├── test_codec.py            # Codec tests
│   ├── test_modifier.py         # Modifier tests
│   ├── test_pob_caller.py       # Caller tests
│   ├── test_relative_calculator.py # Calculator tests
│   ├── test_optimizer.py        # Optimizer tests
│   └── test_manual_tree_modifications.py # Tree modification tests
├── scripts/                     # Utility scripts
│   ├── analysis/                # Analysis tools
│   │   └── analyze_tree.py      # Node impact analysis
│   ├── debug/                   # Debug tools
│   │   ├── debug_node_removal.py
│   │   ├── debug_tree_parsing.py
│   │   └── trace_tree_loading.py
│   └── demos/                   # Demo scripts
│       ├── demo_codec.py
│       └── demo_pob_integration.py
├── examples/                    # Example builds
│   ├── build1                   # Example PoB code
│   ├── build1.xml               # Decoded XML
│   └── outputs/                 # Generated outputs
├── notes/                       # Development notes & session logs
└── docs/                        # Documentation
```

## 🔧 How It Works

1. **Decode Build:** Import PoB build code and decode to XML
2. **Modify Tree:** Remove/add passive tree nodes to test variations
3. **Evaluate:** Call PoB's Lua calculation engine via HeadlessWrapper
4. **Relative Calculation:** Use ratio extrapolation to estimate changes
5. **Optimize:** Greedy algorithm iteratively improves the build
6. **Export:** Generate optimized PoB code to import back into Path of Building

### Current Implementation

The optimizer currently:
- Analyzes each passive tree node's impact on DPS/Life/EHP
- Identifies inefficient nodes that can be reallocated
- Iteratively removes underperforming nodes
- Uses ~5-10% accuracy via relative calculations (fast but approximate)

**Known Limitations:**
- Only removes nodes (adding nodes requires tree graph data)
- Timeless Jewels not supported
- Relative calculations have 5-10% accuracy error (acceptable for ranking)

## 📚 Documentation

- **[Implementation Guide](notes/guides/POE_Build_Optimizer_Guide_v2.md)** - Complete technical guide
- **[Session Notes](notes/sessions/)** - Development session logs and progress
- **[Scripts README](scripts/README.md)** - Documentation for utility scripts

### Quick Start Examples

```bash
# Analyze a build's passive tree nodes
python scripts/analysis/analyze_tree.py

# Test the optimizer
python tests/test_optimizer.py

# Test relative calculator
python tests/test_relative_calculator.py
```

## 🛠️ Requirements

- Python 3.9+
- Lua 5.1 or LuaJIT
- Git (for submodules)

See `requirements.txt` for Python package dependencies.

## 🎮 Features

### Implemented ✅
- ✅ PoB code encoding/decoding
- ✅ XML parsing and modification
- ✅ Passive tree node analysis
- ✅ Relative calculation engine (ratio-based)
- ✅ Greedy tree optimizer
- ✅ Multi-objective support (DPS, Life, EHP, balanced)
- ✅ Node impact analysis tools

### In Development 🚧
- 🚧 Node addition capability
- 🚧 Multi-node operations (swaps, paths)
- 🚧 Genetic algorithm optimization

### Planned 📋
- 📋 Pareto frontier (multi-objective)
- 📋 Item optimization
- 📋 Gem link optimization
- 📋 Budget constraints
- 📋 CLI tool
- 📋 Web interface

## 🤝 Contributing

This is an open-source project. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

**Note:** This project uses [Path of Building Community](https://github.com/PathOfBuildingCommunity/PathOfBuilding) as a submodule. Path of Building is licensed under the MIT License. See `PathOfBuilding/LICENSE` for details.

## 🙏 Acknowledgments

- **Path of Building Community** - For the excellent build planning tool and calculation engine
- **poe.ninja** - For build and economy data
- **PoE Community** - For years of game knowledge and theorycrafting

## 📞 Contact

- GitHub Issues: [Report bugs or request features](https://github.com/alecrivet/poe-optimizer/issues)
- PoE Forums: [Discussion thread](link-when-available)

## 🗺️ Roadmap

**v0.1.0 (Current)** - Core optimizer working
- [x] Phase 1-3 complete (75%)
- [x] Can optimize basic builds (node removal)
- [x] Python API functional
- [ ] Phase 4: Advanced algorithms

**v0.2.0** - Advanced optimization
- [ ] Genetic algorithm
- [ ] Node addition capability
- [ ] Multi-objective optimization (Pareto frontier)
- [ ] Budget constraints

**v0.3.0** - User interface
- [ ] CLI tool
- [ ] Progress visualization
- [ ] Build comparison tools

**v1.0.0** - Production ready
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] Documentation complete
- [ ] Community feedback integrated

## ⚠️ Disclaimer

This is a third-party tool and is not affiliated with Grinding Gear Games. Path of Exile is a registered trademark of Grinding Gear Games.

---

**Status:** 🚧 Under Development - Phase 3 Complete ✅ | 75% Done | Core Optimizer Working!

Last Updated: November 2025

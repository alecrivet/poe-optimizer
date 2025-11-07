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

# Launch Desktop GUI (easiest!)
python run_gui.py

# Or try integration examples
python examples/integration/example_1_quick_optimization.py

# Or run quick test
python tests/test_optimizer.py
```

**Note:** All core features are implemented! The optimizer can add/remove nodes, optimize masteries, handle multiple objectives, and visualize results. Use the **Desktop GUI** for the easiest experience, or see `examples/integration/` for programmatic workflows.

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

**Current Status:** Phase 4 Complete! All core features implemented and tested.

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
│   ├── optimizer/               # Optimization algorithms ✅
│   │   ├── tree_optimizer.py    # Greedy tree optimizer
│   │   ├── genetic_optimizer.py # Genetic algorithm (evolution-based)
│   │   ├── multi_objective_optimizer.py # Pareto frontier optimization
│   │   ├── extended_objectives.py # 7 objectives (DPS/Life/EHP/Mana/ES/Block/Clear)
│   │   └── constraints.py       # Point budget, attributes, jewel sockets
│   └── visualization/           # Visualization tools ✅
│       ├── frontier_plot.py     # Pareto frontier plots (3D/2D)
│       ├── evolution_plot.py    # Evolution progress tracking
│       └── tree_diff.py          # Tree difference visualization
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
├── examples/                    # Example builds and workflows
│   ├── build1                   # Example PoB code
│   ├── build1.xml               # Decoded XML
│   ├── outputs/                 # Generated outputs
│   └── integration/             # Integration workflow examples ✅
│       ├── example_1_quick_optimization.py      # 2-min greedy workflow
│       ├── example_2_genetic_algorithm.py       # Evolution-based optimization
│       ├── example_3_multi_objective.py         # Trade-off exploration
│       ├── example_4_advanced_features.py       # 7 objectives + constraints
│       └── example_5_complete_workflow.py       # Full pipeline
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

The optimizer offers two approaches:

**Greedy Optimizer (Fast - 2-5 minutes)**
- Analyzes each node's impact on objectives
- Iteratively improves the build via local search
- Adds and removes nodes intelligently
- Best for quick improvements

**Genetic Algorithm (Thorough - 10-20 minutes)**
- Population-based evolution (30 individuals, 50 generations)
- Explores global optimization space
- Discovers non-obvious node combinations
- Best for maximum optimization

Both use relative calculations (~5-10% accuracy) for fast iteration, which is acceptable for ranking and selection.

**Current Limitations:**
- Timeless Jewels not supported (complex calculation requirements)
- Cluster Jewels not supported (dynamic tree modification)
- Items and gems are fixed (future phases will address this)

## 📚 Documentation

- **[Implementation Guide](notes/guides/POE_Build_Optimizer_Guide_v2.md)** - Complete technical guide
- **[Session Notes](notes/sessions/)** - Development session logs and progress
- **[Scripts README](scripts/README.md)** - Documentation for utility scripts

### Integration Examples

See `examples/integration/` for complete end-to-end workflows:

```bash
# Quick 2-minute optimization (greedy algorithm)
python examples/integration/example_1_quick_optimization.py

# Genetic algorithm with evolution tracking
python examples/integration/example_2_genetic_algorithm.py

# Multi-objective trade-off exploration
python examples/integration/example_3_multi_objective.py

# Advanced: 7 objectives + constraints
python examples/integration/example_4_advanced_features.py

# Complete pipeline: greedy vs genetic comparison
python examples/integration/example_5_complete_workflow.py
```

### Development and Testing

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

### Core Features ✅
- ✅ **PoB Integration:** Full encode/decode support for PoB builds
- ✅ **Passive Tree Parsing:** 3,287 nodes parsed with full connectivity graph
- ✅ **Mastery Optimization:** 213 mastery nodes with effect selection
- ✅ **Relative Calculator:** Fast ratio-based stat extrapolation
- ✅ **Node Addition/Removal:** Intelligent path finding and tree modification

### Optimization Algorithms ✅
- ✅ **Greedy Optimizer:** Fast local optimization (2-5 minutes)
- ✅ **Genetic Algorithm:** Evolution-based global optimization (10-20 minutes)
- ✅ **Multi-Objective:** Pareto frontier exploration (NSGA-II components)
- ✅ **7 Objectives:** DPS, Life, EHP, Mana, Energy Shield, Block, Clear Speed
- ✅ **Constraint System:** Point budget, attribute requirements, jewel sockets

### Visualization & Analysis ✅
- ✅ **Pareto Frontier Plots:** 3D/2D interactive visualizations
- ✅ **Evolution Tracking:** Fitness progress and convergence analysis
- ✅ **Tree Diff Viewer:** Visual comparison of builds
- ✅ **Node Impact Analysis:** Detailed stat contribution reports

### Desktop GUI ✅
- ✅ **PyQt6 Application:** Native desktop app for individual use
- ✅ **PoB Code I/O:** Paste input, copy optimized output
- ✅ **Build Viewer:** Display character, stats, gear, gems
- ✅ **Optimizer Controls:** Configure algorithm, objective, parameters
- ✅ **Real-time Progress:** Background optimization with live updates
- ✅ **Results Comparison:** Before/after stats table
- 🚧 **Tree Visualization:** Passive tree canvas (in progress)
- 🚧 **Animated GA:** Watch genetic algorithm work (in progress)

### Planned for Future Phases 📋
- 📋 Item optimization (equipment upgrades)
- 📋 Gem link optimization
- 📋 Timeless Jewel support
- 📋 CLI tool with progress bars

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

**v0.4.0 (Current)** - Phase 4 Complete ✅
- [x] Genetic algorithm implementation
- [x] Node addition capability (3,287 nodes)
- [x] Multi-objective optimization (Pareto frontier)
- [x] Extended objectives (7 total metrics)
- [x] Constraint system (points, attributes, jewels)
- [x] Visualization suite (plots, diffs, evolution)
- [x] Integration examples and documentation

**v0.5.0 (Current)** - Desktop GUI 🚧
- [x] PyQt6 desktop application
- [x] PoB code input/output
- [x] Build information display
- [x] Optimizer configuration UI
- [x] Real-time progress tracking
- [ ] Passive tree visualization canvas
- [ ] Animated genetic algorithm visualization
- [ ] Gear and gem parsing/display

**v0.6.0** - Polish & Testing
- [ ] Comprehensive test suite expansion
- [ ] Performance benchmarking and optimization
- [ ] Bug fixes and edge case handling
- [ ] CLI tool with progress bars

**v1.0.0** - Production Ready
- [ ] Item optimization
- [ ] Gem link optimization
- [ ] Community feedback integration
- [ ] Production deployment infrastructure

## ⚠️ Disclaimer

This is a third-party tool and is not affiliated with Grinding Gear Games. Path of Exile is a registered trademark of Grinding Gear Games.

---

**Status:** ✅ Phase 4 Complete | All Core Features Implemented | Ready for Polish & UI Work

Last Updated: November 2025

# Path of Exile Build Optimizer

An intelligent build optimization tool for Path of Exile that uses genetic algorithms and Path of Building's calculation engine to automatically generate optimized character builds.

## 🎯 Project Goals

- **100% Calculation Accuracy:** Uses Path of Building's battle-tested calculation engine
- **Intelligent Optimization:** Genetic algorithms to explore the massive build space
- **Multi-Objective:** Balance DPS, survivability, and budget constraints
- **Community Integration:** Compatible with PoB import/export format

## 🚀 Quick Start

**Note:** This project is currently under development. Follow the implementation phases below.

```bash
# Clone with submodules
git clone --recursive https://github.com/yourusername/poe-optimizer.git
cd poe-optimizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Future) Run optimization
python -m src.cli optimize --skill Cyclone --budget 5000000
```

## 📋 Implementation Progress

This project is being built in 6 phases:

- [ ] **Phase 1:** PoB Integration & Interface (Week 1)
- [ ] **Phase 2:** Data Access Layer (Week 2)
- [ ] **Phase 3:** Build Representation & Validation (Week 3)
- [ ] **Phase 4:** Optimization Algorithms (Week 4)
- [ ] **Phase 5:** Polish & Testing (Week 5)
- [ ] **Phase 6:** Advanced Features (Week 6+)

See individual phase files (`Phase1_*.md` through `Phase6_*.md`) for detailed implementation plans.

## 🏗️ Architecture

```
poe-optimizer/
├── PathOfBuilding/          # Git submodule - PoB source
├── src/
│   ├── pob/                 # PoB interface layer
│   │   ├── caller.py        # Subprocess wrapper for PoB
│   │   ├── parser.py        # Parse PoB Lua data files
│   │   ├── xml_generator.py # Generate PoB XML
│   │   └── codec.py         # Encode/decode PoB codes
│   ├── optimizer/           # Optimization algorithms
│   │   ├── genetic.py       # Genetic algorithm
│   │   ├── tree_optimizer.py # Passive tree optimization
│   │   └── item_optimizer.py # Item selection
│   ├── models/              # Data structures
│   │   ├── build.py         # Build representation
│   │   └── constraints.py   # Optimization constraints
│   └── cli.py               # Command-line interface
├── tests/                   # Test suite
├── examples/                # Example builds
└── docs/                    # Documentation
```

## 🔧 How It Works

1. **Read Game Data:** Parse passive tree, items, and gems from PoB's Lua files
2. **Generate Builds:** Create build variations using optimization algorithms
3. **Evaluate:** Call PoB's calculation engine to get accurate DPS, EHP, etc.
4. **Evolve:** Use genetic algorithms to improve builds over generations
5. **Export:** Generate PoB import codes for the best builds

## 📚 Documentation

- **[Implementation Guide](POE_Build_Optimizer_Guide_v2.md)** - Complete technical guide
- **[Phase 1: PoB Integration](Phase1_PoB_Integration.md)** - Week 1 tasks
- **[Phase 2: Data Access](Phase2_Data_Access.md)** - Week 2 tasks
- **[Phase 3: Build Representation](Phase3_Build_Representation.md)** - Week 3 tasks
- **[Phase 4: Optimization Algorithms](Phase4_Optimization_Algorithms.md)** - Week 4 tasks
- **[Phase 5: Polish & Testing](Phase5_Polish_Testing.md)** - Week 5 tasks
- **[Phase 6: Advanced Features](Phase6_Advanced_Features.md)** - Week 6+ tasks

## 🛠️ Requirements

- Python 3.9+
- Lua 5.1 or LuaJIT
- Git (for submodules)

See `requirements.txt` for Python package dependencies.

## 🎮 Features (Planned)

### Core Features
- ✅ Accurate calculations via PoB engine
- ✅ Genetic algorithm optimization
- ✅ Multi-objective optimization (DPS, EHP, Budget)
- ✅ CLI interface
- ✅ PoB import/export compatibility

### Advanced Features (Phase 6)
- 🔄 Pareto frontier optimization
- 🔄 Budget progression analysis
- 🔄 League mechanic specialization
- 🔄 ML-powered item recommendations
- 🔄 Web interface

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

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/poe-optimizer/issues)
- PoE Forums: [Discussion thread](link-when-available)

## 🗺️ Roadmap

**v0.1.0 (6 weeks)** - Core optimizer working
- [x] Phase 1-5 complete
- [ ] Can optimize basic builds
- [ ] CLI functional
- [ ] Tested against meta builds

**v0.2.0 (3 months)** - Advanced features
- [ ] Multi-objective optimization
- [ ] Budget progression
- [ ] Web interface

**v1.0.0 (6 months)** - Production ready
- [ ] Comprehensive testing
- [ ] Documentation complete
- [ ] Community feedback integrated
- [ ] Stable API

## ⚠️ Disclaimer

This is a third-party tool and is not affiliated with Grinding Gear Games. Path of Exile is a registered trademark of Grinding Gear Games.

---

**Status:** 🚧 Under Development - Phase 1 in progress

Last Updated: October 2024

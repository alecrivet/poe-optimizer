# CLI Implementation Plan

## Overview

Create a full-featured CLI tool for poe-optimizer with the following command structure:

```
poe-optimizer <command> [options]

Commands:
  optimize    Optimize a build's passive tree
  analyze     Analyze build statistics
  diff        Compare two builds
  jewels      Show jewel information
  encode      Encode XML to PoB code
  decode      Decode PoB code to XML
  setup       First-time setup (decompress timeless data, etc.)
```

---

## Phase 1: Core CLI Framework

**Goal:** Set up the CLI structure using Click framework

### Tasks:
- [ ] Create `src/cli/__init__.py` - CLI module
- [ ] Create `src/cli/main.py` - Main entry point with Click group
- [ ] Create `src/cli/utils.py` - Shared CLI utilities (input/output helpers)
- [ ] Add click to requirements.txt (already present via fastapi)
- [ ] Create basic command stubs for all subcommands
- [ ] Add `console_scripts` entry point in setup.py/pyproject.toml

### File Structure:
```
src/cli/
├── __init__.py
├── main.py          # @click.group() and subcommand registration
├── utils.py         # Input/output helpers, error handling
├── commands/
│   ├── __init__.py
│   ├── optimize.py  # optimize command
│   ├── analyze.py   # analyze, stats commands
│   ├── diff.py      # diff command
│   ├── jewels.py    # jewels command
│   ├── codec.py     # encode/decode commands
│   └── setup.py     # setup command
└── formatters/
    ├── __init__.py
    ├── console.py   # Rich console output
    └── json.py      # JSON output format
```

### Deliverables:
- Running `python -m src.cli` shows help
- All subcommands registered (with placeholder implementations)
- `--version` and `--help` work

---

## Phase 2: Input/Output Handling

**Goal:** Create flexible input sources and output formats

### Input Sources:
- [ ] File path (XML or PoB code file)
- [ ] PoB code string (direct argument)
- [ ] Stdin pipe support
- [ ] URL fetch (pobb.in, pastebin) - stretch goal

### Output Formats:
- [ ] Console (rich formatted, default)
- [ ] JSON (`--json` flag)
- [ ] File (`--output <path>`)
- [ ] PoB code (`--pob-code` for optimized builds)

### Tasks:
- [ ] Create `InputHandler` class in utils.py
  - Auto-detect input type (file, code, stdin)
  - Decode PoB codes automatically
  - Return normalized XML
- [ ] Create `OutputHandler` class in utils.py
  - Format results based on `--json`, `--output` flags
  - Use Rich for console output
- [ ] Add common options decorator for input/output flags
- [ ] Error handling with helpful messages

### Example Usage:
```bash
# From file
poe-optimizer optimize build.xml

# From PoB code
poe-optimizer optimize --code "eNr1WltvG..."

# From stdin
cat build.xml | poe-optimizer optimize -

# JSON output
poe-optimizer analyze build.xml --json

# Save to file
poe-optimizer optimize build.xml --output optimized.xml
```

---

## Phase 3: Optimize Command

**Goal:** Full-featured optimization command

### Options:
```
poe-optimizer optimize <input> [options]

Options:
  --objective, -o      Optimization objective (dps, life, ehp, balanced)
  --algorithm, -a      Algorithm (greedy, genetic, multi-objective)
  --iterations         Max iterations for greedy (default: 50)
  --generations        Generations for genetic (default: 50)
  --population-size    Population size for genetic (default: 30)
  --mutation-rate      Mutation rate for genetic (default: 0.2)
  --allow-point-change Allow adding/removing points
  --max-point-change   Max point difference from original
  --optimize-masteries Optimize mastery selections (default: true)
  --protect-jewels     Protect jewel sockets and cluster nodes (default: true)
  --min-life           Minimum life constraint
  --min-ehp            Minimum EHP constraint
  --output, -o         Output file path
  --json               Output as JSON
  --verbose, -v        Verbose output
  --quiet, -q          Minimal output
```

### Tasks:
- [ ] Create `commands/optimize.py` with all options
- [ ] Integrate GreedyTreeOptimizer
- [ ] Integrate GeneticTreeOptimizer
- [ ] Integrate MultiObjectiveOptimizer
- [ ] Add constraint handling (min-life, min-ehp, etc.)
- [ ] Add jewel protection integration
- [ ] Progress bar for long operations
- [ ] Result summary with improvements
- [ ] Generate PoB code for optimized build

### Output Example:
```
╭──────────────────────────────────────────────────────────╮
│                  OPTIMIZATION COMPLETE                    │
╰──────────────────────────────────────────────────────────╯

Algorithm: Genetic (50 generations, 30 population)
Objective: DPS

┌─────────┬─────────────┬─────────────┬───────────┐
│ Metric  │ Original    │ Optimized   │ Change    │
├─────────┼─────────────┼─────────────┼───────────┤
│ DPS     │ 1,234,567   │ 1,456,789   │ +18.0%    │
│ Life    │ 4,500       │ 4,350       │ -3.3%     │
│ EHP     │ 45,000      │ 43,500      │ -3.3%     │
└─────────┴─────────────┴─────────────┴───────────┘

Nodes Added: 3
Nodes Removed: 5
Masteries Changed: 2
Protected Nodes: 7 (2 jewel sockets, 5 cluster nodes)

PoB Code saved to: optimized_build.txt
```

---

## Phase 4: Analysis Commands

**Goal:** Commands for build analysis without optimization

### 4.1 Analyze/Stats Command
```
poe-optimizer analyze <input> [options]

Options:
  --json    Output as JSON
  --full    Show all available stats
```

Tasks:
- [ ] Show key stats (DPS, Life, EHP, resistances, attributes)
- [ ] Show passive tree summary (points, notable count)
- [ ] Show skill/gem info
- [ ] Show jewel summary

### 4.2 Diff Command
```
poe-optimizer diff <build1> <build2> [options]

Options:
  --json    Output as JSON
```

Tasks:
- [ ] Compare stats between builds
- [ ] Show node differences (added/removed)
- [ ] Show mastery differences
- [ ] Highlight improvements/regressions

### 4.3 Jewels Command
```
poe-optimizer jewels <input> [options]

Options:
  --json    Output as JSON
```

Tasks:
- [ ] List all jewels (socketed and inventory)
- [ ] Show timeless jewel info (type, seed, variant)
- [ ] Show cluster jewel info (size, notables)
- [ ] Show unique jewel effects
- [ ] Show protected nodes

### 4.4 Tree Command (Stretch)
```
poe-optimizer tree <input> [options]

Options:
  --format   Output format (text, svg, png)
  --output   Output file
```

Tasks:
- [ ] ASCII tree visualization (basic)
- [ ] Show allocated nodes list
- [ ] Node groupings by type

---

## Phase 5: Utility Commands

**Goal:** Helper commands for common operations

### 5.1 Encode Command
```
poe-optimizer encode <input.xml> [options]

Options:
  --output, -o   Output file (default: stdout)
  --copy         Copy to clipboard
```

Tasks:
- [ ] Read XML file
- [ ] Encode to PoB code
- [ ] Output to stdout/file/clipboard

### 5.2 Decode Command
```
poe-optimizer decode <pob-code-or-file> [options]

Options:
  --output, -o   Output file (default: stdout)
```

Tasks:
- [ ] Accept PoB code string or file
- [ ] Decode to XML
- [ ] Pretty-print XML output

### 5.3 Setup Command
```
poe-optimizer setup [options]

Options:
  --decompress-timeless   Decompress timeless jewel data
  --check                 Check installation status
  --force                 Force re-setup
```

Tasks:
- [ ] Check PoB submodule is initialized
- [ ] Check Lua/LuaJIT is installed
- [ ] Decompress timeless jewel data
- [ ] Verify all dependencies
- [ ] Show installation status

---

## Phase 6: Polish & Packaging

**Goal:** Production-ready CLI

### Tasks:
- [ ] Add comprehensive `--help` text for all commands
- [ ] Add usage examples in help
- [ ] Create `poe-optimizer` entry point in pyproject.toml
- [ ] Add shell completion support (bash, zsh, fish)
- [ ] Add `--verbose` and `--quiet` global options
- [ ] Add `--config` option for config file
- [ ] Create default config file template
- [ ] Add color themes (light/dark)
- [ ] Error messages with suggestions
- [ ] Add `--dry-run` for optimize command

### Configuration File (~/.poe-optimizer.yaml):
```yaml
defaults:
  algorithm: genetic
  objective: dps
  generations: 50
  population_size: 30
  optimize_masteries: true
  protect_jewels: true

output:
  format: console  # console, json
  colors: true
  verbose: false
```

### Entry Point (pyproject.toml):
```toml
[project.scripts]
poe-optimizer = "src.cli.main:cli"
```

---

## Implementation Order

1. **Phase 1** (Core Framework) - 2 hours
   - Basic CLI structure, all commands stubbed

2. **Phase 2** (Input/Output) - 2 hours
   - Input detection, output formatting

3. **Phase 3** (Optimize) - 3 hours
   - Full optimization workflow

4. **Phase 4** (Analysis) - 2 hours
   - Stats, diff, jewels commands

5. **Phase 5** (Utilities) - 1 hour
   - Encode, decode, setup

6. **Phase 6** (Polish) - 2 hours
   - Help text, packaging, config

**Total: ~12 hours**

---

## Testing Plan

- [ ] Unit tests for InputHandler, OutputHandler
- [ ] Integration tests for each command
- [ ] Test with various build types (timeless, cluster, unique jewels)
- [ ] Test error handling (invalid input, missing files)
- [ ] Test JSON output format

---

## Future Enhancements

- Web API mode (`poe-optimizer serve`)
- Batch optimization of multiple builds
- Build comparison reports (HTML/PDF)
- Integration with poe.ninja for item prices
- Trade site integration for gear recommendations

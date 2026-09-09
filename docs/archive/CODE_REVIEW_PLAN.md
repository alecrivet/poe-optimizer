# Code Review Plan: poe-optimizer

## Overview

This document outlines a structured approach to reviewing the entire poe-optimizer codebase. The goal is to understand the architecture, identify technical debt, and document how components interact.

**Codebase Stats:**
- ~16,000 lines of production code
- ~7,000 lines of tests (326 tests)
- 6 major modules

## Review Sessions

### Session 1: Core Architecture & Data Flow (2-3 hours)

**Goal:** Understand how data flows from input to optimization output.

**Files to review:**
```
src/pob/codec.py           - PoB code encoding/decoding
src/pob/xml_parser.py      - XML parsing utilities
src/pob/tree_parser.py     - Passive tree data extraction
src/pob/caller.py          - PoB Lua process communication
src/pob/worker_pool.py     - Parallel PoB evaluation
```

**Questions to answer:**
- [ ] How does a PoB code get parsed into workable data?
- [ ] How do we communicate with the PoB Lua process?
- [ ] What's the worker pool architecture for parallel evaluation?
- [ ] Where are the performance bottlenecks?

---

### Session 2: Optimizer Core (2-3 hours)

**Goal:** Understand the optimization algorithms and objective handling.

**Files to review:**
```
src/optimizer/tree_optimizer.py      - Greedy/hill-climbing optimizer
src/optimizer/genetic_optimizer.py   - Genetic algorithm optimizer
src/optimizer/multi_objective_optimizer.py - Pareto optimization
src/optimizer/extended_objectives.py - DPS, EHP, custom objectives
src/optimizer/constraints.py         - Build constraints
```

**Questions to answer:**
- [ ] How do the greedy vs genetic optimizers differ?
- [ ] How are objectives calculated and compared?
- [ ] How do constraints get enforced?
- [ ] What's the mutation/crossover strategy?

---

### Session 3: Jewel System (2-3 hours)

**Goal:** Understand the jewel abstraction and all jewel types.

**Files to review:**
```
src/pob/jewel/base.py              - Base jewel class
src/pob/jewel/registry.py          - Jewel type registry
src/pob/jewel/radius_calculator.py - Radius-based node detection
src/pob/jewel/socket_optimizer.py  - Jewel socket placement
src/pob/jewel/timeless.py          - Timeless jewel handling
src/pob/jewel/timeless_data.py     - Timeless jewel node data
src/pob/jewel/thread_of_hope.py    - Thread of Hope logic
src/pob/jewel/cluster.py           - Cluster jewel basics
src/pob/jewel/cluster_optimizer.py - Cluster notable optimization
src/pob/jewel/cluster_subgraph.py  - Cluster graph structure
```

**Questions to answer:**
- [ ] How does the jewel registry pattern work?
- [ ] How are radius calculations done for different jewel types?
- [ ] How does timeless jewel optimization work?
- [ ] How are cluster jewel subgraphs represented?

---

### Session 4: Mastery & Build Context (1-2 hours)

**Goal:** Understand mastery handling and build context management.

**Files to review:**
```
src/pob/build_context.py      - Build state management
src/pob/mastery_optimizer.py  - Mastery effect selection
src/pob/mastery_synergy.py    - Mastery synergy calculations
src/pob/modifier.py           - Modifier parsing and tracking
src/pob/batch_calculator.py   - Batch stat calculations
src/pob/relative_calculator.py - Relative value calculations
```

**Questions to answer:**
- [ ] What state does BuildContext track?
- [ ] How are masteries evaluated and selected?
- [ ] How does relative value calculation work?
- [ ] What's the batch calculation strategy?

---

### Session 5: CLI & Integration (1-2 hours)

**Goal:** Understand the CLI structure and user-facing interface.

**Files to review:**
```
src/cli/main.py                    - CLI entry point
src/cli/commands/optimize.py       - Optimize command
src/cli/commands/analyze.py        - Analyze command
src/cli/commands/jewels.py         - Jewel analysis command
src/cli/commands/account.py        - GGG account import
src/cli/utils.py                   - CLI utilities
src/ggg/                           - GGG API client (all files)
```

**Questions to answer:**
- [ ] How is the CLI structured with Click?
- [ ] What options are exposed for each command?
- [ ] How does the GGG import flow work?
- [ ] What's the output formatting strategy?

---

### Session 6: Visualization & Utilities (1 hour)

**Goal:** Review visualization and helper modules.

**Files to review:**
```
src/visualization/evolution_plot.py  - Optimization progress plots
src/visualization/frontier_plot.py   - Pareto frontier visualization
src/visualization/tree_diff.py       - Tree comparison visualization
src/pob/tree_positions.py            - Node position data
```

**Questions to answer:**
- [ ] What visualizations are available?
- [ ] How is tree diffing implemented?
- [ ] Are there unused/dead code paths?

---

## Review Checklist

For each session, evaluate:

### Code Quality
- [ ] Clear function/class naming
- [ ] Appropriate abstractions
- [ ] No excessive complexity
- [ ] Proper error handling

### Architecture
- [ ] Clear separation of concerns
- [ ] Minimal coupling between modules
- [ ] Consistent patterns used
- [ ] No circular dependencies

### Technical Debt
- [ ] TODO comments to address
- [ ] Dead code to remove
- [ ] Opportunities for simplification
- [ ] Missing type hints

### Documentation
- [ ] Key functions documented
- [ ] Complex logic explained
- [ ] Module-level docstrings present

### Testing
- [ ] Critical paths tested
- [ ] Edge cases covered
- [ ] Test names descriptive
- [ ] Mocking used appropriately

---

## Priority Items to Investigate

Based on organic development, likely areas needing attention:

1. **Worker pool reliability** - Process communication edge cases
2. **Error propagation** - Are errors from PoB handled gracefully?
3. **Memory usage** - Large tree data structures
4. **Configuration** - Hardcoded values that should be configurable
5. **Unused code** - Features started but not completed (web module?)

---

## Output

After each session, document:
1. Architecture diagram for that module
2. List of concerns/technical debt found
3. Suggestions for improvement
4. Questions that need further investigation

Create a summary document: `docs/ARCHITECTURE.md`

---

## Suggested Schedule

| Session | Module | Estimated Time |
|---------|--------|----------------|
| 1 | Core Architecture | 2-3 hours |
| 2 | Optimizer Core | 2-3 hours |
| 3 | Jewel System | 2-3 hours |
| 4 | Mastery & Context | 1-2 hours |
| 5 | CLI & Integration | 1-2 hours |
| 6 | Visualization | 1 hour |

**Total: 9-14 hours** (can be split across multiple days)

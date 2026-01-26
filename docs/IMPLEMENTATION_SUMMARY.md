# Comprehensive Jewel Implementation - Summary

**Date:** 2025-12-06
**Updated:** 2025-12-06 (Expanded to include all jewel types)
**Status:** Plan Complete, Ready for Implementation

---

## Overview

The PoE Build Optimizer will pivot from GUI development to implementing **comprehensive jewel support** using Path of Building's calculation engine:

1. **Timeless Jewels** (5 types) - Transform passive nodes based on seed
2. **Cluster Jewels** (3 sizes) - Dynamically add nodes to the tree
3. **Unique Jewels** (178 jewels) - Special jewels with unique effects

---

## Why This Change?

### Current Problems

**Timeless Jewels:**
- Transform passive tree nodes based on seed
- Our optimizer currently **ignores** these transformations
- Example: `build2.xml` has Lethal Pride (seed 13628, Akoya)

**Cluster Jewels:**
- Dynamically add nodes to the passive tree (IDs >= 65536)
- Our tree parser doesn't know about these nodes
- Optimizer could **corrupt** cluster jewel subgraphs

**Unique Jewels:**
- 178 unique jewels with special mechanics
- Many have radius effects that modify passive nodes
- Need to ensure proper passthrough to PoB

### Impact
- ~50-60% of endgame builds use some form of jewel
- ~30-40% use timeless jewels specifically
- ~40% use cluster jewels
- Core calculation accuracy is critical

---

## The Plan

### Part 1: Shelve GUI Work

**Status:** GUI work remains on main branch but is deprioritized
- GUI is functional but incomplete
- Future work tracked in `feature/gui-development` branch tag
- Focus shifts to core calculation accuracy

---

### Part 2: Timeless Jewel Support (Priority 1)

**5 Phases:**

| Phase | Task | Time |
|-------|------|------|
| 1 | XML Parsing | 2 hours |
| 2 | Legion Data Access | 1 day |
| 3 | Calculation Integration | 2-3 days |
| 4 | Optimizer Integration | 1-2 days |
| 5 | Testing & Documentation | 2 days |

**Timeless Jewel Types:** Glorious Vanity, Lethal Pride, Elegant Hubris, Militant Faith, Brutal Restraint

---

### Part 3: Cluster Jewel Support (Priority 2)

**Critical Challenge:** Cluster jewels dynamically generate nodes (IDs >= 65536)

| Phase | Task | Time |
|-------|------|------|
| A | Cluster Detection | 1 day |
| B | Subgraph Mapping | 2 days |
| C | Optimizer Constraints | 1 day |

**Strategy:** Treat cluster nodes as **immutable** - don't let optimizer modify them

**Cluster Sizes:**
- Small: 2-3 nodes, 1 notable
- Medium: 4-6 nodes, 1-2 notables, 1 medium socket
- Large: 6-12 nodes, 2-3 notables, 2 medium sockets

---

### Part 4: Unique Jewel Support (Priority 3)

**178 unique jewels in PoB data**

| Phase | Task | Time |
|-------|------|------|
| A | XML Validation | 1 day |
| B | Radius Jewel Support | 2 days |
| C | Mechanic Validation | 1 day |

**Notable Unique Jewels:**
- Thread of Hope, Impossible Escape (pathing bypass)
- Watcher's Eye (aura-conditional)
- Radius jewels (Fireborn, Cold Steel, etc.)

**Strategy:** Ensure passthrough to PoB; let PoB handle calculations

---

### Unified Architecture

```
src/pob/jewel/
├── __init__.py      # Unified exports
├── base.py          # Base classes
├── timeless.py      # Timeless handling
├── cluster.py       # Cluster handling
├── unique.py        # Unique handling
└── registry.py      # Central registry
```

**JewelRegistry** provides:
- `get_protected_nodes()` - Nodes optimizer shouldn't touch
- `get_jewel_constraints()` - Auto-generated constraints

**Total Time:** ~4 weeks

---

## Success Criteria

### Week 2: Timeless Jewels
- [ ] Parse timeless jewels from XML
- [ ] Calculations include jewel modifiers
- [ ] Optimizer doesn't break with jewels
- [ ] Lethal Pride working (most common)

### Week 3: Cluster Jewels
- [ ] Detect cluster jewels and subgraphs
- [ ] Map generated node IDs (65536+)
- [ ] Protect cluster nodes from modification
- [ ] Nested cluster jewels handled

### Week 4: Full Implementation
- [ ] All 5 timeless jewel types supported
- [ ] All 3 cluster jewel sizes supported
- [ ] Unique jewels pass through correctly
- [ ] Accurate to within 1% of PoB
- [ ] Comprehensive tests and docs

---

## Implementation Order

```
Week 1: Foundation
├── Create jewel module architecture
└── Timeless jewel parsing

Week 2: Timeless + Unique
├── Legion data access
├── Calculation integration
└── Unique jewel validation

Week 3: Cluster Jewels
├── Detection and parsing
├── Subgraph mapping
└── Constraint integration

Week 4: Polish
├── Comprehensive testing
├── Documentation
└── Release v0.6.0
```

---

**Status:** Planning Complete | Ready to Implement

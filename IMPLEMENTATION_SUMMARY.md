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

**What's Being Shelved:**
- PyQt6 desktop application (functional but incomplete)
- Passive tree visualization canvas
- Tree position loading and rendering

**How:**
- Move all GUI work to `feature/gui-development` branch
- Tag as `v0.5.0-gui-wip` for future reference
- Update README to mark GUI as future work

**Time:** 15 minutes

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

## Technical Details

### Timeless Jewel Types

| Jewel | Legion | Effect |
|-------|--------|--------|
| Glorious Vanity | Vaal | Replaces passives, adds keystone |
| **Lethal Pride** | Karui | **Adds modifiers to small passives** ⭐ |
| Elegant Hubris | Eternal Empire | Adds percentage modifiers |
| Militant Faith | Templar | Transforms notables to Devotion |
| Brutal Restraint | Maraketh | Transforms passives |

**build2.xml has:** Lethal Pride (Akoya, Seed 13628)

### PoB Integration Points

```
PathOfBuilding/
├── src/
│   ├── Data/TimelessJewelData/
│   │   ├── LegionPassives.lua       (185KB)
│   │   ├── LethalPride.zip          (2.2MB)
│   │   ├── GloriousVanity.zip.*     (25MB)
│   │   └── ...
│   └── Classes/
│       ├── PassiveTree.lua          (loads legion data)
│       ├── PassiveSpec.lua          (manages jewels)
│       └── TimelessJewelListControl.lua
```

### Implementation Strategy

**Phase 1 Example:**
```python
from src.pob.timeless_jewel import parse_timeless_jewels

with open('examples/build2.xml') as f:
    xml = f.read()

jewels = parse_timeless_jewels(xml)
# Returns: [TimelessJewel(type="Lethal Pride", seed=13628, variant="Akoya")]
```

**Phase 3 Example:**
```lua
-- evaluator_manual_tree.lua
-- Ensure timeless jewels are loaded
build.spec:ProcessJewels()  -- Apply jewel transformations
build:BuildModList()        -- Rebuild with jewel mods
```

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

## Risk Assessment

### Timeless Jewels
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PoB data format complex | Medium | High | Study source |
| HeadlessWrapper limitations | Low | High | Test early |

### Cluster Jewels (HIGHEST RISK)
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Subgraph corruption | High | Critical | Treat as immutable |
| Node ID collision | Medium | High | Verify 65536+ range |
| Socket chain breakage | Medium | High | Process recursively |

### Unique Jewels
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Radius calculation | Low | Medium | Use PoB's method |
| Mechanic edge cases | Medium | Low | Let PoB handle |

---

## Files Created

### Planning Documents
- `TIMELESS_JEWEL_IMPLEMENTATION_PLAN.md` (now comprehensive jewel plan)
  - Part 2: Timeless jewels
  - Part 3: Unique jewels
  - Part 4: Cluster jewels
  - Part 5: Unified architecture

- `QUICKSTART_TIMELESS_JEWEL.md`
  - Step-by-step implementation guide

- `IMPLEMENTATION_SUMMARY.md` (this file)
  - Executive summary

---

## Implementation Order

```
Week 1: Foundation
├── Shelve GUI
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

## Questions?

**Q: Can we do GUI later?**
A: Yes! All GUI work preserved in `feature/gui-development` branch.

**Q: Why cluster jewels as "immutable"?**
A: Cluster jewels dynamically generate nodes. Modifying them could corrupt the subgraph structure. Safer to preserve and optimize the regular tree only.

**Q: Will timeless jewels slow calculations?**
A: Potentially slightly. PoB loads 30MB of seed data. We'll use lazy loading.

**Q: When will it be done?**
A: 4 weeks for comprehensive support. Timeless jewels in 2 weeks.

---

## Approval Checklist

- [ ] Plan reviewed and approved
- [ ] Timeline acceptable (4 weeks)
- [ ] Risk assessment acceptable
- [ ] Ready to shelve GUI work
- [ ] Ready to start implementation

---

**Next Step:** Execute `QUICKSTART_TIMELESS_JEWEL.md` Step 1 (shelve GUI)

**Status:** Planning Complete | Awaiting Approval to Begin

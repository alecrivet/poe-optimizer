# Comprehensive Jewel Implementation Plan

**Created:** 2025-12-06
**Updated:** 2025-12-06 (Expanded to include all jewel types)
**Status:** Planning Phase
**Priority:** High - Core Calculation Accuracy

---

## Overview

This document outlines the plan to:
1. **Shelve GUI development** - Move GUI work to a feature branch for future development
2. **Implement comprehensive jewel support** - Integrate PoB's jewel systems for accurate build optimization:
   - **Unique Jewels** (178 jewels) - Special jewels with unique effects
   - **Timeless Jewels** (5 types) - Transform passive nodes based on seed
   - **Cluster Jewels** (3 sizes) - Dynamically add nodes to the tree

---

## Part 1: Shelving GUI Work

### Current GUI Status

**Completed GUI Features:**
- ✅ PyQt6 desktop application (`src/gui/main_window.py`)
- ✅ PoB code input/output
- ✅ Build information display
- ✅ Optimizer configuration UI
- ✅ Real-time progress tracking
- ✅ Results comparison

**In-Progress GUI Features:**
- 🚧 Passive tree visualization canvas (`src/gui/widgets/tree_canvas.py`)
- 🚧 Loading actual PoB tree node positions
- 🚧 Filtering ruthless nodes
- 🚧 Timeless Jewel warnings

**Recent GUI Commits:**
```
f33be89 feat: Load actual PoB tree positions and filter ruthless nodes
8f70286 fix: Add Timeless Jewel warning before optimization
73882fc fix: Use getattr for PassiveNode attribute access instead of dict.get()
b5d18ff fix: Correct function name from parse_pob_xml to parse_pob_stats
b45efe1 fix: Add robust error handling to tree canvas widget
0a81a6c feat: Add passive tree visualization canvas and testing guide
05eddae docs: Update README with Desktop GUI information
0d8dc81 feat: Add PyQt6 desktop GUI application (MVP)
```

### Shelving Strategy

**Option 1: Create Feature Branch (RECOMMENDED)**
```bash
# Create a new branch from current state
git checkout -b feature/gui-development

# Push to remote
git push -u origin feature/gui-development

# Switch back to main (or appropriate base branch)
git checkout main

# Tag the GUI work for reference
git tag v0.5.0-gui-wip feature/gui-development
git push origin v0.5.0-gui-wip
```

**Option 2: Revert GUI Commits**
```bash
# Less preferred - loses commit history
git revert --no-commit f33be89..0d8dc81
git commit -m "Revert GUI development to focus on timeless jewel support"
```

**Recommendation:** Use Option 1 to preserve all GUI work and allow easy continuation later.

### Updated README After Shelving

Mark GUI as experimental/future work:
- Change status from "🚧 Current Work" to "📋 Future Work"
- Add note: "GUI development is on hold pending core calculation improvements"
- Point interested users to `feature/gui-development` branch

---

## Part 2: Timeless Jewel Implementation

### Problem Statement

**Current Limitation:**
- Timeless jewels are detected but not properly handled
- XML contains timeless jewel data but calculations ignore it
- Warning shown to user: "Timeless Jewels are not currently supported"
- Optimizer may produce incorrect results for builds with timeless jewels

**Example from build2.xml:**
```xml
<Item id="23">
    Rarity: UNIQUE
Lethal Pride
Timeless Jewel
Unique ID: 883f70d7ad6771620c432ed28265691cb003f39dd475e8eb6a740f129b46cbd9
Item Level: 84
Radius: Large
Implicits: 0
Commanded leadership over 13628 warriors under Akoya
Passives in radius are Conquered by the Karui
Historic
</Item>
```

**Impact:**
- Timeless jewels transform passive nodes in radius
- Can add/change significant modifiers (e.g., +5% Strength, Double Damage, etc.)
- Optimizer that ignores these changes produces inaccurate results

### PoB's Timeless Jewel System

**Data Location:**
- `PathOfBuilding/src/Data/TimelessJewelData/` - Seed data for all jewel types
  - `LegionPassives.lua` - Passive node modifications (185KB)
  - `GloriousVanity.zip.part0-4` - 25MB of Glorious Vanity data
  - `LethalPride.zip` - 2.2MB of Lethal Pride data
  - `ElegantHubris.zip` - 2.4MB of Elegant Hubris data
  - `MilitantFaith.zip` - 855KB of Militant Faith data
  - `BrutalRestraint.zip` - 2.1MB of Brutal Restraint data
  - `NodeIndexMapping.lua` - Node ID mappings (97KB)
  - `LegionTradeIds.lua` - Trade site ID mappings

**Timeless Jewel Types:**
1. **Glorious Vanity** (Vaal) - Replaces passives, adds keystone
   - Variants: Doryani, Xibaqua, Ahuana
2. **Lethal Pride** (Karui) - Adds modifiers to small passives
   - Variants: Kaom, Rakiata, Akoya
3. **Elegant Hubris** (Eternal Empire) - Adds percentage modifiers
   - Variants: Cadiro, Victario, Caspiro
4. **Militant Faith** (Templar) - Transforms notables to Devotion
   - Variants: Avarius, Dominus, Maxarius
5. **Brutal Restraint** (Maraketh) - Transforms passives
   - Variants: Asenath, Balbala, Nasima

**PoB Integration Points:**
- `PassiveTree.lua` line 56: Loads `LegionPassives` module
- `PassiveTree.lua` line 657: Builds ModList for legion jewels
- `PassiveSpec.lua`: Manages jewel allocation to sockets
- `CalcSetup.lua`: Applies timeless jewel transformations during calculation
- `TimelessJewelListControl.lua`: UI for jewel search/selection

### Implementation Approach

#### Phase 1: XML Parsing and Detection

**Goal:** Parse timeless jewel data from PoB XML

**Tasks:**
1. Extend `src/pob/xml_parser.py` to extract timeless jewels
   - Parse `<Item>` elements with type "Timeless Jewel"
   - Extract jewel type, seed, variant, socket location
   - Store in structured format

2. Create `src/pob/timeless_jewel.py` module
   ```python
   @dataclass
   class TimelessJewel:
       jewel_type: str  # "Lethal Pride", "Glorious Vanity", etc.
       seed: int        # e.g., 13628
       variant: str     # e.g., "Akoya"
       socket_node_id: Optional[int]

   def parse_timeless_jewels(build_xml: str) -> List[TimelessJewel]:
       """Extract timeless jewels from XML"""

   def get_jewel_variant_id(jewel: TimelessJewel) -> int:
       """Map variant name to ID (1, 2, or 3)"""
   ```

3. Test parsing with build2.xml

**Deliverables:**
- `src/pob/timeless_jewel.py` - Jewel data structures
- Tests in `tests/test_timeless_jewel.py`
- Parsed jewel from build2.xml

#### Phase 2: Legion Data Access

**Goal:** Access PoB's timeless jewel transformation data

**Tasks:**
1. Extract timeless jewel data from PoB
   - Decompress .zip files if needed
   - Load `LegionPassives.lua` structure
   - Understand data format

2. Create Lua interface for timeless data
   ```lua
   -- src/pob/timeless_evaluator.lua
   function getTimelessJewelModifiers(jewelType, seed, variant, nodeId)
       -- Query PoB's timeless jewel data
       -- Return modifier strings for the node
   end
   ```

3. Python wrapper for timeless data access
   ```python
   # src/pob/timeless_jewel.py
   class TimelessJewelDatabase:
       def __init__(self, pob_path: Path):
           self.legion_data = self._load_legion_data()

       def get_node_modifiers(self, jewel: TimelessJewel, node_id: int) -> List[str]:
           """Get modifiers applied to a node by a timeless jewel"""
   ```

**Deliverables:**
- Lua script to query timeless data
- Python wrapper for data access
- Tests verifying correct modifier lookup

#### Phase 3: Calculation Integration

**Goal:** Use PoB's calculation engine with timeless jewels

**Tasks:**
1. Ensure timeless jewels are included in XML passed to PoB
   - Verify `<Item>` elements are preserved
   - Verify socket assignments in `<Sockets>` section

2. Verify HeadlessWrapper handles timeless jewels
   - Test with build2.xml (has Lethal Pride)
   - Check if stats reflect timeless jewel modifiers
   - Debug if calculations are incorrect

3. Update `evaluator_manual_tree.lua` if needed
   - Ensure TreeTab:Load() processes jewels
   - Ensure Build:BuildModList() includes jewel mods
   - May need to explicitly call jewel initialization

4. Test relative calculations with timeless jewels
   - Remove a node affected by timeless jewel
   - Verify DPS change is correct
   - Verify calculations account for lost jewel modifiers

**Potential Issues:**
- **Issue 1:** HeadlessWrapper may not initialize timeless data
  - **Solution:** Manually load legion data in evaluator

- **Issue 2:** Timeless transformations may not apply
  - **Solution:** Explicitly call `spec:AddTimelessJewelModifiers()` or equivalent

- **Issue 3:** Seed-specific data lookup fails
  - **Solution:** Pre-load seed data or implement caching

**Deliverables:**
- Updated evaluator that handles timeless jewels
- Tests showing correct calculations with/without jewels
- Documentation of any PoB quirks discovered

#### Phase 4: Optimizer Integration

**Goal:** Optimize builds with timeless jewels correctly

**Tasks:**
1. Update tree optimizer to respect timeless jewels
   - Don't remove nodes that are valuable due to jewel
   - Consider jewel-modified nodes in scoring
   - Preserve jewel socket allocations

2. Add constraints for timeless jewels (optional)
   ```python
   @dataclass
   class TimelessJewelConstraint:
       preserve_socket: bool = True  # Don't deallocate socket
       min_affected_nodes: int = 3   # Keep at least N nodes in radius
   ```

3. Add warnings/validation
   - Warn if optimizer wants to remove jewel socket
   - Validate that jewel data is loaded correctly
   - Report if calculations seem inaccurate

**Deliverables:**
- Optimizer works correctly with timeless jewels
- Appropriate warnings and validations
- Example optimization of build2.xml

#### Phase 5: Testing and Documentation

**Goal:** Comprehensive testing and user documentation

**Tasks:**
1. Create test builds with each jewel type
   - Glorious Vanity test build
   - Lethal Pride test build (already have build2.xml)
   - Elegant Hubris test build
   - Militant Faith test build
   - Brutal Restraint test build

2. Verify calculations for each
   - Manual verification against PoB
   - Automated tests comparing stats
   - Edge cases (multiple jewels, radius overlaps)

3. Update documentation
   - Remove "Timeless Jewels not supported" warnings
   - Add "Timeless Jewel Support" section to README
   - Document any limitations (e.g., jewel optimization not supported)
   - Add examples to USER_GUIDE.md

4. Performance testing
   - Check if timeless data slows calculations
   - Optimize if needed (caching, preloading)

**Deliverables:**
- Test suite for all jewel types
- Updated documentation
- Performance benchmarks

---

## Implementation Timeline

### Week 1: Shelving & Phase 1
- **Day 1:** Shelve GUI work, create feature branch
- **Day 2-3:** Implement XML parsing for timeless jewels
- **Day 4:** Test parsing with build2.xml

### Week 2: Phase 2 & 3
- **Day 1-2:** Access legion data from PoB
- **Day 3-4:** Integrate with HeadlessWrapper calculations
- **Day 5:** Test and debug calculation accuracy

### Week 3: Phase 4 & 5
- **Day 1-2:** Update optimizer for timeless jewels
- **Day 3:** Create test builds for all jewel types
- **Day 4:** Documentation and examples
- **Day 5:** Final testing and release

**Total Estimated Time:** 15 days (3 weeks)

---

## Risk Assessment

### High Risk Items

1. **PoB Data Format Unknown**
   - **Risk:** Legion data format may be complex or undocumented
   - **Mitigation:** Study PoB source code, reverse engineer if needed
   - **Fallback:** Contact PoB community for help

2. **HeadlessWrapper Limitations**
   - **Risk:** HeadlessWrapper may not support timeless jewels
   - **Mitigation:** Test early, prepare to patch if needed
   - **Fallback:** Call PoB functions directly, bypass wrapper

3. **Calculation Accuracy**
   - **Risk:** Our calculations may still be inaccurate
   - **Mitigation:** Extensive testing against PoB
   - **Fallback:** Document known inaccuracies

### Medium Risk Items

1. **Data Size**
   - **Risk:** 30MB of timeless data may slow loading
   - **Mitigation:** Lazy loading, only load needed data

2. **Multiple Jewels**
   - **Risk:** Handling multiple timeless jewels may be complex
   - **Mitigation:** Start with single jewel, extend later

3. **Radius Calculations**
   - **Risk:** Determining which nodes are in radius
   - **Mitigation:** Use PoB's existing radius calculation

---

## Success Criteria

### Minimum Viable Implementation
- ✅ Parse timeless jewels from XML
- ✅ Calculations reflect timeless jewel modifiers
- ✅ Optimizer doesn't break with timeless jewels
- ✅ Works with Lethal Pride (most common)

### Full Implementation
- ✅ All 5 jewel types supported
- ✅ Multiple jewels in one build
- ✅ Accurate to within 1% of PoB calculations
- ✅ Comprehensive tests and documentation
- ✅ No performance degradation

### Stretch Goals
- 📋 Optimize timeless jewel selection (find best seed)
- 📋 Suggest best socket for a given jewel
- 📋 Visualize jewel radius in tree display

---

## Alternative Approaches Considered

### Alternative 1: Ignore Timeless Jewels
- **Pros:** No implementation work
- **Cons:** Inaccurate results, user confusion
- **Verdict:** ❌ Not acceptable for production

### Alternative 2: Pre-calculate Timeless Transformations
- **Pros:** Faster calculations
- **Cons:** Complex, error-prone, hard to maintain
- **Verdict:** ❌ Too fragile

### Alternative 3: Use PoB's Full Calculation Engine
- **Pros:** Guaranteed accuracy
- **Cons:** Already doing this via HeadlessWrapper
- **Verdict:** ✅ This is our current approach

### Alternative 4: External API for Timeless Data
- **Pros:** Could use poe.ninja or community APIs
- **Cons:** Network dependency, may not be accurate
- **Verdict:** ❌ PoB data is more reliable

---

## File Structure After Implementation

```
poe-optimizer/
├── src/
│   ├── pob/
│   │   ├── timeless_jewel.py          # NEW - Jewel data structures
│   │   ├── timeless_evaluator.lua     # NEW - Lua interface for jewel data
│   │   ├── xml_parser.py              # UPDATED - Parse jewels
│   │   ├── evaluator_manual_tree.lua  # UPDATED - Handle jewels
│   │   └── caller.py                  # UPDATED - Jewel validation
│   └── optimizer/
│       ├── tree_optimizer.py          # UPDATED - Respect jewels
│       └── constraints.py             # UPDATED - Jewel constraints
├── tests/
│   ├── test_timeless_jewel.py         # NEW - Jewel parsing tests
│   └── test_pob_caller.py             # UPDATED - Jewel calculation tests
├── examples/
│   ├── build2.xml                     # Has Lethal Pride
│   ├── build_glorious_vanity.xml      # NEW
│   ├── build_elegant_hubris.xml       # NEW
│   ├── build_militant_faith.xml       # NEW
│   └── build_brutal_restraint.xml     # NEW
└── docs/
    ├── TIMELESS_JEWEL_SUPPORT.md      # NEW - User guide
    └── USER_GUIDE.md                  # UPDATED - Remove limitation note
```

---

## Part 3: Unique Jewel Support

### Problem Statement

**Current State:**
- PoB XML contains unique jewels as `<Item>` elements
- Our XML parser may not extract jewel-specific mechanics
- Unique jewels with "Radius" effects interact with passive nodes
- Some unique jewels have build-altering mechanics

### Unique Jewel Categories

**Data Source:** `PathOfBuilding/src/Data/Uniques/jewel.lua` (178 unique jewels)

#### Category 1: Simple Stat Jewels
Jewels that provide straightforward stat bonuses:
- **Watcher's Eye** - Conditional bonuses based on auras
- **Thread of Hope** - Allows allocation of passives in radius without pathing
- **Impossible Escape** - Similar to Thread of Hope for specific keystones

**Complexity:** Low - Stats applied directly, no tree modification

#### Category 2: Radius Effect Jewels
Jewels that interact with passive nodes in radius:
- **Anatomical Knowledge** - Life per Intelligence in radius
- **The Blue Dream/Nightmare** - Power charges from resistance nodes
- **Fireborn** - Transform physical damage to fire in radius
- **Cold Steel** - Transform physical/cold damage in radius
- **Eldritch Knowledge** - Chaos damage per Intelligence in radius

**Complexity:** Medium - Need to calculate radius and query affected nodes

#### Category 3: Build-Altering Jewels
Jewels with major mechanical changes:
- **Dissolution of the Flesh** - Changes how life works
- **Bloodnotch** - Stun damage recovery
- **Calamitous Visions** - Adds "Lone Messenger" keystone

**Complexity:** High - PoB handles internally, we pass through

### Implementation Approach

**Strategy:** Let PoB handle all jewel calculations; we ensure jewels are properly passed through

**Phase A: Jewel XML Validation (1 day)**
1. Verify all jewel items are preserved in XML transformations
2. Ensure socket assignments in ItemSet are maintained
3. Test with builds containing multiple jewel types

**Phase B: Radius Jewel Support (2 days)**
1. Parse jewel radius from item data
2. Query which nodes are in radius of a jewel socket
3. Use PoB's radius calculation: `PassiveTree:IsNodeInRadius(node, jewelSocket, radius)`

**Phase C: Unique Mechanic Validation (1 day)**
1. Create test builds for complex jewels (Thread of Hope, Watcher's Eye)
2. Verify PoB calculations match our relative calculator
3. Document any special handling needed

### Deliverables
- `src/pob/jewel.py` - Unified jewel parsing (unique, timeless, cluster)
- Test builds with radius jewels
- Documentation of supported unique jewels

---

## Part 4: Cluster Jewel Support

### Problem Statement

**Current State:**
- Cluster jewels dynamically add nodes to the passive tree
- These nodes are NOT in the base tree data
- PoB generates "subgraphs" at runtime based on jewel mods
- Our tree parser doesn't know about cluster nodes
- Optimizer may corrupt cluster jewel allocations

### Cluster Jewel System

**Data Source:** `PathOfBuilding/src/Data/ClusterJewels.lua` (1050 lines)

#### Cluster Jewel Sizes

| Size | Min Nodes | Max Nodes | Can Socket | Notable Count |
|------|-----------|-----------|------------|---------------|
| Small | 2 | 3 | 0 | 1 |
| Medium | 4 | 6 | 1 (Medium) | 1-2 |
| Large | 6 | 12 | 2 (Medium) | 2-3 |

#### Cluster Jewel Structure

```
Large Cluster Jewel (socketed in outer jewel socket)
├── Small passives (enchant-based stats)
├── Notable 1 (from notable mod)
├── Notable 2 (from notable mod)
├── Medium Socket 1 → Medium Cluster Jewel
│   ├── Small passives
│   ├── Notable 1
│   └── Medium Socket → Small Cluster Jewel
│       └── Notable 1
└── Medium Socket 2 → Medium Cluster Jewel
```

#### How PoB Handles Cluster Jewels

**`PassiveSpec.lua:BuildClusterJewelGraphs()` (lines 1428-1491):**
1. Removes old subgraphs
2. For each large jewel socket with a valid cluster jewel:
   - Calls `BuildSubgraph()` to create nodes
3. Assigns generated node IDs (65536+ range)
4. Links subgraph entrance to parent socket
5. Rebuilds paths

**Node ID Encoding (16-bit):**
```
Bits 0-3:  Node index (0-11)
Bits 4-5:  Group size (0=Small, 1=Medium, 2=Large)
Bits 6-8:  Large socket index (0-5)
Bits 9-10: Medium socket index (0-2)
Bit 16:    Signal bit (always 1 to avoid collision with tree hashes)
```

### Implementation Challenges

#### Challenge 1: Dynamic Node Generation
**Problem:** Cluster nodes don't exist until PoB generates them
**Impact:** Our tree parser returns null for cluster node IDs
**Solution:** After XML load, query PoB for active subgraph structure

#### Challenge 2: Random Mods
**Problem:** Cluster jewels have random enchants and mods
**Impact:** Node effects vary per jewel
**Solution:** Parse jewel item text for actual mods, or let PoB handle

#### Challenge 3: Tree Modification
**Problem:** Optimizer might try to add/remove cluster nodes
**Impact:** Could corrupt subgraph structure
**Solution:** Treat cluster jewel allocations as fixed (constraint)

#### Challenge 4: Socket Chains
**Problem:** Medium clusters in Large, Small in Medium
**Impact:** Complex nested subgraph dependencies
**Solution:** Process recursively, preserve socket chains

### Implementation Approach

**Strategy:** Preserve cluster jewel allocations as immutable; don't optimize cluster nodes

**Phase A: Cluster Detection (1 day)**
1. Parse cluster jewels from XML items
2. Detect which sockets have cluster jewels
3. Extract enchant and notable mods

```python
@dataclass
class ClusterJewel:
    size: str  # "Small", "Medium", "Large"
    enchant_type: str  # e.g., "affliction_maximum_life"
    notables: List[str]  # Notable names
    socket_node_id: int  # Where socketed
    item_id: int
```

**Phase B: Subgraph Mapping (2 days)**
1. Query PoB for active subgraph nodes after build load
2. Map generated node IDs to their cluster jewel
3. Store mapping for optimizer reference

```python
class ClusterJewelSubgraph:
    jewel: ClusterJewel
    generated_nodes: List[int]  # IDs >= 65536
    allocated_nodes: List[int]  # Which are allocated
    socket_nodes: List[int]  # Nested sockets for Medium/Small
```

**Phase C: Optimizer Constraints (1 day)**
1. Add `ClusterJewelConstraint` to prevent subgraph modification
2. Treat all cluster nodes as "protected" during optimization
3. Allow optimization of regular tree, not cluster subgraphs

```python
@dataclass
class ClusterJewelConstraint:
    preserve_subgraphs: bool = True  # Don't touch cluster nodes
    preserve_sockets: bool = True    # Keep jewel sockets allocated
```

**Phase D: Future Enhancement (Stretch Goal)**
- Optimize cluster jewel notable selection
- Suggest best cluster jewel mods for build
- Support cluster jewel swapping

### Deliverables
- `src/pob/cluster_jewel.py` - Cluster jewel parsing and mapping
- ClusterJewelConstraint integration
- Test builds with cluster jewels
- Documentation of cluster jewel handling

---

## Part 5: Unified Jewel Architecture

### Proposed Architecture

```
src/pob/
├── jewel/
│   ├── __init__.py           # Unified exports
│   ├── base.py               # Base jewel classes
│   ├── unique.py             # Unique jewel handling (178 types)
│   ├── timeless.py           # Timeless jewel handling (5 types)
│   ├── cluster.py            # Cluster jewel handling (3 sizes)
│   └── registry.py           # Jewel type detection and routing
```

### Base Classes

```python
# src/pob/jewel/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class JewelCategory(Enum):
    UNIQUE = "unique"
    TIMELESS = "timeless"
    CLUSTER = "cluster"
    ABYSS = "abyss"  # Future: Abyss jewels


@dataclass
class JewelSocket:
    node_id: int
    position: tuple  # (x, y) on tree
    radius: Optional[str]  # "Small", "Medium", "Large"
    is_cluster_socket: bool


@dataclass
class BaseJewel(ABC):
    category: JewelCategory
    item_id: int
    socket_node_id: Optional[int]

    @abstractmethod
    def get_affected_nodes(self, tree: PassiveTreeGraph) -> List[int]:
        """Return node IDs affected by this jewel"""
        pass


@dataclass
class UniqueJewel(BaseJewel):
    name: str
    base_type: str  # "Cobalt", "Crimson", "Viridian", "Prismatic"
    radius: Optional[str]
    modifiers: List[str]

    def get_affected_nodes(self, tree):
        if not self.radius:
            return []
        return tree.get_nodes_in_radius(self.socket_node_id, self.radius)


@dataclass
class TimelessJewel(BaseJewel):
    jewel_type: str  # "Lethal Pride", etc.
    seed: int
    variant: str
    variant_id: int

    def get_affected_nodes(self, tree):
        return tree.get_nodes_in_radius(self.socket_node_id, "Large")


@dataclass
class ClusterJewel(BaseJewel):
    size: str  # "Small", "Medium", "Large"
    enchant_type: str
    notables: List[str]
    generated_nodes: List[int]

    def get_affected_nodes(self, tree):
        return self.generated_nodes  # Return dynamically generated nodes
```

### Jewel Registry

```python
# src/pob/jewel/registry.py

class JewelRegistry:
    """Central registry for all jewels in a build"""

    def __init__(self):
        self.unique_jewels: List[UniqueJewel] = []
        self.timeless_jewels: List[TimelessJewel] = []
        self.cluster_jewels: List[ClusterJewel] = []

    @classmethod
    def from_build_xml(cls, xml: str) -> 'JewelRegistry':
        """Parse all jewels from build XML"""
        registry = cls()

        # Parse each jewel type
        registry.unique_jewels = parse_unique_jewels(xml)
        registry.timeless_jewels = parse_timeless_jewels(xml)
        registry.cluster_jewels = parse_cluster_jewels(xml)

        return registry

    def get_protected_nodes(self) -> Set[int]:
        """Return all nodes that should not be modified by optimizer"""
        protected = set()

        # Cluster jewel nodes are protected
        for cluster in self.cluster_jewels:
            protected.update(cluster.generated_nodes)

        # Jewel socket nodes are protected
        for jewel in self.all_jewels:
            if jewel.socket_node_id:
                protected.add(jewel.socket_node_id)

        return protected

    def get_jewel_constraints(self) -> List[Constraint]:
        """Generate optimizer constraints from jewels"""
        constraints = []

        # Timeless jewel: preserve nodes in radius (valuable due to transformation)
        for tj in self.timeless_jewels:
            constraints.append(TimelessJewelConstraint(
                socket_node_id=tj.socket_node_id,
                min_affected_nodes=3
            ))

        # Cluster jewels: don't modify subgraph
        for cj in self.cluster_jewels:
            constraints.append(ClusterJewelConstraint(
                socket_node_id=cj.socket_node_id,
                preserve_subgraph=True
            ))

        return constraints
```

---

## Revised Implementation Timeline

### Week 1: Shelving & Foundation
- **Day 1:** Shelve GUI work, create feature branch
- **Day 2-3:** Create jewel module architecture
- **Day 4-5:** Implement timeless jewel parsing (Phase 1)

### Week 2: Timeless & Unique Jewels
- **Day 1-2:** Timeless jewel data access (Phase 2)
- **Day 3-4:** Timeless jewel calculation integration (Phase 3)
- **Day 5:** Unique jewel validation

### Week 3: Cluster Jewels & Integration
- **Day 1-2:** Cluster jewel detection and parsing
- **Day 3:** Subgraph mapping
- **Day 4:** Optimizer constraint integration
- **Day 5:** Unified testing

### Week 4: Testing & Documentation
- **Day 1-2:** Comprehensive test builds
- **Day 3-4:** Documentation
- **Day 5:** Release preparation

**Total Estimated Time:** 4 weeks

---

## Revised Risk Assessment

### Cluster Jewel Risks (NEW - HIGH PRIORITY)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Subgraph corruption | High | Critical | Treat as immutable |
| Node ID collision | Medium | High | Verify 65536+ range |
| Socket chain breakage | Medium | High | Process recursively |
| Performance with many clusters | Low | Medium | Lazy loading |

### Implementation Order Recommendation

**Priority 1: Timeless Jewels** (Most common issue)
- Affects 30-40% of builds
- Data is deterministic (seed-based)
- High user impact

**Priority 2: Cluster Jewels** (Most complex)
- Dynamically generated
- Critical to not corrupt
- Complex but well-documented

**Priority 3: Unique Jewels** (Lowest risk)
- PoB handles internally
- Just ensure passthrough
- Test radius effects

---

## Next Steps

1. **Get Approval** - Review this expanded plan
2. **Shelve GUI** - Execute Part 1 (create feature branch)
3. **Start Timeless** - Begin timeless jewel implementation
4. **Parallel Planning** - Document cluster jewel subgraph format
5. **Regular Check-ins** - Review progress after each phase

---

## References

- **PoB Source:** `PathOfBuilding/src/Classes/PassiveTree.lua`
- **PassiveSpec:** `PathOfBuilding/src/Classes/PassiveSpec.lua` (cluster subgraph logic)
- **Legion Data:** `PathOfBuilding/src/Data/TimelessJewelData/`
- **Cluster Data:** `PathOfBuilding/src/Data/ClusterJewels.lua`
- **Unique Jewels:** `PathOfBuilding/src/Data/Uniques/jewel.lua` (178 jewels)
- **Example Build:** `examples/build2.xml` (Lethal Pride seed 13628, Akoya variant)
- **PoB Community:** https://github.com/PathOfBuildingCommunity/PathOfBuilding

---

**Status:** Ready for review and approval
**Next Action:** Shelve GUI work and begin timeless jewel implementation

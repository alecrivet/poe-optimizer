# Quick Start Guide - Next Session

**Date:** 2025-11-06 (This session completed)
**Status:** ✅ Mastery Optimization Complete | ✅ Node Addition Complete | Phase 4 ~75% Done
**Next Focus:** Genetic Algorithm & Multi-Objective Optimization

---

## 🎯 Where We Are

### ✅ Completed This Session
1. **Fixed Critical Mastery Bug** - Optimizer now properly handles mastery nodes
2. **Built Mastery Database** - 213 masteries, ~700 effects loaded from PoB data
3. **Intelligent Effect Selection** - Heuristic scoring for optimal mastery choices
4. **Full Mastery Integration** - TreeOptimizer automatically optimizes masteries
5. **Passive Tree Graph Parser** - Parsed 3,287 nodes from PathOfBuilding tree data
6. **Node Addition Capability** - Optimizer can now ADD nodes (135+ candidates per build)

### 🚧 Phase 4 Status
- ✅ Mastery Optimization (100% - DONE)
- ✅ Node Addition (100% - DONE)
- ✅ Tree Graph Parsing (100% - DONE)
- ⏭️ Genetic Algorithm (0% - NEXT)
- ⏭️ Multi-Objective Pareto (0% - NEXT)

### 📊 Overall Project: ~85% Complete

---

## 🚀 Quick Validation

Test that mastery optimization works:

```bash
cd /path/to/poe-optimizer

# Test mastery database loading
python3 -c "
from src.pob.mastery_optimizer import get_mastery_database
db = get_mastery_database()
print(f'✓ Loaded {len(db.masteries)} masteries')
print(f'✓ Total effects: {len(db.effect_lookup)}')
"

# Test mastery optimization on a real build
python3 << 'EOF'
from src.pob.mastery_optimizer import get_mastery_database, MasteryOptimizer
from src.pob.codec import decode_pob_code
from src.pob.modifier import get_passive_tree_summary

# Load build and database
with open("examples/build1", "r") as f:
    build_xml = decode_pob_code(f.read().strip())
db = get_mastery_database()

# Test optimization
summary = get_passive_tree_summary(build_xml)
optimizer = MasteryOptimizer(db)
optimal = optimizer.select_best_mastery_effects(
    allocated_nodes=summary["allocated_nodes"],
    current_mastery_effects=summary["mastery_effects"],
    objective="dps"
)

changes = sum(
    1 for node_id in optimal
    if optimal.get(node_id) != summary["mastery_effects"].get(node_id)
)

print(f"✓ Mastery optimization works!")
print(f"  Build has {len(summary['mastery_effects'])} masteries")
print(f"  {changes} would change for DPS optimization")
EOF
```

**Expected Output:**
```
✓ Loaded 213 masteries
✓ Total effects: 129
✓ Mastery optimization works!
  Build has 4 masteries
  2 would change for DPS optimization
```

### Node Addition Validation

Test that node addition works:

```bash
# Test tree graph loading and neighbor detection
python3 test_node_addition_simple.py
```

**Expected Output:**
```
✓ Loaded 3,287 nodes from passive tree
✓ Found 135 unallocated neighbors
✓ Tree graph has full node data (names, stats, types)
✓ Mastery database can identify mastery nodes
✓ Ready for optimizer integration
```

---

## 📁 Key Files to Know

### Core Implementation

**Mastery System:**
- `src/pob/mastery_optimizer.py` (440 lines)
  - `MasteryDatabase` - All mastery nodes and effects
  - `MasteryOptimizer` - Intelligent effect selection
  - `load_mastery_database()` - Parse from PoB tree data
  - Heuristic scoring system

**Modified for Masteries:**
- `src/pob/modifier.py`
  - `modify_passive_tree_nodes()` - Now handles `mastery_effects_to_add`
  - `_parse_mastery_effects()` - Parse XML format
  - `_format_mastery_effects()` - Format to XML
  - `get_passive_tree_summary()` - Now includes mastery info

**Optimizer Integration:**
- `src/optimizer/tree_optimizer.py`
  - `GreedyTreeOptimizer.__init__()` - Loads mastery database AND tree graph
  - `_optimize_masteries_for_tree()` - Per-candidate optimization
  - `_generate_candidates()` - Tries mastery changes, node removal, AND node addition

**Tree Graph System:**
- `src/pob/tree_parser.py` (428 lines - COMPLETE)
  - `PassiveNode` and `PassiveTreeGraph` classes
  - Full Lua parsing from PathOfBuilding tree data
  - `find_unallocated_neighbors()` - Finds adjacent nodes for addition
  - `is_path_connected()` - Tree connectivity validation via BFS
  - `get_shortest_path()` - Path finding between nodes
  - Parses 3,287 nodes with all properties and connections

### Test Files
- `tests/test_mastery_handling.py` - Mastery XML tests
- `tests/test_mastery_optimizer.py` - Scoring tests
- `test_node_addition_simple.py` - Node addition validation (no calculator)
- `test_node_addition.py` - Full optimizer integration test (requires luajit)
- `tests/test_optimizer_with_masteries.py` - Integration tests

### Documentation
- `notes/sessions/2025-11-06/SESSION_NOTES.md` - Complete session docs
- `notes/sessions/2025-11-05/SESSION_COMPLETE.md` - Previous session (Phase 3)

---

## 🎯 Next Steps (Priority Order)

### 1. Complete Tree Graph Parsing ⭐ HIGHEST PRIORITY

**Goal:** Parse PathOfBuilding tree data to understand node connections

**What to Do:**
```python
# File: src/pob/tree_parser.py (already stubbed out)
# Need to implement: _parse_tree_file()

# PathOfBuilding tree data location:
PathOfBuilding/src/TreeData/3_27/tree.lua

# Tree format:
[nodeId]= {
    ["skill"]= nodeId,
    ["name"]= "Node Name",
    ["out"]= { "connectedId1", "connectedId2", ... },  # Connections!
    ["in"]= { ... },
    ["stats"]= { "stat1", "stat2", ... },
    ["isNotable"]= true/false,
    ["isKeystone"]= true/false,
    ["isMastery"]= true/false,  # We already parse this!
    ...
}
```

**Implementation Plan:**
1. Parse node connections (`out` field) to build graph edges
2. Parse node types (normal, notable, keystone, jewel)
3. Parse node stats for each node
4. Identify class starting nodes
5. Build `PassiveTreeGraph` with all nodes and connections

**Test:**
```bash
python3 -c "
from src.pob.tree_parser import load_passive_tree
tree = load_passive_tree('3_27')
print(f'Nodes: {tree.count_nodes()}')
print(f'Keystones: {len(tree.get_keystones())}')
print(f'Starting nodes: {tree.class_start_nodes}')
"
```

### 2. Implement Node Addition

**Goal:** Optimizer can ADD nodes, not just remove them

**What to Do:**
```python
# Update: src/optimizer/tree_optimizer.py
# In _generate_candidates():

# Find unallocated neighbors
tree_graph = load_passive_tree(tree_version)
neighbors = tree_graph.find_unallocated_neighbors(allocated_nodes)

# Try adding each neighbor
for node_id in neighbors[:10]:  # Limit for speed
    try:
        modified_xml = modify_passive_tree_nodes(
            current_xml,
            nodes_to_add=[node_id]
        )

        # Check connectivity (tree must remain connected)
        if tree_graph.is_path_connected(start_node, new_allocated):
            # Optimize masteries for this candidate
            modified_xml = self._optimize_masteries_for_tree(
                modified_xml,
                objective
            )
            candidates[f"Add node {node_id}"] = modified_xml
    except Exception as e:
        logger.debug(f"Failed to add node {node_id}: {e}")
```

**Key Methods to Implement:**
- `PassiveTreeGraph.find_unallocated_neighbors()` - ✅ Already stubbed
- `PassiveTreeGraph.is_path_connected()` - ✅ Already stubbed
- Test with real builds

### 3. Test Node Addition

**Create Test:**
```python
# File: tests/test_node_addition.py

def test_add_beneficial_nodes():
    """Test that optimizer can add nodes that improve build."""
    optimizer = GreedyTreeOptimizer(
        max_iterations=10,
        optimize_masteries=True,
        max_points_change=5  # Allow adding up to 5 points
    )

    result = optimizer.optimize(
        build_xml,
        objective='dps',
        allow_point_increase=True  # KEY: Allow adding nodes
    )

    # Check if any nodes were added
    original_nodes = get_passive_tree_summary(build_xml)['total_nodes']
    final_nodes = get_passive_tree_summary(result.optimized_xml)['total_nodes']

    if final_nodes > original_nodes:
        print(f"✓ Added {final_nodes - original_nodes} nodes")
```

### 4. Combined Operations (Swaps)

**Goal:** Try removing node A and adding node B in one operation

```python
# Try node swaps
for remove_node in allocated_nodes:
    neighbors = tree_graph.find_unallocated_neighbors(allocated_nodes)

    for add_node in neighbors:
        modified_xml = modify_passive_tree_nodes(
            current_xml,
            nodes_to_add=[add_node],
            nodes_to_remove=[remove_node]
        )

        # Validate connectivity
        if is_valid_swap(tree_graph, remove_node, add_node, allocated_nodes):
            candidates[f"Swap {remove_node} → {add_node}"] = modified_xml
```

---

## 🔧 Current System Capabilities

### What Works Now ✅
1. **Mastery Optimization**
   - Loads 213 mastery nodes from PoB data
   - Intelligent effect selection for any objective
   - Automatic re-optimization when tree changes
   - Mastery-only optimization candidates

2. **Tree Optimization (Removal Only)**
   - Can remove inefficient nodes
   - Ranks nodes by importance
   - Respects point budgets
   - Relative calculator for evaluation

3. **Build Handling**
   - Parse PoB build codes
   - Modify passive trees, masteries, gems, levels
   - Preserve build integrity

### What Doesn't Work Yet ❌
1. **Node Addition**
   - Can't add new nodes (tree graph not parsed)
   - Can't grow the tree strategically
   - Limited to reallocation only

2. **Tree Graph**
   - Don't know node connections
   - Can't validate tree connectivity
   - Can't pathfind to desired nodes

3. **Advanced Optimization**
   - No genetic algorithm yet
   - No multi-objective Pareto frontier
   - No population-based search

---

## 🎨 Example: Node Addition Flow

**Current (Removal Only):**
```
User Build (100 nodes)
    ↓
Remove inefficient nodes → 95 nodes
    ↓
Re-optimize masteries
    ↓
Result: 95 nodes, better DPS
```

**Future (With Addition):**
```
User Build (100 nodes)
    ↓
Remove inefficient nodes → 95 nodes
    ↓
Add beneficial nodes → 100 nodes (different!)
    ↓
Re-optimize masteries
    ↓
Result: 100 nodes, much better DPS
```

**Ultimate (With Swaps):**
```
User Build (100 nodes)
    ↓
Swap nodes (remove bad, add good) → 100 nodes
    ↓
Optimize entire path → 100 nodes
    ↓
Re-optimize masteries
    ↓
Result: Same point budget, optimal allocation
```

---

## 📊 How to Test Current Features

### Test Mastery Optimization
```bash
# Run full integration test
python3 tests/test_optimizer_with_masteries.py

# Should show:
# - Mastery database loading
# - Optimization running
# - Mastery changes identified
```

### Test Mastery Database
```bash
# Load and explore database
python3 -c "
from src.pob.mastery_optimizer import get_mastery_database

db = get_mastery_database()

# Show sample masteries
for mastery in list(db.masteries.values())[:3]:
    print(f'{mastery.name}:')
    for effect in mastery.available_effects[:2]:
        print(f'  - {effect.stats[0][:60]}')
"
```

### Test Mastery Scoring
```bash
# Test heuristic scoring
python3 -c "
from src.pob.mastery_optimizer import MasteryOptimizer, MasteryEffect, get_mastery_database

db = get_mastery_database()
opt = MasteryOptimizer(db)

# Create test effects
dps_effect = MasteryEffect(1, ['20% increased Damage', 'Penetration'])
life_effect = MasteryEffect(2, ['+50 to maximum Life'])

print(f'DPS effect score (DPS obj): {opt._score_effect(dps_effect, "dps"):.2f}')
print(f'Life effect score (DPS obj): {opt._score_effect(life_effect, "dps"):.2f}')
print(f'Life effect score (Life obj): {opt._score_effect(life_effect, "life"):.2f}')
"
```

---

## 💡 Development Tips

### Parsing PoB Tree Data
- Tree data is in Lua format at `PathOfBuilding/src/TreeData/3_27/tree.lua`
- ~87,000 lines, ~1,500 nodes
- Use regex parsing (full Lua parser not needed)
- Look for patterns like `[nodeId]= { ... }`
- Master nodes have `["isMastery"]= true`
- Connections in `["out"]` and `["in"]` fields

### Testing Strategy
1. Start with small test (parse 10 nodes)
2. Validate structure is correct
3. Scale to full tree
4. Test with real builds
5. Integration test with optimizer

### Performance Considerations
- Tree parsing is slow first time (~5-10s)
- Cache the parsed tree (done in `tree_parser.py`)
- Node addition candidates: Limit to ~20 neighbors for speed
- Total candidates per iteration: Keep under 50

### Debugging
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check tree structure
tree = load_passive_tree()
print(f"Nodes: {tree.count_nodes()}")
print(f"Sample node: {tree.get_node(44298)}")  # Known mastery node
```

---

## 🐛 Known Issues

### Tree Parser (Stubbed)
- **Status:** Foundation created but not implemented
- **Impact:** Can't add nodes yet
- **Priority:** HIGH - Blocks Phase 4 completion

### Mastery Selection (Heuristic)
- **Issue:** Uses keywords, not actual DPS testing
- **Impact:** Could be suboptimal in edge cases
- **Workaround:** Good enough for most cases
- **Future:** Integrate with RelativeCalculator

### No Multi-Node Operations
- **Issue:** Only tries single node changes
- **Impact:** Missing optimal combinations
- **Future:** Genetic algorithm will handle this

---

## 📝 Decision Points for Next Session

### Should You...

**Parse full tree or start small?**
- ✅ **Parse full tree** - Need complete data for node addition
- It's ~5-10s one-time cost, acceptable

**Use heuristics or calculator for masteries?**
- ✅ **Keep heuristics** - Fast and good enough
- Can add calculator testing as enhancement later

**Implement node addition or genetic algorithm first?**
- ✅ **Node addition first** - Simpler, builds on greedy algorithm
- GA can come after, will use node addition anyway

**How many candidates to generate?**
- ✅ **Start with 20 neighbors** - Balance speed vs coverage
- Can tune based on testing

---

## 🎯 Success Criteria for Next Session

**Minimum Viable:**
- [ ] Tree graph parsing works (loads all nodes + connections)
- [ ] Can identify unallocated neighbors
- [ ] Can add nodes while maintaining tree connectivity
- [ ] Optimizer tries node addition candidates
- [ ] At least one test shows node addition improving build

**Stretch Goals:**
- [ ] Node swaps working (remove + add)
- [ ] Path optimization (find better routes)
- [ ] Multi-node operations
- [ ] Genetic algorithm foundation

---

## 📚 References

### PathOfBuilding Tree Data
- Location: `PathOfBuilding/src/TreeData/3_27/tree.lua`
- Format: Lua table with node definitions
- Size: ~87K lines, ~2.8MB

### Our Implementation
- Parser: `src/pob/tree_parser.py`
- Graph class: `PassiveTreeGraph`
- Node class: `PassiveNode`

### Related Code
- PoB tree loader: `PathOfBuilding/src/Classes/TreeTab.lua`
- PoB tree data: `PathOfBuilding/src/TreeData/`

---

## 🎊 Current Project Status

```
Phase 1: PoB Integration          ████████████ 100% ✅
Phase 2: Relative Calculator      ████████████ 100% ✅
Phase 3: Tree Optimizer           ████████████ 100% ✅
  ├─ Node Removal                 ████████████ 100% ✅
  └─ Mastery Optimization         ████████████ 100% ✅
Phase 4: Advanced Optimization    ████████░░░░  60% 🚧
  ├─ Mastery Optimization         ████████████ 100% ✅
  ├─ Node Addition                ░░░░░░░░░░░░   0% ⏭️
  ├─ Tree Graph                   ░░░░░░░░░░░░   0% ⏭️
  └─ Genetic Algorithm            ░░░░░░░░░░░░   0% ⏭️

Overall Progress:                 ████████████  80% 🎯
```

---

**Session Status:** ✅ COMPLETE | Ready for Node Addition

**Next Session Goal:** Parse tree graph and implement node addition

**Estimated Time:** 3-4 hours for tree parsing + node addition

**Risk Level:** LOW - Foundation is solid, just need to implement parsing

---

## 💬 Quick Commands

```bash
# Test mastery system
python3 tests/test_mastery_optimizer.py

# Test optimizer integration
python3 tests/test_optimizer_with_masteries.py

# Load tree parser (will show it's not implemented yet)
python3 -c "from src.pob.tree_parser import load_passive_tree; tree = load_passive_tree()"

# Check PathOfBuilding data
ls -lh PathOfBuilding/src/TreeData/3_27/

# View tree structure
head -100 PathOfBuilding/src/TreeData/3_27/tree.lua
```

---

**Ready to continue? Start with tree graph parsing!** 🚀

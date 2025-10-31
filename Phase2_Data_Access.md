# Phase 2: Data Access Layer
## Week 2 - Reading PoB's Game Data

### Overview
**Goal:** Parse Path of Building's Lua data files to access the passive skill tree, unique items, and gems. This gives us the "search space" for optimization - all possible choices we can make when building a character.

**Time Estimate:** 5 days
**Priority:** Critical - Needed for build generation

**Key Insight:** No database needed! We'll parse PoB's existing Lua data files directly using Python.

---

## Prerequisites

### Completed
- ✅ Phase 1: Can call PoB and get results back

### Python Libraries Needed
```bash
pip install lupa networkx requests
```

### Key PoB Data Files
- `PathOfBuilding/Data/3_0/Tree.lua` - Passive skill tree (~1,500 nodes)
- `PathOfBuilding/Data/Uniques/*.lua` - Unique items (500+ items)
- `PathOfBuilding/Data/Skills/*.lua` - Skill gems and supports
- `PathOfBuilding/TreeData/` - Tree JSON data (alternative format)

---

## Day 1-2: Parse Passive Skill Tree

The passive tree is a graph with ~1,500 nodes. We'll use NetworkX to represent it.

### Tasks

#### 1. Explore Tree Data Structure

**Claude Code Prompt:**
> "Examine PathOfBuilding/TreeData/ and PathOfBuilding/Data/3_0/Tree.lua to understand the passive tree data structure. Show me:
> 1. How nodes are represented (id, name, stats, position)
> 2. How connections between nodes are stored
> 3. How to identify keystones vs notables vs small nodes
> 4. How ascendancy nodes are differentiated
> 5. Which format is easier to parse: JSON from TreeData/ or Lua from Data/"

#### 2. Implement Tree Parser

**Claude Code Prompt:**
> "Create src/pob/tree_parser.py with a PassiveTreeParser class. Use the lupa library to execute Lua and extract tree data. Requirements:
>
> - load_tree() -> networkx.Graph: Returns the full passive tree
> - Each node should have attributes:
>   - node_id (int)
>   - name (str)
>   - stats (list of str) - The modifier text
>   - type (str) - 'normal', 'notable', 'keystone', 'jewel', 'mastery'
>   - position (tuple) - (x, y) coordinates
>   - ascendancy (str or None) - Ascendancy name if applicable
>   - icon (str) - Icon identifier
> - Edges represent valid connections
> - Handle both 3.0 tree format and current league
> - Add caching to avoid re-parsing (use pickle)"

**File Location:** `src/pob/tree_parser.py`

**Expected Usage:**
```python
from src.pob.tree_parser import PassiveTreeParser

parser = PassiveTreeParser()
tree = parser.load_tree()

print(f"Total nodes: {tree.number_of_nodes()}")
print(f"Total edges: {tree.number_of_edges()}")

# Find a specific node
resolute_technique = parser.find_node_by_name("Resolute Technique")
print(f"RT Node ID: {resolute_technique['node_id']}")
print(f"Stats: {resolute_technique['stats']}")
```

#### 3. Implement Tree Query Methods

**Claude Code Prompt:**
> "Add these utility methods to PassiveTreeParser:
> - find_node_by_name(name: str) -> dict: Case-insensitive search
> - find_nodes_by_type(node_type: str) -> list: Get all keystones, etc.
> - get_starting_nodes() -> dict: Map class name to starting node ID
> - find_keystones() -> list: Return all keystone nodes
> - find_notable() -> list: Return all notable nodes
> - get_ascendancy_nodes(ascendancy_name: str) -> list
> - find_shortest_path(from_id: int, to_id: int) -> list: Use NetworkX
> Include docstrings and examples for each method."

#### 4. Create Tree Visualization (Optional but Cool)

**Claude Code Prompt:**
> "Create src/pob/tree_visualizer.py that uses matplotlib or networkx's drawing functions to visualize a path on the tree. Input: set of allocated node IDs. Output: PNG image showing the tree with allocated nodes highlighted. This is useful for debugging path optimization later."

#### 5. Test Tree Parser

**Claude Code Prompt:**
> "Create tests/test_tree_parser.py with tests:
> 1. Test tree loads successfully
> 2. Verify node count is ~1,500 (adjust based on current league)
> 3. Test finding 'Resolute Technique' keystone
> 4. Test finding all keystones (should be ~50-80)
> 5. Test starting nodes exist for all 7 classes
> 6. Test shortest path from Duelist start to 'Point Blank' keystone
> 7. Test ascendancy nodes are properly tagged
> Print readable output showing what was found."

---

## Day 3-4: Parse Unique Items

### Tasks

#### 1. Explore Item Data Structure

**Claude Code Prompt:**
> "Examine PathOfBuilding/Data/Uniques/ directory. Show me:
> 1. How items are structured in the Lua files
> 2. What information is available for each item
> 3. How implicit vs explicit mods are stored
> 4. How requirements (level, stats) are represented
> 5. Are there separate files per item type (weapons, armor, etc.)?"

#### 2. Implement Item Parser

**Claude Code Prompt:**
> "Create src/pob/item_parser.py with an ItemParser class. Requirements:
>
> - load_unique_items() -> dict: Returns all unique items
> - Item dict structure:
>   - name (str)
>   - base_type (str) - e.g., 'Vaal Axe', 'Astral Plate'
>   - item_class (str) - 'weapon', 'body_armor', 'helmet', etc.
>   - implicit_mods (list of str)
>   - explicit_mods (list of str)
>   - requirements (dict) - level, str, dex, int
>   - tags (list) - weapon type tags
>   - league_specific (bool)
> - Cache parsed items to disk
> - Handle parsing all files in Data/Uniques/
> Use lupa library for Lua execution"

**File Location:** `src/pob/item_parser.py`

#### 3. Implement Item Query Methods

**Claude Code Prompt:**
> "Add utility methods to ItemParser:
> - get_weapons() -> dict: All weapon uniques
> - get_armor() -> dict: All armor uniques
> - get_accessories() -> dict: Rings, amulets, belts
> - get_items_for_slot(slot: str) -> dict: Filter by equipment slot
> - get_items_for_skill(skill: str) -> dict: Items that synergize with skill
>   - For 'Cyclone': two-handed axes, swords, maces, or dual wield
>   - For 'Spectral Throw': one-handed weapons
>   - etc.
> - search_items(keyword: str) -> dict: Search by name or mod text
> - get_items_under_budget(max_chaos: int, poeninja_api: bool = False) -> dict
> Include caching and examples."

#### 4. Integrate poe.ninja Pricing (Basic)

**Claude Code Prompt:**
> "Create src/pob/pricing.py with a PoeNinjaPricing class:
> - fetch_unique_prices(league: str = 'Standard') -> dict: Get prices from API
> - get_item_price(item_name: str) -> float: Returns price in chaos
> - cache_prices(expiry_hours: int = 24): Cache prices to avoid spam
> - Handle API rate limits gracefully
> Use requests library. poe.ninja API endpoint:
>   https://poe.ninja/api/data/itemoverview?league=X&type=UniqueWeapon
> Document API structure and response format."

**File Location:** `src/pob/pricing.py`

#### 5. Test Item Parser

**Claude Code Prompt:**
> "Create tests/test_item_parser.py:
> 1. Test loading all unique items (should be 500+)
> 2. Test finding 'Starforge' (unique Infernal Sword)
> 3. Verify it has correct mods
> 4. Test filtering weapons for Cyclone
> 5. Test filtering by budget (mock poe.ninja API)
> 6. Test searching items by keyword
> Print summary statistics:
>    - Total uniques found
>    - Breakdown by type (weapons, armor, etc.)
>    - Most expensive items (top 10)
>    - League-specific items count"

---

## Day 5: Parse Skill Gems

### Tasks

#### 1. Explore Gem Data

**Claude Code Prompt:**
> "Examine PathOfBuilding/Data/Skills/ to understand gem data structure. Show me:
> 1. How active skill gems are represented
> 2. How support gems are represented
> 3. What data is available per gem level (1-20)
> 4. How quality bonuses are stored
> 5. How gem tags work (melee, projectile, spell, etc.)"

#### 2. Implement Gem Parser

**Claude Code Prompt:**
> "Create src/pob/gem_parser.py with a GemParser class:
>
> - load_skill_gems() -> dict: All active skill gems
> - load_support_gems() -> dict: All support gems
>
> Gem dict structure:
>   - name (str)
>   - gem_type (str) - 'active' or 'support'
>   - tags (list) - 'melee', 'projectile', 'spell', etc.
>   - level_data (dict) - Per-level stats (1-20)
>     - damage_effectiveness
>     - mana_cost
>     - level_requirement
>   - quality_bonuses (dict) - What 20% quality gives
>   - description (str)
>
> Use lupa for Lua parsing, cache results"

**File Location:** `src/pob/gem_parser.py`

#### 3. Implement Gem Compatibility Logic

**Claude Code Prompt:**
> "Add methods to determine which gems work together:
> - get_supports_for_skill(skill_name: str) -> list: Valid supports for a skill
>   - Match by tags (e.g., Cyclone is 'melee', so Melee Phys works)
>   - Exclude incompatible supports (e.g., Multistrike doesn't work with Vaal skills)
> - get_recommended_supports(skill_name: str, sort_by: str = 'damage') -> list:
>   - Return supports sorted by impact (damage, utility, defense)
>   - Use heuristics based on support type
> - validate_link_setup(skill: str, supports: list) -> tuple[bool, str]:
>   - Check if all supports are compatible
>   - Return (is_valid, error_message)
> Reference PoB's gem tag system for compatibility rules"

#### 4. Create Gem Database

**Claude Code Prompt:**
> "Create a simplified gem database in src/pob/gem_database.py as a Python dict for quick lookups. Include:
> - Common skill gems with tags
> - Common support gems with tags and multipliers
> - Typical 6-link setups for popular skills
> This is for quick validation without parsing Lua every time.
>
> Example structure:
> ```python
> SKILLS = {
>     'Cyclone': {
>         'tags': ['attack', 'melee', 'aoe', 'channel'],
>         'weapon_types': ['two_hand_axe', 'two_hand_sword', 'one_hand_axe', 'one_hand_sword'],
>     },
>     ...
> }
>
> SUPPORTS = {
>     'Melee Physical Damage': {
>         'tags': ['support', 'melee', 'physical'],
>         'more_multipliers': {'physical_damage': 1.49},  # Level 20
>     },
>     ...
> }
> ```"

#### 5. Test Gem Parser

**Claude Code Prompt:**
> "Create tests/test_gem_parser.py:
> 1. Test loading all gems (should be 200+ including supports)
> 2. Test finding 'Cyclone' and verify tags
> 3. Test finding valid supports for Cyclone
> 4. Test that incompatible supports are excluded
> 5. Test recommended 6-link for Cyclone
> 6. Test gem level scaling (compare level 1 vs 20)
> Print useful summary:
>    - Total active skills
>    - Total support gems
>    - Most common tags
>    - Example 6-link setup for Cyclone"

---

## Integration: Complete Data Access Layer

### Task: Create Unified Data Loader

**Claude Code Prompt:**
> "Create src/pob/data_loader.py that combines all parsers:
>
> ```python
> class PoBDataLoader:
>     '''Unified interface to all PoB game data.'''
>
>     def __init__(self, pob_path='./PathOfBuilding'):
>         self.tree_parser = PassiveTreeParser(pob_path)
>         self.item_parser = ItemParser(pob_path)
>         self.gem_parser = GemParser(pob_path)
>         self.pricing = PoeNinjaPricing()
>
>     def load_all(self):
>         '''Load all data with progress indicators.'''
>         print('Loading passive tree...')
>         self.tree = self.tree_parser.load_tree()
>
>         print('Loading unique items...')
>         self.items = self.item_parser.load_unique_items()
>
>         print('Loading gems...')
>         self.skills = self.gem_parser.load_skill_gems()
>         self.supports = self.gem_parser.load_support_gems()
>
>         print('Fetching prices...')
>         self.prices = self.pricing.fetch_unique_prices()
>
>         print('✓ All data loaded!')
>
>     def get_build_search_space(self, skill: str, budget: int) -> dict:
>         '''Get all valid choices for a build.'''
>         return {
>             'tree': self.tree,
>             'valid_items': self.item_parser.get_items_for_skill(skill),
>             'affordable_items': self.pricing.filter_by_budget(budget),
>             'valid_supports': self.gem_parser.get_supports_for_skill(skill),
>         }
> ```
>
> Add proper error handling and caching. Include a CLI test script."

**File Location:** `src/pob/data_loader.py`

---

## Deliverables Checklist

- [ ] `src/pob/tree_parser.py` - Passive tree parser with NetworkX graph
- [ ] `src/pob/item_parser.py` - Unique item parser
- [ ] `src/pob/gem_parser.py` - Skill and support gem parser
- [ ] `src/pob/gem_database.py` - Simplified gem compatibility data
- [ ] `src/pob/pricing.py` - poe.ninja API integration
- [ ] `src/pob/data_loader.py` - Unified data loader
- [ ] `tests/test_tree_parser.py` - Tree parser tests
- [ ] `tests/test_item_parser.py` - Item parser tests
- [ ] `tests/test_gem_parser.py` - Gem parser tests
- [ ] `tests/test_data_loader.py` - Integration test
- [ ] Documentation in docstrings

---

## Success Criteria

### Must Have ✅
1. Can load passive tree as NetworkX graph with ~1,500 nodes
2. Can query tree for keystones, notables, and paths
3. Can load all unique items (500+)
4. Can filter items by type, slot, and skill compatibility
5. Can load all gems with tags and compatibility info
6. Can determine valid support gems for any skill
7. All data loads in <10 seconds total
8. All parsers have caching implemented

### Nice to Have 🎯
1. Tree visualization working
2. poe.ninja pricing integration complete
3. Smart item recommendations based on skill
4. Performance: data loads in <5 seconds

---

## Common Issues & Solutions

### Issue: Lua parsing fails with "module not found"
**Solution:** PoB's Lua files use relative imports. Set working directory:
```python
lua = LuaRuntime()
os.chdir('./PathOfBuilding')
lua.execute('dofile("Data/3_0/Tree.lua")')
```

### Issue: Tree has disconnected nodes
**Solution:** Some nodes (ascendancy starts, cluster jewels) aren't connected to main tree. This is expected. Use `nx.is_connected(tree.subgraph(allocated_nodes))` to validate player's tree.

### Issue: Item mods are hard to parse
**Solution:** Don't try to parse mod semantics yet! Just store them as strings. Phase 4 will handle mod evaluation (PoB does this for us).

### Issue: poe.ninja API rate limits
**Solution:** Implement caching with 24-hour expiry:
```python
@functools.lru_cache(maxsize=1)
def fetch_prices():
    # Only called once per day
    pass
```

### Issue: Gem tags don't match PoB's internal tags
**Solution:** PoB's gem tags are in `Data/Skills/act_*.lua`. Some gems have multiple tag sources. When in doubt, test by creating a build and seeing if PoB allows the support.

---

## Testing Checklist

Run each test suite and verify:

```bash
# Tree parser
pytest tests/test_tree_parser.py -v
# Expected: ~1,500 nodes, 7 starting positions found, keystone queries work

# Item parser
pytest tests/test_item_parser.py -v
# Expected: 500+ items loaded, filtering works, Starforge found

# Gem parser
pytest tests/test_gem_parser.py -v
# Expected: 200+ gems, Cyclone found, supports filtered correctly

# Full integration
python -m src.pob.data_loader
# Expected: All data loads successfully in <10 seconds
```

---

## Performance Targets

| Operation | Target | Stretch Goal |
|-----------|---------|--------------|
| Load passive tree | <3s | <1s |
| Load all items | <2s | <1s |
| Load all gems | <1s | <0.5s |
| Query tree path | <0.1s | <0.01s |
| Filter items | <0.1s | <0.01s |

Use caching and pickle to achieve these targets.

---

## Next Steps

Once Phase 2 is complete:
1. **Verify data quality:** Spot-check random items, nodes, gems match PoB
2. **Profile performance:** If loads are slow, add more caching
3. **Move to Phase 3:** Build representation and XML generation

**Phase 3 Preview:** We'll create a Build class that represents a complete character, then generate valid PoB XML from it.

---

## Quick Reference Commands

```bash
# Test data loading speed
python -c "from src.pob.data_loader import PoBDataLoader; import time; start = time.time(); d = PoBDataLoader(); d.load_all(); print(f'Loaded in {time.time()-start:.2f}s')"

# Interactive exploration
python
>>> from src.pob.tree_parser import PassiveTreeParser
>>> parser = PassiveTreeParser()
>>> tree = parser.load_tree()
>>> keystones = parser.find_nodes_by_type('keystone')
>>> print([tree.nodes[k]['name'] for k in keystones])

# Check item prices
python
>>> from src.pob.pricing import PoeNinjaPricing
>>> pricing = PoeNinjaPricing()
>>> prices = pricing.fetch_unique_prices('Standard')
>>> print(pricing.get_item_price('Starforge'))
```

---

## Resources

- **NetworkX Docs:** https://networkx.org/documentation/stable/
- **lupa GitHub:** https://github.com/scoder/lupa
- **poe.ninja API:** https://poe.ninja/api/docs (unofficial)
- **PoB Data Files:** Explore PathOfBuilding/Data/ directory
- **Lua 5.1 Reference:** https://www.lua.org/manual/5.1/

---

**Ready to continue?** Start Phase 2, Day 1: Exploring the tree data structure!

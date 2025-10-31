# Phase 3: Build Representation & Validation
## Week 3 - Creating and Converting Builds

### Overview
**Goal:** Create Python data structures to represent complete PoE builds, then convert them to PoB's XML format. By the end, you'll be able to define a build in Python and generate a valid PoB import code that players can use.

**Time Estimate:** 5 days
**Priority:** Critical - Bridge between Python and PoB

**Key Achievement:** Round-trip works: Python Build → PoB XML → Import to PoB → Verify

---

## Prerequisites

### Completed
- ✅ Phase 1: Can call PoB and get results
- ✅ Phase 2: Can read all PoB game data

### New Libraries
```bash
pip install lxml dataclasses-json
```

### Study Materials
- Download 5-10 build codes from poe.ninja
- Decode them to XML using Phase 1's codec
- Study the XML structure in detail

---

## Day 1-2: Build Data Model

### Tasks

#### 1. Analyze PoB XML Structure

**Claude Code Prompt:**
> "I have decoded XML files from 5 popular builds in examples/. Analyze them and create a detailed spec of the PoB XML structure. Document:
> 1. Required XML elements and their attributes
> 2. How passive tree is encoded (node IDs format)
> 3. How items are represented in XML
> 4. How skill gems and links are structured
> 5. What config options are available
> 6. Class and ascendancy ID mappings
> Create a markdown spec document: docs/pob_xml_spec.md"

#### 2. Design Build Class

**Claude Code Prompt:**
> "Create src/models/build.py with a Build dataclass that represents a complete PoE character. Requirements:
>
> ```python
> @dataclass
> class Build:
>     '''Represents a Path of Exile character build.'''
>
>     # Character basics
>     class_name: str = 'Duelist'
>     ascendancy: str = 'Slayer'
>     level: int = 90
>     bandit_choice: str = 'None'  # Alira, Kraityn, Oak, or None
>
>     # Passive tree
>     allocated_nodes: Set[int] = field(default_factory=set)
>     # Node IDs from the passive tree
>
>     # Items (slot -> item dict)
>     items: Dict[str, Optional[Dict]] = field(default_factory=lambda: {
>         'Weapon 1': None,
>         'Weapon 2': None,  # or Shield
>         'Helmet': None,
>         'Body Armour': None,
>         'Gloves': None,
>         'Boots': None,
>         'Amulet': None,
>         'Ring 1': None,
>         'Ring 2': None,
>         'Belt': None,
>         'Flask 1-5': [None] * 5,
>         'Jewel 1-N': {},  # Jewel node ID -> jewel
>     })
>
>     # Skills
>     main_skill: str = 'Cyclone'
>     skill_links: List[List[str]] = field(default_factory=list)
>     # Each inner list is a gem link group, e.g.:
>     # [['Cyclone', 'Melee Phys', 'Brutality', 'Fortify', 'Impale', 'Infused Channelling']]
>
>     # Configuration
>     config: Dict[str, Any] = field(default_factory=dict)
>     # Boss fight, shock, crit recently, etc.
>
>     # Cached calculation results (filled after evaluation)
>     stats: Optional[Dict] = None
>
>     def __post_init__(self):
>         '''Validate build on creation.'''
>         pass
> ```
>
> Include type hints, docstrings, and sensible defaults for a league starter build."

**File Location:** `src/models/build.py`

#### 3. Add Validation Methods

**Claude Code Prompt:**
> "Add validation methods to the Build class:
>
> ```python
> def available_points(self) -> int:
>     '''Calculate available passive points at current level.'''
>     # Base: level - 1
>     # Quests: 22 respec points from quests
>     # Total: ~120 points at level 100
>
> def calculate_points_spent(self, tree_graph) -> int:
>     '''Calculate total passive points allocated.'''
>     return len(self.allocated_nodes)
>
> def is_valid(self, tree_graph, item_db) -> Tuple[bool, List[str]]:
>     '''
>     Validate build for correctness.
>
>     Returns:
>         (is_valid, list_of_errors)
>
>     Checks:
>     - Point budget not exceeded
>     - Passive tree is connected (path from start node)
>     - All items exist in database
>     - All gems are compatible
>     - Required attributes met for items
>     '''
>
> def _check_tree_connectivity(self, tree_graph) -> bool:
>     '''Verify passive tree forms connected path from class start.'''
>     # Use NetworkX to check if allocated nodes are connected
>
> def _check_item_requirements(self, item_db) -> List[str]:
>     '''Check if character meets item requirements.'''
>     # Need to calculate total attributes from tree + items
>
> def clone(self) -> 'Build':
>     '''Create a deep copy of this build.'''
>     import copy
>     return copy.deepcopy(self)
> ```
>
> Implement these methods with proper error messages."

#### 4. Create Constraints Class

**Claude Code Prompt:**
> "Create src/models/constraints.py with a Constraints dataclass:
>
> ```python
> @dataclass
> class Constraints:
>     '''Constraints and requirements for build optimization.'''
>
>     # Defensive requirements
>     min_life: int = 4000
>     min_energy_shield: int = 0
>     min_effective_hp: int = 100000
>
>     # Resistances
>     min_fire_res: int = 75
>     min_cold_res: int = 75
>     min_lightning_res: int = 75
>     min_chaos_res: int = -60
>
>     # Attributes (None = no requirement)
>     min_strength: Optional[int] = None
>     min_dexterity: Optional[int] = None
>     min_intelligence: Optional[int] = None
>
>     # Budget
>     max_budget_chaos: int = 10_000_000  # ~100 divines
>
>     # Passive tree
>     max_passive_points: Optional[int] = None
>     required_keystones: Set[str] = field(default_factory=set)
>     forbidden_keystones: Set[str] = field(default_factory=set)
>     required_nodes: Set[int] = field(default_factory=set)
>
>     # Performance
>     min_dps: int = 1_000_000
>     min_boss_dps: Optional[int] = None
>
>     # Other
>     max_level: int = 95
>     require_capped_res: bool = True
>
>     def validate_build(self, build_stats: dict) -> Tuple[bool, List[str]]:
>         '''
>         Check if build meets all constraints.
>
>         Returns:
>             (is_valid, list_of_violations)
>         '''
>
>     def calculate_penalty(self, build_stats: dict) -> float:
>         '''
>         Calculate constraint violation penalty.
>         Used in optimization fitness functions.
>         Returns 0 if all constraints met, >0 otherwise.
>         '''
> ```
>
> Implement validation logic for all constraint types."

**File Location:** `src/models/constraints.py`

#### 5. Test Build Model

**Claude Code Prompt:**
> "Create tests/test_build_model.py:
> 1. Test creating a minimal valid build
> 2. Test that invalid builds are caught (overspent points, disconnected tree)
> 3. Test build cloning
> 4. Test constraint validation with various scenarios
> 5. Test that builds with different violations are correctly identified
> Use pytest and include clear test names."

---

## Day 3-4: XML Generation

This is the critical piece - converting our Build object to PoB's XML format.

### Tasks

#### 1. Study PoB Export Format

**Claude Code Prompt:**
> "Using the examples/ directory, identify the exact XML structure PoB expects. Create a template in docs/pob_xml_template.xml with placeholders marked clearly. Pay special attention to:
> - XML declaration and encoding
> - PathOfBuilding root element attributes
> - Build element and its attributes
> - Tree element structure for passive nodes
> - Items element and item representation
> - Skills element and gem links
> - Config element for configuration options
> Mark all variable sections with {{PLACEHOLDER}} syntax."

#### 2. Implement XML Generator Core

**Claude Code Prompt:**
> "Create src/pob/xml_generator.py with a BuildXMLGenerator class:
>
> ```python
> class BuildXMLGenerator:
>     '''Generate Path of Building XML from Build objects.'''
>
>     def __init__(self, item_database, gem_database):
>         self.items = item_database
>         self.gems = gem_database
>
>     def generate_xml(self, build: Build) -> str:
>         '''
>         Convert Build object to PoB XML string.
>
>         Args:
>             build: Build instance to convert
>
>         Returns:
>             Complete PoB XML string
>
>         Raises:
>             ValueError: If build is invalid
>         '''
>
>     def _generate_build_element(self, build: Build) -> ET.Element:
>         '''Create <Build> element with metadata.'''
>
>     def _generate_tree_element(self, build: Build) -> ET.Element:
>         '''Create <Tree> element with allocated passives.'''
>
>     def _generate_items_element(self, build: Build) -> ET.Element:
>         '''Create <Items> element with all equipment.'''
>
>     def _generate_skills_element(self, build: Build) -> ET.Element:
>         '''Create <Skills> element with gem links.'''
>
>     def _generate_config_element(self, build: Build) -> ET.Element:
>         '''Create <Config> element with configuration.'''
>
>     def encode_for_import(self, xml: str) -> str:
>         '''
>         Encode XML as PoB import code (base64 + zlib).
>         Can reuse codec.py from Phase 1.
>         '''
> ```
>
> Use lxml library for XML generation. Ensure output matches PoB's expected format exactly."

**File Location:** `src/pob/xml_generator.py`

#### 3. Implement Class/Ascendancy Mappings

**Claude Code Prompt:**
> "Create src/pob/constants.py with all the ID mappings PoB uses:
>
> ```python
> # Class ID mappings (PoB internal IDs)
> CLASS_IDS = {
>     'Scion': 0,
>     'Marauder': 1,
>     'Ranger': 2,
>     'Witch': 3,
>     'Duelist': 4,
>     'Templar': 5,
>     'Shadow': 6,
> }
>
> # Ascendancy ID mappings
> ASCENDANCY_IDS = {
>     'None': 0,
>     # Duelist
>     'Slayer': 1,
>     'Gladiator': 2,
>     'Champion': 3,
>     # Add all ascendancies...
> }
>
> # Starting node IDs for each class
> CLASS_START_NODES = {
>     'Scion': 31628,
>     'Marauder': 35679,
>     'Ranger': 17218,
>     'Witch': 27864,
>     'Duelist': 36634,
>     'Templar': 15372,
>     'Shadow': 57538,
> }
>
> # Item slot IDs
> ITEM_SLOTS = [
>     'Weapon 1',
>     'Weapon 2',
>     'Helmet',
>     'Body Armour',
>     'Gloves',
>     'Boots',
>     'Amulet',
>     'Ring 1',
>     'Ring 2',
>     'Belt',
> ]
> ```
>
> Extract these from PoB source or decoded XMLs. Verify all mappings are correct."

**File Location:** `src/pob/constants.py`

#### 4. Test XML Generation

**Claude Code Prompt:**
> "Create tests/test_xml_generation.py:
>
> 1. **Test minimal build generation:**
>    - Create simplest valid build (level 90 Duelist with Cyclone)
>    - Generate XML
>    - Validate XML is well-formed (parse it back)
>    - Verify key elements exist
>
> 2. **Test with items:**
>    - Create build with weapons and armor
>    - Verify items appear correctly in XML
>
> 3. **Test with passive tree:**
>    - Allocate 50 random nodes
>    - Verify all nodes appear in XML
>    - Check format matches PoB's expectations
>
> 4. **Test round-trip:**
>    - Take example build XML
>    - Parse to Build object (need parser)
>    - Generate XML back
>    - Compare with original (some differences OK, but structure must match)
>
> 5. **Test import code generation:**
>    - Generate XML
>    - Encode to import code
>    - Decode back
>    - Verify XML is identical
>
> Include assertions and clear error messages."

---

## Day 4-5: XML Parsing (Reverse Direction)

We also need to parse PoB XML into our Build objects for analysis and mutation.

### Tasks

#### 1. Implement XML Parser

**Claude Code Prompt:**
> "Create src/pob/xml_parser.py with a BuildXMLParser class:
>
> ```python
> class BuildXMLParser:
>     '''Parse Path of Building XML into Build objects.'''
>
>     def __init__(self, item_database, gem_database):
>         self.items = item_database
>         self.gems = gem_database
>
>     def parse_xml(self, xml_string: str) -> Build:
>         '''
>         Parse PoB XML string into Build object.
>
>         Args:
>             xml_string: Complete PoB XML
>
>         Returns:
>             Build instance
>
>         Raises:
>             ValueError: If XML is malformed or unsupported
>         '''
>
>     def parse_from_code(self, pob_code: str) -> Build:
>         '''
>         Parse PoB import code into Build object.
>         Decodes base64+zlib, then parses XML.
>         '''
>
>     def _parse_build_element(self, root: ET.Element) -> dict:
>         '''Extract character info from <Build> element.'''
>
>     def _parse_tree_element(self, root: ET.Element) -> Set[int]:
>         '''Extract allocated nodes from <Tree> element.'''
>
>     def _parse_items_element(self, root: ET.Element) -> Dict:
>         '''Extract items from <Items> element.'''
>
>     def _parse_skills_element(self, root: ET.Element) -> List[List[str]]:
>         '''Extract gem links from <Skills> element.'''
>
>     def _parse_config_element(self, root: ET.Element) -> Dict:
>         '''Extract config from <Config> element.'''
> ```
>
> Handle missing elements gracefully with sensible defaults."

**File Location:** `src/pob/xml_parser.py`

#### 2. Test Parsing Real Builds

**Claude Code Prompt:**
> "Create tests/test_xml_parser.py:
> 1. Test parsing all example builds from examples/
> 2. Verify parsed Build objects have correct:
>    - Class and ascendancy
>    - Level
>    - Number of allocated nodes
>    - Number of equipped items
>    - Main skill name
> 3. Test parsing from import code (base64 encoded)
> 4. Test parsing builds with missing elements (should use defaults)
> 5. Test error handling for completely invalid XML
> Print summary for each parsed build showing key stats."

---

## Day 5: Complete Integration & Validation

### Tasks

#### 1. Round-Trip Test

**Claude Code Prompt:**
> "Create tests/test_round_trip.py that validates the complete pipeline:
>
> 1. Take example build XML from examples/cyclone_slayer.xml
> 2. Parse it to Build object using BuildXMLParser
> 3. Generate XML back using BuildXMLGenerator
> 4. Call PoBCalculator on both original and regenerated XML
> 5. Compare calculation results - should be identical or very close
> 6. If differences exist, identify where they come from
>
> This test proves our Build representation is complete and accurate."

#### 2. Import Into Actual PoB

This is the ultimate validation - import your generated builds into the real PoB app.

**Claude Code Prompt:**
> "Create a script examples/test_in_pob.py that:
> 1. Creates a simple but valid Cyclone Slayer build
> 2. Generates PoB import code
> 3. Prints the code with instructions:
>    - Open Path of Building
>    - Click Import/Export
>    - Paste the code
>    - Click Import
> 4. Asks user to verify it imported successfully
> 5. Asks user to report the DPS and Life shown in PoB
> 6. Compares with our calculated values
>
> This is manual validation but essential for confidence."

**Manual Test Checklist:**
```markdown
## Manual PoB Import Test

- [ ] Generated code imports without errors
- [ ] Character class and ascendancy correct
- [ ] Passive tree shows allocated nodes
- [ ] Items appear in correct slots
- [ ] Skill gems show in correct links
- [ ] DPS calculation matches our output (within 5%)
- [ ] Life calculation matches our output (within 5%)
- [ ] Resistances show correctly
- [ ] Build is playable (no obvious errors)
```

#### 3. Create Build Templates

**Claude Code Prompt:**
> "Create src/models/build_templates.py with factory functions for common build archetypes:
>
> ```python
> def create_cyclone_slayer(level: int = 90) -> Build:
>     '''Create a basic Cyclone Slayer template.'''
>     return Build(
>         class_name='Duelist',
>         ascendancy='Slayer',
>         level=level,
>         main_skill='Cyclone',
>         skill_links=[
>             ['Cyclone', 'Melee Physical Damage', 'Brutality',
>              'Fortify', 'Impale', 'Infused Channelling']
>         ],
>         # Add some basic passive allocations
>         allocated_nodes={36634, ...},  # Starting area + life nodes
>     )
>
> def create_league_starter(class_name: str, skill: str) -> Build:
>     '''Create a minimal league starter template.'''
>
> def create_boss_killer(class_name: str, skill: str) -> Build:
>     '''Create a single-target focused template.'''
>
> def create_mapper(class_name: str, skill: str) -> Build:
>     '''Create a clear-speed focused template.'''
> ```
>
> These templates are starting points for optimization."

**File Location:** `src/models/build_templates.py`

#### 4. Integration with Calculator

**Claude Code Prompt:**
> "Update src/models/build.py to add a method that evaluates itself:
>
> ```python
> def evaluate(self, calculator: PoBCalculator) -> Dict:
>     '''
>     Evaluate this build using PoB calculator.
>     Caches result in self.stats.
>
>     Args:
>         calculator: PoBCalculator instance
>
>     Returns:
>         dict: Calculation results
>     '''
>     if self.stats is not None:
>         return self.stats  # Return cached
>
>     # Generate XML
>     generator = BuildXMLGenerator(items_db, gems_db)
>     xml = generator.generate_xml(self)
>
>     # Evaluate
>     self.stats = calculator.evaluate_build(xml)
>     return self.stats
> ```
>
> This makes builds self-contained for evaluation."

---

## Deliverables Checklist

- [ ] `src/models/build.py` - Complete Build dataclass with validation
- [ ] `src/models/constraints.py` - Constraints dataclass
- [ ] `src/models/build_templates.py` - Build factory functions
- [ ] `src/pob/xml_generator.py` - Build → XML converter
- [ ] `src/pob/xml_parser.py` - XML → Build converter
- [ ] `src/pob/constants.py` - ID mappings and constants
- [ ] `docs/pob_xml_spec.md` - XML format documentation
- [ ] `docs/pob_xml_template.xml` - XML template
- [ ] `tests/test_build_model.py` - Build validation tests
- [ ] `tests/test_xml_generation.py` - XML generation tests
- [ ] `tests/test_xml_parser.py` - XML parsing tests
- [ ] `tests/test_round_trip.py` - Round-trip validation
- [ ] `examples/test_in_pob.py` - Manual PoB import script

---

## Success Criteria

### Must Have ✅
1. Can create Build objects in Python
2. Build validation catches all major errors
3. Can generate valid PoB XML from Build objects
4. Can parse existing PoB XML into Build objects
5. Round-trip works: Build → XML → Build (preserved)
6. Generated codes import successfully into actual PoB
7. Calculated stats match PoB (within 5%)
8. All tests pass

### Nice to Have 🎯
1. XML generation is fast (<0.1s per build)
2. Pretty-printed XML for debugging
3. Build comparison utilities
4. JSON export for builds
5. Build templates for 5+ archetypes

---

## Common Issues & Solutions

### Issue: Generated XML doesn't import
**Solution:** Compare byte-by-byte with working example. Common issues:
- Wrong XML encoding (must be UTF-8)
- Missing required attributes
- Invalid node IDs (check against tree data)
- Malformed item strings

### Issue: PoB shows different stats than our calculator
**Solution:** Check these first:
- Config options (are they identical?)
- Skill gem levels (level 20 vs 1?)
- Item quality settings
- Flasks active/inactive
Most differences come from config mismatches.

### Issue: Tree validation fails
**Solution:** Ensure starting node is included:
```python
start_node = CLASS_START_NODES[build.class_name]
build.allocated_nodes.add(start_node)  # Always include!
```

### Issue: Items don't show in PoB
**Solution:** PoB needs exact item text format. Copy from working builds:
```xml
<Item id="1">
Rarity: UNIQUE
Starforge
Infernal Sword
Requires Level 67, 113 Str, 113 Dex
Sockets: R-R-R-R-R-R
LevelReq: 67
Implicits: 0
{range:0.6}(400-500)% increased Physical Damage
...
</Item>
```

---

## Testing Checklist

```bash
# Unit tests
pytest tests/test_build_model.py -v
pytest tests/test_xml_generation.py -v
pytest tests/test_xml_parser.py -v

# Integration test
pytest tests/test_round_trip.py -v

# Manual validation
python examples/test_in_pob.py

# All tests
pytest tests/ -v --cov=src
```

---

## Performance Targets

| Operation | Target | Stretch Goal |
|-----------|---------|--------------|
| Build validation | <0.01s | <0.001s |
| XML generation | <0.1s | <0.01s |
| XML parsing | <0.1s | <0.01s |
| Full round-trip | <0.5s | <0.1s |

---

## Next Steps

Once Phase 3 is complete:
1. **Validate extensively:** Test with 20+ different builds
2. **Fix any edge cases:** Not all builds will work first try
3. **Move to Phase 4:** Optimization algorithms

**Phase 4 Preview:** We'll implement genetic algorithms, passive tree optimization, and item selection algorithms to automatically generate optimized builds.

---

## Quick Reference Commands

```bash
# Generate and print PoB code for a build
python -c "
from src.models.build_templates import create_cyclone_slayer
from src.pob.xml_generator import BuildXMLGenerator
build = create_cyclone_slayer()
gen = BuildXMLGenerator(items, gems)
xml = gen.generate_xml(build)
code = gen.encode_for_import(xml)
print(code)
"

# Parse and examine a build code
python -c "
from src.pob.xml_parser import BuildXMLParser
from src.pob.codec import decode_pob_code
parser = BuildXMLParser(items, gems)
build = parser.parse_from_code('your_code_here')
print(f'{build.class_name} {build.ascendancy} Level {build.level}')
print(f'Nodes: {len(build.allocated_nodes)}')
"
```

---

## Resources

- **lxml Tutorial:** https://lxml.de/tutorial.html
- **PoB XML Examples:** Decode builds from poe.ninja
- **dataclasses Guide:** https://docs.python.org/3/library/dataclasses.html

---

**Ready for the critical phase?** Start Day 1: Analyzing PoB XML structure!

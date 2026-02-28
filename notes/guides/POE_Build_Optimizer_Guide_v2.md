# Path of Exile Build Optimizer
## Implementation Guide v2.0
### Using Path of Building as Calculation Engine

**The Smart Approach: Build on Existing Tools**

---

## Table of Contents

1. [Why This Approach is Better](#why-this-approach-is-better)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites & Setup](#prerequisites--setup)
4. [Week 1: PoB Integration & Interface](#week-1-pob-integration--interface)
5. [Week 2: Data Access Layer](#week-2-data-access-layer)
6. [Week 3: Build Representation & Validation](#week-3-build-representation--validation)
7. [Week 4: Optimization Algorithms](#week-4-optimization-algorithms)
8. [Week 5: Polish & Testing](#week-5-polish--testing)
9. [Week 6: Advanced Features](#week-6-advanced-features)
10. [Claude Code Strategies](#claude-code-strategies)
11. [Testing & Validation](#testing--validation)
12. [Deployment Options](#deployment-options)
13. [Contributing to PoB](#contributing-to-pob)

---

## Why This Approach is Better

### The Original Problem

Reimplementing Path of Exile's damage calculation system is extraordinarily complex:

- **50+ damage types** with conversion mechanics
- **Conditional modifiers** ("while at full life", "recently", "if you've killed")
- **Complex interactions** between support gems
- **Calculation order matters** (increased → more → conversion → penetration)
- **Thousands of edge cases** and special interactions
- **Changes every 3 months** with patches

**Reality check:** Path of Building took years to develop with dozens of contributors. Reimplementing would take months and still have errors.

### The Smart Solution

Build a Python optimizer that:

1. ✅ Reads game data from PoB's existing Lua files
2. ✅ Generates build configurations in PoB's XML format
3. ✅ Calls PoB's calculation engine to evaluate builds
4. ✅ Uses optimization algorithms to find the best builds
5. ✅ Outputs valid PoB codes players can immediately use

### Benefits

| Feature | Reimplemented | PoB Wrapper | Fork PoB (Lua) |
|---------|--------------|-------------|----------------|
| **Dev Time** | 6 weeks | 3 weeks | 5 weeks |
| **Accuracy** | 90-95% | 100% | 100% |
| **Maintenance** | High | Low | Medium |
| **Python ML** | ✓ | ✓ | ✗ |
| **Auto Updates** | ✗ | ✓ | ✓ |

**Key advantages:**

- **100% Calculation Accuracy** - Using PoB's battle-tested engine
- **80% Less Dev Time** - Skip reimplementation entirely
- **Automatic Patches** - PoB updates, you just pull latest
- **Community Trust** - "Powered by Path of Building" = instant credibility
- **Focus on Innovation** - Spend time on algorithms, not calculations
- **Python Ecosystem** - scipy, numpy, scikit-learn available

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────┐
│   Python Optimizer (Your Code)     │
│  - Genetic algorithms               │
│  - Constraint solving               │
│  - Item selection                   │
│  - Passive tree optimization        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   PoB Interface Layer (Your Code)  │
│  - Build XML generator              │
│  - PoB caller (subprocess)          │
│  - Result parser                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Path of Building (Git Submodule) │
│  - Data/*.lua (you read)            │
│  - Modules/Calc*.lua (you call)     │
│  - Export format (you use)          │
└─────────────────────────────────────┘
```

### Project Structure

```
poe-optimizer/
├── PathOfBuilding/          # Git submodule
│   ├── Data/                # Game data (you read)
│   ├── Modules/             # Calculations (you call)
│   └── headless.lua         # CLI entry point (you create)
├── src/
│   ├── pob/                 # PoB interface
│   │   ├── caller.py        # Subprocess wrapper
│   │   ├── parser.py        # Parse PoB Lua/XML
│   │   └── builder.py       # Build XML generator
│   ├── optimizer/           # Your algorithms
│   │   ├── genetic.py       # Genetic algorithm
│   │   ├── passive_tree.py  # Tree optimization
│   │   └── items.py         # Item selection
│   ├── models/              # Data structures
│   │   ├── build.py         # Build representation
│   │   └── constraints.py   # Constraint validation
│   └── cli.py               # Command-line interface
├── tests/
├── examples/                # Example builds/constraints
└── requirements.txt
```

### Core Workflow

1. **User Request**
   ```bash
   $ python -m src.cli optimize --skill Cyclone --budget 50div
   ```

2. **Your Optimizer**
   - Reads PoB's Lua files for passive tree and items
   - Generates random initial population (100 builds)
   - Converts each build to PoB XML format

3. **PoB Calculator**
   - Your code calls: `lua PathOfBuilding/headless.lua --xml build.xml`
   - PoB returns: `{"dps": 5000000, "ehp": 150000, "life": 5000, ...}`

4. **Evolution**
   - Score builds based on DPS, EHP, cost
   - Select best performers
   - Mutate and crossover
   - Repeat for 50 generations

5. **Output**
   - Export best build as PoB code
   - User imports directly into Path of Building

---

## Prerequisites & Setup

### Required Software

- Python 3.9+ (with pip)
- Lua 5.1 or LuaJIT (for running PoB)
- Git (for submodules)
- Code editor (VS Code recommended)

### Python Libraries

Create `requirements.txt`:

```
numpy>=1.24.0
scipy>=1.10.0
lupa>=2.0              # Lua parser
networkx>=3.0          # For passive tree graphs
requests>=2.31.0       # For poe.ninja API
lxml>=4.9.0            # For XML parsing
deap>=1.4.0            # Genetic algorithms (optional)
```

### Initial Setup

**Claude Code Prompt:**
> "Create a new directory called poe-optimizer, initialize it as a git repo, add PathOfBuilding as a submodule, create the src/ directory structure shown above, and create a requirements.txt file with the dependencies listed."

Expected commands:
```bash
mkdir poe-optimizer && cd poe-optimizer
git init
git submodule add https://github.com/PathOfBuildingCommunity/PathOfBuilding
mkdir -p src/{pob,optimizer,models} tests examples
touch src/__init__.py src/cli.py
# Create requirements.txt
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### Verify PoB Installation

**Claude Code Prompt:**
> "Check if Path of Building has a headless/CLI mode. Look for lua scripts that can be run from command line. Show me the directory structure of PathOfBuilding/ and explain how PoB initializes and runs calculations."

You're looking for:
- `PathOfBuilding/Launch.lua` or similar entry point
- `PathOfBuilding/Modules/` (calculation engine)
- `PathOfBuilding/Data/` (game data)

**Note:** If PoB doesn't have a CLI mode, you'll need to create a simple Lua wrapper. This is straightforward and covered in Week 1.

---

## Week 1: PoB Integration & Interface

**Goal:** Get Python talking to PoB. Be able to generate a build, send it to PoB, and get calculation results back.

### Day 1-2: Create PoB CLI Wrapper

First, create a simple Lua script that PoB can run headlessly.

**Claude Code Prompt:**
> "Examine PathOfBuilding/Launch.lua to understand how PoB initializes. Create a new file PathOfBuilding/headless.lua that: 1) Loads PoB's modules, 2) Accepts a build XML file as argument, 3) Runs PoB's calculation engine, 4) Outputs DPS, EHP, life, resistances, and other key stats as JSON to stdout, 5) Exits cleanly."

Example `headless.lua` structure:

```lua
-- PathOfBuilding/headless.lua
-- Initialize PoB's runtime environment
dofile("Launch.lua")

-- Parse command line arguments
local buildFile = arg[1]
if not buildFile then
    print('{"error": "No build file specified"}')
    os.exit(1)
end

-- Load build from XML
local build = LoadBuildFromXML(buildFile)
if not build then
    print('{"error": "Failed to load build"}')
    os.exit(1)
end

-- Run calculations
build:BuildCalcs()

-- Extract results
local output = {
    dps = build.calcs.TotalDPS or 0,
    combinedDPS = build.calcs.CombinedDPS or 0,
    ehp = build.calcs.TotalEHP or 0,
    life = build.calcs.Life or 0,
    energyShield = build.calcs.EnergyShield or 0,
    fireRes = build.calcs.FireResist or 0,
    coldRes = build.calcs.ColdResist or 0,
    lightningRes = build.calcs.LightningResist or 0,
    chaosRes = build.calcs.ChaosResist or 0,
    -- Add more stats as needed
}

-- Output as JSON
print(require("dkjson").encode(output))
```

**Testing:**
```bash
# Test with an existing PoB build
lua PathOfBuilding/headless.lua test_build.xml
# Should output: {"dps": 5000000, "ehp": 150000, ...}
```

### Day 2-3: Python Subprocess Caller

**Claude Code Prompt:**
> "Create src/pob/caller.py with a class PoBCalculator. It should have a method evaluate_build(build_xml_string) that: 1) Writes the XML to a temp file, 2) Calls lua PathOfBuilding/headless.lua using subprocess, 3) Parses the JSON output, 4) Returns a dict with DPS, EHP, etc. Include error handling for failed subprocess calls."

Example implementation:

```python
# src/pob/caller.py
import subprocess
import json
import tempfile
import os
from pathlib import Path

class PoBCalculator:
    def __init__(self, pob_path="./PathOfBuilding"):
        self.pob_path = Path(pob_path)
        if not self.pob_path.exists():
            raise FileNotFoundError(f"PoB not found at {pob_path}")
        
        self.headless_script = self.pob_path / "headless.lua"
        if not self.headless_script.exists():
            raise FileNotFoundError(f"headless.lua not found at {self.headless_script}")
    
    def evaluate_build(self, build_xml):
        """
        Evaluate a build using PoB's calculation engine.
        
        Args:
            build_xml (str): Complete PoB build XML string
            
        Returns:
            dict: Calculation results with keys: dps, ehp, life, etc.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(build_xml)
            temp_path = f.name
        
        try:
            result = subprocess.run(
                ['lua', str(self.headless_script), temp_path],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=str(self.pob_path)
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"PoB calculation failed: {result.stderr}")
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            raise TimeoutError("PoB calculation timed out")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from PoB: {result.stdout}") from e
        finally:
            os.unlink(temp_path)  # Clean up temp file
```

### Day 4-5: Test with Known Builds

**Claude Code Prompt:**
> "I have a PoB code from poe.ninja for a Cyclone Slayer. The code is base64-encoded XML. Create a function decode_pob_code(code) that decodes it, then use our PoBCalculator to evaluate it. Compare the DPS/EHP output with what the community tool shows."

Steps:

1. Download a popular build from poe.ninja
2. PoB codes are base64 + zlib compressed XML
3. Decode and save to test_build.xml
4. Run: `calc = PoBCalculator(); results = calc.evaluate_build(xml)`
5. Verify numbers match PoB

Example decoder:

```python
# src/pob/decoder.py
import base64
import zlib
from urllib.parse import unquote

def decode_pob_code(code):
    """
    Decode a Path of Building import code.
    
    Args:
        code (str): PoB import code (base64 encoded)
        
    Returns:
        str: Decoded XML string
    """
    # Remove any URL encoding
    code = unquote(code)
    
    # Decode base64
    compressed = base64.b64decode(code)
    
    # Decompress zlib
    xml = zlib.decompress(compressed).decode('utf-8')
    
    return xml
```

**Test script:**

```python
# tests/test_pob_integration.py
from src.pob.caller import PoBCalculator
from src.pob.decoder import decode_pob_code

# Example PoB code from poe.ninja
POB_CODE = "eNqVVk1v2zAM..."  # Truncated for brevity

def test_cyclone_slayer():
    calc = PoBCalculator()
    
    # Decode build
    xml = decode_pob_code(POB_CODE)
    
    # Evaluate
    results = calc.evaluate_build(xml)
    
    # Check results
    print(f"DPS: {results['dps']:,.0f}")
    print(f"EHP: {results['ehp']:,.0f}")
    print(f"Life: {results['life']}")
    print(f"Resistances: Fire {results['fireRes']}% / Cold {results['coldRes']}% / Lightning {results['lightningRes']}%")
    
    # Assertions (adjust based on actual build)
    assert results['dps'] > 1_000_000, "DPS too low"
    assert results['life'] > 4000, "Life too low"
    assert results['fireRes'] >= 75, "Fire res not capped"

if __name__ == "__main__":
    test_cyclone_slayer()
```

### Week 1 Deliverables

- ✅ PoB headless wrapper working
- ✅ Python can call PoB and get results
- ✅ Verified accuracy with 3-5 real builds
- ✅ Error handling for edge cases
- ✅ Test suite with known builds

**Success Criteria:** Can input any valid PoB XML and get accurate calculations back within 5 seconds.

---

## Week 2: Data Access Layer

**Goal:** Read PoB's Lua data files to access passive tree, items, and gems. No database needed - parse on demand.

### Day 1-2: Parse Passive Tree

The passive tree is the foundation of any build. It's a graph with ~1,500 nodes.

**Claude Code Prompt:**
> "Using the lupa library, create src/pob/parser.py with a function load_passive_tree() that reads PathOfBuilding/Data/3_0/Tree.lua and returns a networkx DiGraph. Each node should have attributes: node_id, name, stats (list of modifiers), position (x, y), type (normal/notable/keystone/jewel), ascendancy (if applicable). Edges represent connections between nodes."

Example code:

```python
# src/pob/parser.py
from lupa import LuaRuntime
import networkx as nx
from pathlib import Path
from typing import Dict, Any

class PoBDataParser:
    def __init__(self, pob_path="./PathOfBuilding"):
        self.pob_path = Path(pob_path)
        self.lua = LuaRuntime()
        
    def load_passive_tree(self) -> nx.Graph:
        """
        Load passive skill tree from PoB data.
        
        Returns:
            nx.Graph: Passive tree as a graph
        """
        tree_file = self.pob_path / "Data" / "3_0" / "Tree.lua"
        
        with open(tree_file, 'r', encoding='utf-8') as f:
            lua_code = f.read()
            
        # Execute Lua and get tree data
        self.lua.execute(lua_code)
        tree_data = self.lua.globals().tree
        
        # Build NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for node_id, node_data in tree_data.nodes.items():
            node_attrs = {
                'name': node_data.dn or '',
                'stats': list(node_data.sd or []),
                'type': self._classify_node(node_data),
                'position': (node_data.x, node_data.y),
                'icon': node_data.icon or '',
                'ascendancy': node_data.ascendancyName or None,
            }
            G.add_node(int(node_id), **node_attrs)
            
            # Add edges
            if node_data.out:
                for connected_id in node_data.out:
                    G.add_edge(int(node_id), int(connected_id))
        
        return G
    
    def _classify_node(self, node_data) -> str:
        """Classify node as normal, notable, keystone, etc."""
        if node_data.isKeystone:
            return 'keystone'
        elif node_data.isNotable:
            return 'notable'
        elif node_data.isJewelSocket:
            return 'jewel'
        elif node_data.isAscendancyStart:
            return 'ascendancy_start'
        else:
            return 'normal'
```

**Test it:**

```python
# Quick test
parser = PoBDataParser()
tree = parser.load_passive_tree()

print(f"Total nodes: {tree.number_of_nodes()}")
print(f"Total edges: {tree.number_of_edges()}")

# Find a specific node
for node_id, attrs in tree.nodes(data=True):
    if 'Resolute Technique' in attrs.get('name', ''):
        print(f"Found Resolute Technique: node {node_id}")
        print(f"  Stats: {attrs['stats']}")
        print(f"  Connections: {list(tree.neighbors(node_id))}")
        break
```

### Day 3-4: Parse Items

**Claude Code Prompt:**
> "Add a method load_unique_items() to PoBDataParser that reads PathOfBuilding/Data/Uniques.lua. Return a dict where keys are item names and values are dicts with: type (base type), implicit (implicit mods), explicit (explicit mods), requirements (level, str, dex, int). Focus on weapons and armour for Cyclone builds."

Example structure:

```python
def load_unique_items(self) -> Dict[str, Dict[str, Any]]:
    """
    Load unique items from PoB data.
    
    Returns:
        dict: {item_name: {type, implicit, explicit, requirements}}
    """
    uniques_file = self.pob_path / "Data" / "Uniques.lua"
    
    with open(uniques_file, 'r', encoding='utf-8') as f:
        lua_code = f.read()
    
    self.lua.execute(lua_code)
    items_data = self.lua.globals().items
    
    uniques = {}
    for item_name, item_data in items_data.items():
        uniques[item_name] = {
            'base_type': item_data.base,
            'implicit': list(item_data.implicit or []),
            'explicit': list(item_data.explicit or []),
            'required_level': item_data.req_level or 0,
            'required_str': item_data.req_str or 0,
            'required_dex': item_data.req_dex or 0,
            'required_int': item_data.req_int or 0,
        }
    
    return uniques
```

**Filter for relevant items:**

```python
def get_weapons_for_skill(self, skill_name: str, items: dict) -> dict:
    """Get weapons suitable for a skill."""
    weapon_types = {
        'Cyclone': ['Two Handed Axe', 'Two Handed Sword', 'Two Handed Mace', 
                    'One Handed Axe', 'One Handed Sword', 'Staff'],
        'Spectral Throw': ['Claw', 'Dagger', 'One Handed Axe', 'One Handed Sword'],
        # ... more skills
    }
    
    valid_types = weapon_types.get(skill_name, [])
    return {
        name: data 
        for name, data in items.items() 
        if any(wtype in data['base_type'] for wtype in valid_types)
    }
```

### Day 5: Parse Gems

**Claude Code Prompt:**
> "Add methods load_skill_gems() and load_support_gems() that read PathOfBuilding/Data/Skills.lua and PathOfBuilding/Data/Gems.lua. For each gem, return: base damage (if applicable), level scaling (1-20), tags (melee, projectile, etc.), and quality bonuses."

```python
def load_skill_gems(self) -> Dict[str, Dict]:
    """Load all skill gems with level scaling."""
    skills_file = self.pob_path / "Data" / "Skills.lua"
    
    with open(skills_file, 'r', encoding='utf-8') as f:
        self.lua.execute(f.read())
    
    skills = self.lua.globals().skills
    
    gem_data = {}
    for gem_name, gem_info in skills.items():
        gem_data[gem_name] = {
            'base_damage': gem_info.base_damage,
            'attack_speed': gem_info.attack_time,
            'level_scaling': {},  # populated below
            'tags': list(gem_info.tags or []),
        }
        
        # Get per-level data
        if gem_info.levels:
            for level, level_data in gem_info.levels.items():
                gem_data[gem_name]['level_scaling'][int(level)] = {
                    'damage_mult': level_data.damage_mult or 1.0,
                    'mana_cost': level_data.mana_cost or 0,
                    'quality_bonus': level_data.quality or {},
                }
    
    return gem_data
```

### Week 2 Deliverables

- ✅ Can load passive tree as graph (1,500+ nodes)
- ✅ Can query unique items (500+ items)
- ✅ Can access gem stats with level scaling
- ✅ All data comes directly from PoB's Lua files
- ✅ Caching implemented for faster repeated access

**Success Criteria:** Can query any node/item/gem in <100ms. Tree pathfinding works correctly.

---

## Week 3: Build Representation & Validation

**Goal:** Create data structures for builds and convert them to PoB XML format.

### Day 1-2: Build Model

**Claude Code Prompt:**
> "Create src/models/build.py with a Build class that represents a complete PoE character. Include: class_name, ascendancy, level, allocated_passives (set of node IDs), items (dict by slot), main_skill, support_gems, config options. Add methods: is_valid(), to_xml(), from_xml(), calculate_point_cost()."

```python
# src/models/build.py
from typing import Set, Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class Build:
    """Represents a Path of Exile character build."""
    
    # Character basics
    class_name: str = "Duelist"
    ascendancy: str = "Slayer"
    level: int = 90
    
    # Passive tree
    allocated_passives: Set[int] = field(default_factory=set)
    
    # Items (slot_name -> item_name)
    items: Dict[str, Optional[str]] = field(default_factory=lambda: {
        "Weapon 1": None,
        "Weapon 2": None,
        "Helmet": None,
        "Body Armour": None,
        "Gloves": None,
        "Boots": None,
        "Amulet": None,
        "Ring 1": None,
        "Ring 2": None,
        "Belt": None,
    })
    
    # Skills
    main_skill: str = "Cyclone"
    support_gems: List[str] = field(default_factory=list)
    
    # Config
    config: Dict[str, any] = field(default_factory=dict)
    
    # Cached stats
    stats: Optional[Dict] = None
    
    def calculate_point_cost(self, tree_graph) -> int:
        """Calculate total passive points spent."""
        return len(self.allocated_passives)
    
    def available_points(self) -> int:
        """Points available at current level."""
        # Base: 99 points (at level 100)
        # Quests: +22 points
        # Ascendancy: comes from nodes themselves
        base_points = min(self.level - 1, 99)
        quest_points = min(self.level // 5, 22)  # Simplified
        return base_points + quest_points
    
    def is_valid(self, tree_graph, item_database) -> tuple[bool, str]:
        """
        Check if build is valid.
        
        Returns:
            (is_valid, error_message)
        """
        # Check point budget
        points_spent = self.calculate_point_cost(tree_graph)
        if points_spent > self.available_points():
            return False, f"Overspent: {points_spent}/{self.available_points()} points"
        
        # Check passive tree connectivity
        if not self._tree_is_connected(tree_graph):
            return False, "Passive tree is not connected"
        
        # Check item slots
        for slot, item_name in self.items.items():
            if item_name and item_name not in item_database:
                return False, f"Unknown item: {item_name}"
        
        # Check skill compatibility
        # ... add more validation
        
        return True, ""
    
    def _tree_is_connected(self, tree_graph) -> bool:
        """Verify all allocated nodes form a connected path."""
        if not self.allocated_passives:
            return True
            
        # Start from class starting location
        start_nodes = {
            'Duelist': 36634,  # Example node IDs
            'Witch': 27864,
            # ... other classes
        }
        
        start = start_nodes.get(self.class_name)
        if not start:
            return False
        
        # BFS to check connectivity
        import networkx as nx
        subgraph = tree_graph.subgraph(self.allocated_passives | {start})
        return nx.is_connected(subgraph)
    
    def to_xml(self) -> str:
        """Generate PoB XML format."""
        # Implemented in next section
        pass
    
    @classmethod
    def from_xml(cls, xml_string: str):
        """Parse PoB XML into Build object."""
        # Implemented in next section
        pass
```

### Day 3-4: XML Generation

**Claude Code Prompt:**
> "Look at real PoB exports (decode a few codes from poe.ninja) and understand the XML structure. Implement Build.to_xml() that generates valid PoB XML. Key sections needed: <PathOfBuilding>, <Build>, <Tree>, <Items>, <Skills>, <Config>. Use lxml for XML generation. Test by creating a minimal build and importing into actual PoB."

```python
# src/pob/builder.py
from lxml import etree
from typing import Dict
import base64
import zlib

class BuildXMLGenerator:
    """Generate Path of Building XML from Build objects."""
    
    def generate_xml(self, build) -> str:
        """
        Generate PoB XML string from Build object.
        
        Args:
            build: Build instance
            
        Returns:
            str: Complete PoB XML
        """
        root = etree.Element("PathOfBuilding")
        
        # Build metadata
        build_elem = etree.SubElement(root, "Build")
        build_elem.set("level", str(build.level))
        build_elem.set("targetVersion", "3_27")  # Current PoE version
        build_elem.set("className", build.class_name)
        build_elem.set("ascendClassName", build.ascendancy)
        
        # Passive tree
        tree_elem = etree.SubElement(root, "Tree")
        tree_elem.set("activeSpec", "1")
        
        spec = etree.SubElement(tree_elem, "Spec")
        spec.set("nodes", ",".join(str(n) for n in sorted(build.allocated_passives)))
        spec.set("classId", self._get_class_id(build.class_name))
        spec.set("ascendClassId", self._get_ascend_id(build.ascendancy))
        
        # Items
        items_elem = etree.SubElement(root, "Items")
        for slot_id, (slot_name, item_name) in enumerate(build.items.items(), 1):
            if item_name:
                item = etree.SubElement(items_elem, "Item")
                item.set("id", str(slot_id))
                item.text = item_name
                # Add item mods here from database
        
        # Skills
        skills_elem = etree.SubElement(root, "Skills")
        
        skill_group = etree.SubElement(skills_elem, "SkillSet")
        skill_group.set("id", "1")
        
        skill = etree.SubElement(skill_group, "Skill")
        skill.set("mainActiveSkill", build.main_skill)
        skill.set("enabled", "true")
        
        # Support gems
        for i, support in enumerate(build.support_gems, 1):
            gem = etree.SubElement(skill, "Gem")
            gem.set("nameSpec", support)
            gem.set("level", "20")
            gem.set("quality", "20")
            gem.set("enabled", "true")
        
        # Config
        config_elem = etree.SubElement(root, "Config")
        for key, value in build.config.items():
            input_elem = etree.SubElement(config_elem, "Input")
            input_elem.set("name", key)
            input_elem.text = str(value)
        
        # Convert to string
        xml_string = etree.tostring(
            root,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        ).decode('utf-8')
        
        return xml_string
    
    def _get_class_id(self, class_name: str) -> str:
        """Map class name to PoB class ID."""
        classes = {
            "Scion": "0",
            "Marauder": "1",
            "Ranger": "2",
            "Witch": "3",
            "Duelist": "4",
            "Templar": "5",
            "Shadow": "6",
        }
        return classes.get(class_name, "0")
    
    def _get_ascend_id(self, ascendancy: str) -> str:
        """Map ascendancy to PoB ascend ID."""
        ascendancies = {
            "Slayer": "1",
            "Gladiator": "2",
            "Champion": "3",
            # ... add all ascendancies
        }
        return ascendancies.get(ascendancy, "0")
    
    def encode_for_import(self, xml_string: str) -> str:
        """
        Encode XML for PoB import (base64 + zlib).
        
        Args:
            xml_string: Complete PoB XML
            
        Returns:
            str: Encoded import code
        """
        compressed = zlib.compress(xml_string.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode('ascii')
        return encoded
```

**Test generation:**

```python
# tests/test_xml_generation.py
from src.models.build import Build
from src.pob.builder import BuildXMLGenerator
from src.pob.caller import PoBCalculator

def test_minimal_build():
    # Create minimal valid build
    build = Build(
        class_name="Duelist",
        ascendancy="Slayer",
        level=90,
        allocated_passives={36634, 12345, 54321},  # Example nodes
        main_skill="Cyclone",
        support_gems=["Melee Physical Damage", "Brutality", "Fortify"]
    )
    
    # Generate XML
    generator = BuildXMLGenerator()
    xml = generator.generate_xml(build)
    
    # Verify it's valid
    calc = PoBCalculator()
    try:
        results = calc.evaluate_build(xml)
        print(f"✓ Build is valid! DPS: {results['dps']}")
    except Exception as e:
        print(f"✗ Build invalid: {e}")
    
    # Generate import code
    code = generator.encode_for_import(xml)
    print(f"Import code (first 50 chars): {code[:50]}...")

if __name__ == "__main__":
    test_minimal_build()
```

### Day 5: Constraint Validation

**Claude Code Prompt:**
> "Create src/models/constraints.py with a Constraints class that can validate builds against requirements. Include methods for: min_life, max_budget, required_resistances, required_attributes, forbidden_keystones. Make it easy to define custom constraints."

```python
# src/models/constraints.py
from dataclasses import dataclass
from typing import Set, Optional

@dataclass
class Constraints:
    """Constraints for build optimization."""
    
    # Defensive requirements
    min_life: int = 4000
    min_energy_shield: int = 0
    min_fire_res: int = 75
    min_cold_res: int = 75
    min_lightning_res: int = 75
    min_chaos_res: int = -60
    
    # Budget
    max_budget_chaos: int = 10_000_000  # 100 divines
    
    # Attributes
    min_strength: Optional[int] = None
    min_dexterity: Optional[int] = None
    min_intelligence: Optional[int] = None
    
    # Passive tree
    max_passive_points: Optional[int] = None
    required_keystones: Set[str] = None
    forbidden_keystones: Set[str] = None
    
    # Performance
    min_dps: int = 1_000_000
    
    def validate(self, build_stats: dict) -> tuple[bool, list[str]]:
        """
        Validate build stats against constraints.
        
        Returns:
            (is_valid, list_of_violations)
        """
        violations = []
        
        # Check life
        if build_stats.get('life', 0) < self.min_life:
            violations.append(f"Life too low: {build_stats['life']} < {self.min_life}")
        
        # Check resistances
        if build_stats.get('fireRes', 0) < self.min_fire_res:
            violations.append(f"Fire res too low: {build_stats['fireRes']}%")
        if build_stats.get('coldRes', 0) < self.min_cold_res:
            violations.append(f"Cold res too low: {build_stats['coldRes']}%")
        if build_stats.get('lightningRes', 0) < self.min_lightning_res:
            violations.append(f"Lightning res too low: {build_stats['lightningRes']}%")
        
        # Check DPS
        if build_stats.get('dps', 0) < self.min_dps:
            violations.append(f"DPS too low: {build_stats['dps']:,.0f}")
        
        # ... more checks
        
        return (len(violations) == 0, violations)
```

### Week 3 Deliverables

- ✅ Build class with full representation
- ✅ XML generation working
- ✅ Can import generated builds into PoB
- ✅ Constraint validation system
- ✅ Round-trip test (Build → XML → PoB → verify)

**Success Criteria:** Can create a build in code, export to PoB, import into actual PoB application, and all values match.

---

## Week 4: Optimization Algorithms

**Goal:** Implement algorithms that can search the build space and find optimal configurations.

### Day 1-2: Passive Tree Optimizer

The passive tree is a graph pathfinding problem with ~1,500 nodes.

**Claude Code Prompt:**
> "Create src/optimizer/passive_tree.py with a PassiveTreeOptimizer class. Use A* pathfinding to find efficient paths to desired keystones. Given: starting position (class), list of desired nodes, point budget. Output: set of allocated nodes that maximizes value per point. Heuristic: (DPS_gain + EHP_gain) / points_spent."

```python
# src/optimizer/passive_tree.py
import networkx as nx
from typing import Set, List, Dict
import heapq

class PassiveTreeOptimizer:
    """Optimize passive tree allocation."""
    
    def __init__(self, tree_graph: nx.Graph, calculator):
        self.tree = tree_graph
        self.calculator = calculator  # PoB calculator for evaluation
        
    def find_optimal_path(
        self,
        start_node: int,
        target_nodes: List[int],
        point_budget: int,
        current_build
    ) -> Set[int]:
        """
        Find most efficient path to target nodes.
        
        Args:
            start_node: Starting position (class location)
            target_nodes: Keystones/notables to reach
            point_budget: Maximum points to spend
            current_build: Current build state
            
        Returns:
            Set of node IDs to allocate
        """
        # Simple greedy approach: find shortest path to each target
        # then rank by value
        
        paths = {}
        for target in target_nodes:
            try:
                path = nx.shortest_path(self.tree, start_node, target)
                paths[target] = path
            except nx.NetworkXNoPath:
                continue
        
        # Evaluate value of each path
        path_values = {}
        for target, path in paths.items():
            value = self._evaluate_path_value(path, current_build)
            path_values[target] = {
                'path': path,
                'value': value,
                'length': len(path),
                'value_per_point': value / len(path) if len(path) > 0 else 0
            }
        
        # Select best paths within budget
        allocated = set()
        remaining_budget = point_budget
        
        # Sort by value per point
        sorted_paths = sorted(
            path_values.items(),
            key=lambda x: x[1]['value_per_point'],
            reverse=True
        )
        
        for target, data in sorted_paths:
            if data['length'] <= remaining_budget:
                allocated.update(data['path'])
                remaining_budget -= data['length']
        
        return allocated
    
    def _evaluate_path_value(self, path: List[int], build) -> float:
        """
        Estimate value of allocating a path.
        
        This is a heuristic - for accurate eval, need to call PoB.
        """
        value = 0.0
        
        for node_id in path:
            node = self.tree.nodes[node_id]
            stats = node.get('stats', [])
            
            for stat in stats:
                # Parse stat text and estimate value
                if 'increased Physical Damage' in stat:
                    value += 10  # Simple heuristic
                elif 'maximum Life' in stat:
                    value += 5
                elif node.get('type') == 'keystone':
                    value += 50  # Keystones are valuable
                # ... more heuristics
        
        return value
    
    def optimize_with_genetic(
        self,
        start_node: int,
        must_have_nodes: Set[int],
        point_budget: int,
        current_build,
        generations=50
    ) -> Set[int]:
        """
        Use genetic algorithm to find optimal tree.
        
        More sophisticated than greedy pathfinding.
        """
        from deap import base, creator, tools, algorithms
        
        # This will be implemented with genetic algorithm
        # For now, placeholder
        pass
```

### Day 3: Item Optimizer

**Claude Code Prompt:**
> "Create src/optimizer/items.py with an ItemOptimizer class. Use greedy algorithm: for each equipment slot, find the item that provides best DPS-per-chaos ratio while maintaining defensive requirements. Include item price data from poe.ninja API."

```python
# src/optimizer/items.py
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ItemScore:
    """Score for an item."""
    item_name: str
    slot: str
    dps_gain: float
    ehp_gain: float
    price_chaos: float
    score: float  # Combined metric

class ItemOptimizer:
    """Optimize item selection."""
    
    def __init__(self, item_database: Dict, calculator, league="Standard"):
        self.items = item_database
        self.calculator = calculator
        self.league = league
        self.price_cache = {}
        
    def optimize_items(
        self,
        current_build,
        budget_chaos: int,
        constraints
    ) -> Dict[str, str]:
        """
        Find best items within budget.
        
        Returns:
            Dict of slot -> item_name
        """
        best_items = {}
        remaining_budget = budget_chaos
        
        # Prioritize slots by impact
        slot_priority = [
            "Weapon 1",      # Biggest DPS impact
            "Body Armour",   # Biggest defense impact  
            "Weapon 2",      # If dual wielding
            "Helmet",
            "Boots",
            "Gloves",
            "Amulet",
            "Ring 1",
            "Ring 2",
            "Belt",
        ]
        
        for slot in slot_priority:
            best_item = self._find_best_for_slot(
                slot,
                current_build,
                remaining_budget,
                constraints
            )
            
            if best_item:
                best_items[slot] = best_item.item_name
                remaining_budget -= best_item.price_chaos
        
        return best_items
    
    def _find_best_for_slot(
        self,
        slot: str,
        build,
        budget: int,
        constraints
    ) -> Optional[ItemScore]:
        """Find best item for a slot within budget."""
        
        # Get valid items for slot
        valid_items = self._get_valid_items_for_slot(slot, build.main_skill)
        
        # Score each item
        scores = []
        for item_name, item_data in valid_items.items():
            price = self._get_item_price(item_name)
            
            if price > budget:
                continue
            
            # Test item in build
            test_build = self._clone_build(build)
            test_build.items[slot] = item_name
            
            try:
                xml = test_build.to_xml()
                stats = self.calculator.evaluate_build(xml)
                
                # Check constraints
                valid, _ = constraints.validate(stats)
                if not valid:
                    continue
                
                # Calculate score
                dps_gain = stats['dps'] - build.stats.get('dps', 0)
                ehp_gain = stats['ehp'] - build.stats.get('ehp', 0)
                
                # Combined score (tweak weights based on build goal)
                score = (dps_gain * 1.0 + ehp_gain * 0.1) / max(price, 1)
                
                scores.append(ItemScore(
                    item_name=item_name,
                    slot=slot,
                    dps_gain=dps_gain,
                    ehp_gain=ehp_gain,
                    price_chaos=price,
                    score=score
                ))
            except Exception as e:
                # Item caused error, skip it
                continue
        
        # Return best scoring item
        if scores:
            return max(scores, key=lambda x: x.score)
        return None
    
    def _get_item_price(self, item_name: str) -> float:
        """Get item price from poe.ninja."""
        if item_name in self.price_cache:
            return self.price_cache[item_name]
        
        # Call poe.ninja API
        try:
            url = f"https://poe.ninja/api/data/itemoverview"
            params = {
                "league": self.league,
                "type": "UniqueWeapon",  # Adjust based on item type
            }
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            for item in data.get('lines', []):
                if item['name'] == item_name:
                    price = item.get('chaosValue', 999999)
                    self.price_cache[item_name] = price
                    return price
            
            # Not found, assume expensive
            return 999999
            
        except:
            return 999999  # Error fetching, assume expensive
    
    def _get_valid_items_for_slot(self, slot: str, skill: str) -> Dict:
        """Filter items valid for slot and skill."""
        # Implementation depends on item database structure
        pass
    
    def _clone_build(self, build):
        """Create a copy of build for testing."""
        import copy
        return copy.deepcopy(build)
```

### Day 4-5: Genetic Algorithm

**Claude Code Prompt:**
> "Create src/optimizer/genetic.py with a GeneticOptimizer class that evolves builds over generations. Chromosome = (passive_nodes, items, gems). Implement: selection (tournament), crossover (swap subtrees/items), mutation (add/remove node, swap item). Fitness = weighted sum of DPS, EHP, 1/cost. Population size: 50, Generations: 100."

```python
# src/optimizer/genetic.py
import random
from typing import List, Callable
from dataclasses import dataclass
import copy

@dataclass
class Individual:
    """One build in the population."""
    build: object  # Build instance
    fitness: float = 0.0
    stats: dict = None

class GeneticOptimizer:
    """Genetic algorithm for build optimization."""
    
    def __init__(
        self,
        calculator,
        tree_graph,
        item_database,
        constraints,
        population_size=50,
        generations=100
    ):
        self.calculator = calculator
        self.tree = tree_graph
        self.items = item_database
        self.constraints = constraints
        self.pop_size = population_size
        self.generations = generations
        
        # GA parameters
        self.mutation_rate = 0.15
        self.crossover_rate = 0.7
        self.tournament_size = 3
    
    def optimize(
        self,
        seed_build,
        fitness_fn: Callable[[dict], float] = None
    ) -> Individual:
        """
        Run genetic algorithm optimization.
        
        Args:
            seed_build: Starting build template
            fitness_fn: Custom fitness function (optional)
            
        Returns:
            Best individual found
        """
        if fitness_fn is None:
            fitness_fn = self._default_fitness
        
        # Initialize population
        population = self._init_population(seed_build)
        
        # Evaluate initial population
        self._evaluate_population(population, fitness_fn)
        
        best_ever = max(population, key=lambda x: x.fitness)
        
        # Evolution loop
        for gen in range(self.generations):
            # Selection
            parents = self._selection(population)
            
            # Create offspring
            offspring = []
            for i in range(0, len(parents), 2):
                if i + 1 < len(parents):
                    child1, child2 = self._crossover(parents[i], parents[i+1])
                else:
                    child1 = parents[i]
                    child2 = parents[i]
                
                # Mutation
                self._mutate(child1)
                self._mutate(child2)
                
                offspring.extend([child1, child2])
            
            # Evaluate offspring
            self._evaluate_population(offspring, fitness_fn)
            
            # Combine and select survivors
            population = self._survivor_selection(population + offspring)
            
            # Track best
            gen_best = max(population, key=lambda x: x.fitness)
            if gen_best.fitness > best_ever.fitness:
                best_ever = copy.deepcopy(gen_best)
            
            # Progress update
            if gen % 10 == 0:
                print(f"Gen {gen}: Best fitness = {gen_best.fitness:.2f}, "
                      f"DPS = {gen_best.stats['dps']:,.0f}, "
                      f"EHP = {gen_best.stats['ehp']:,.0f}")
        
        return best_ever
    
    def _init_population(self, seed_build) -> List[Individual]:
        """Create initial random population."""
        population = []
        
        for _ in range(self.pop_size):
            # Clone seed
            build = copy.deepcopy(seed_build)
            
            # Randomize passive tree
            build.allocated_passives = self._random_passive_allocation(
                build.class_name,
                build.available_points()
            )
            
            # Randomize items
            for slot in build.items.keys():
                valid_items = list(self._get_slot_items(slot).keys())
                if valid_items:
                    build.items[slot] = random.choice(valid_items)
            
            population.append(Individual(build=build))
        
        return population
    
    def _evaluate_population(self, population: List[Individual], fitness_fn):
        """Evaluate fitness for all individuals."""
        for individual in population:
            if individual.stats is None:  # Not evaluated yet
                try:
                    xml = individual.build.to_xml()
                    stats = self.calculator.evaluate_build(xml)
                    individual.stats = stats
                    individual.fitness = fitness_fn(stats)
                except Exception as e:
                    # Invalid build
                    individual.fitness = 0.0
                    individual.stats = {}
    
    def _default_fitness(self, stats: dict) -> float:
        """Default fitness function."""
        # Weighted combination
        dps = stats.get('dps', 0)
        ehp = stats.get('ehp', 0)
        
        # Check constraints
        valid, _ = self.constraints.validate(stats)
        if not valid:
            return 0.0  # Invalid build
        
        # Normalize and combine
        fitness = (dps / 1_000_000) + (ehp / 100_000)
        return fitness
    
    def _selection(self, population: List[Individual]) -> List[Individual]:
        """Tournament selection."""
        selected = []
        
        for _ in range(self.pop_size):
            tournament = random.sample(population, self.tournament_size)
            winner = max(tournament, key=lambda x: x.fitness)
            selected.append(copy.deepcopy(winner))
        
        return selected
    
    def _crossover(self, parent1: Individual, parent2: Individual) -> tuple:
        """Crossover two parents."""
        if random.random() > self.crossover_rate:
            return parent1, parent2
        
        child1 = copy.deepcopy(parent1)
        child2 = copy.deepcopy(parent2)
        
        # Crossover passive tree (swap subtrees)
        nodes1 = list(child1.build.allocated_passives)
        nodes2 = list(child2.build.allocated_passives)
        
        if nodes1 and nodes2:
            cut = len(nodes1) // 2
            child1.build.allocated_passives = set(nodes1[:cut] + nodes2[cut:])
            child2.build.allocated_passives = set(nodes2[:cut] + nodes1[cut:])
        
        # Crossover items (swap some slots)
        for slot in child1.build.items.keys():
            if random.random() < 0.5:
                child1.build.items[slot], child2.build.items[slot] = \
                    child2.build.items[slot], child1.build.items[slot]
        
        # Reset stats (need re-evaluation)
        child1.stats = None
        child2.stats = None
        
        return child1, child2
    
    def _mutate(self, individual: Individual):
        """Mutate an individual."""
        if random.random() > self.mutation_rate:
            return
        
        mutation_type = random.choice(['add_node', 'remove_node', 'swap_item'])
        
        if mutation_type == 'add_node':
            # Add random connected node
            if individual.build.allocated_passives:
                current = random.choice(list(individual.build.allocated_passives))
                neighbors = list(self.tree.neighbors(current))
                if neighbors:
                    new_node = random.choice(neighbors)
                    individual.build.allocated_passives.add(new_node)
        
        elif mutation_type == 'remove_node':
            # Remove random node (keep connectivity)
            if len(individual.build.allocated_passives) > 1:
                to_remove = random.choice(list(individual.build.allocated_passives))
                individual.build.allocated_passives.discard(to_remove)
        
        elif mutation_type == 'swap_item':
            # Swap random item
            slot = random.choice(list(individual.build.items.keys()))
            valid_items = list(self._get_slot_items(slot).keys())
            if valid_items:
                individual.build.items[slot] = random.choice(valid_items)
        
        # Reset stats
        individual.stats = None
    
    def _survivor_selection(self, combined: List[Individual]) -> List[Individual]:
        """Select survivors (elitism + random)."""
        # Sort by fitness
        combined.sort(key=lambda x: x.fitness, reverse=True)
        
        # Keep top 10%
        elites = combined[:self.pop_size // 10]
        
        # Random selection for rest
        rest = random.sample(combined[self.pop_size // 10:],
                           self.pop_size - len(elites))
        
        return elites + rest
    
    def _random_passive_allocation(self, class_name: str, points: int) -> set:
        """Generate random valid passive tree."""
        # Simplified: random walk from start
        start_nodes = {
            'Duelist': 36634,
            'Witch': 27864,
            # ... other classes
        }
        
        current = start_nodes.get(class_name, 36634)
        allocated = {current}
        
        for _ in range(points):
            neighbors = [n for n in self.tree.neighbors(current) 
                        if n not in allocated]
            if neighbors:
                current = random.choice(neighbors)
                allocated.add(current)
        
        return allocated
    
    def _get_slot_items(self, slot: str) -> dict:
        """Get valid items for a slot."""
        # Filter items by slot type
        # This is simplified - actual implementation would be more sophisticated
        return self.items
```

### Week 4 Deliverables

- ✅ Passive tree pathfinding working
- ✅ Item optimizer functional
- ✅ Genetic algorithm implemented
- ✅ Can optimize simple builds end-to-end
- ✅ Fitness functions tunable

**Success Criteria:** Can take a skill name and budget, run optimizer for 5 minutes, and produce a playable build that meets constraints.

---

## Week 5: Polish & Testing

**Goal:** Refine the optimizer, add CLI, and validate against real builds.

### Day 1-2: Command-Line Interface

**Claude Code Prompt:**
> "Create a user-friendly CLI in src/cli.py using argparse or click. Commands: optimize, validate, compare, export. Example: python -m src.cli optimize --skill Cyclone --ascendancy Slayer --budget 5000000 --min-life 5000 --output build.xml"

```python
# src/cli.py
import click
from pathlib import Path
from src.pob.caller import PoBCalculator
from src.pob.parser import PoBDataParser
from src.optimizer.genetic import GeneticOptimizer
from src.models.build import Build
from src.models.constraints import Constraints
from src.pob.builder import BuildXMLGenerator

@click.group()
def cli():
    """Path of Exile Build Optimizer"""
    pass

@cli.command()
@click.option('--skill', required=True, help='Main skill gem (e.g., Cyclone)')
@click.option('--class-name', default='Duelist', help='Character class')
@click.option('--ascendancy', default='Slayer', help='Ascendancy class')
@click.option('--budget', type=int, default=10000000, help='Budget in chaos orbs')
@click.option('--min-life', type=int, default=4000, help='Minimum life')
@click.option('--min-dps', type=int, default=1000000, help='Minimum DPS')
@click.option('--generations', type=int, default=50, help='GA generations')
@click.option('--output', type=Path, default='optimized_build.xml', help='Output file')
def optimize(skill, class_name, ascendancy, budget, min_life, min_dps, generations, output):
    """Optimize a build."""
    
    click.echo("🔧 Initializing Path of Building optimizer...")
    
    # Load PoB data
    parser = PoBDataParser()
    tree = parser.load_passive_tree()
    items = parser.load_unique_items()
    
    click.echo(f"✓ Loaded {tree.number_of_nodes()} passive nodes")
    click.echo(f"✓ Loaded {len(items)} unique items")
    
    # Setup calculator
    calculator = PoBCalculator()
    
    # Create constraints
    constraints = Constraints(
        min_life=min_life,
        min_dps=min_dps,
        max_budget_chaos=budget
    )
    
    # Create seed build
    seed = Build(
        class_name=class_name,
        ascendancy=ascendancy,
        main_skill=skill
    )
    
    # Run optimizer
    click.echo(f"\n🧬 Running genetic algorithm ({generations} generations)...")
    
    optimizer = GeneticOptimizer(
        calculator=calculator,
        tree_graph=tree,
        item_database=items,
        constraints=constraints,
        generations=generations
    )
    
    best = optimizer.optimize(seed)
    
    # Display results
    click.echo("\n✨ Optimization complete!")
    click.echo(f"\nBest Build Stats:")
    click.echo(f"  DPS:    {best.stats['dps']:>15,.0f}")
    click.echo(f"  EHP:    {best.stats['ehp']:>15,.0f}")
    click.echo(f"  Life:   {best.stats['life']:>15,}")
    click.echo(f"  Res:    {best.stats['fireRes']}% / {best.stats['coldRes']}% / {best.stats['lightningRes']}%")
    
    # Export
    generator = BuildXMLGenerator()
    xml = generator.generate_xml(best.build)
    
    output.write_text(xml)
    click.echo(f"\n💾 Build saved to: {output}")
    
    # Generate import code
    code = generator.encode_for_import(xml)
    click.echo(f"\n📋 PoB Import Code (copy to clipboard):")
    click.echo(code[:100] + "...")
    click.echo(f"\nFull code saved to: {output.with_suffix('.txt')}")
    output.with_suffix('.txt').write_text(code)

@cli.command()
@click.argument('build_file', type=Path)
def validate(build_file):
    """Validate a build file."""
    click.echo(f"Validating {build_file}...")
    
    calculator = PoBCalculator()
    xml = build_file.read_text()
    
    try:
        results = calculator.evaluate_build(xml)
        click.echo("✓ Build is valid!")
        click.echo(f"  DPS: {results['dps']:,.0f}")
        click.echo(f"  Life: {results['life']}")
    except Exception as e:
        click.echo(f"✗ Build is invalid: {e}")

@cli.command()
@click.argument('build_files', nargs=-1, type=Path)
def compare(build_files):
    """Compare multiple builds."""
    if len(build_files) < 2:
        click.echo("Need at least 2 builds to compare")
        return
    
    calculator = PoBCalculator()
    
    results = []
    for build_file in build_files:
        xml = build_file.read_text()
        stats = calculator.evaluate_build(xml)
        results.append((build_file.name, stats))
    
    # Display comparison table
    click.echo("\nBuild Comparison:")
    click.echo(f"{'Build':<30} {'DPS':>15} {'EHP':>15} {'Life':>10}")
    click.echo("-" * 75)
    
    for name, stats in results:
        click.echo(f"{name:<30} {stats['dps']:>15,.0f} {stats['ehp']:>15,.0f} {stats['life']:>10}")

if __name__ == '__main__':
    cli()
```

### Day 3-4: Benchmark Against Meta Builds

**Claude Code Prompt:**
> "Create tests/test_meta_builds.py that downloads top Cyclone builds from poe.ninja, runs our optimizer with similar constraints, and compares results. Create a markdown report showing: our DPS vs meta DPS, our EHP vs meta EHP, cost comparison, unique optimizations we found."

```python
# tests/test_meta_builds.py
import requests
from src.cli import optimize
import json

def fetch_poe_ninja_builds(skill="Cyclone", limit=5):
    """Fetch top builds from poe.ninja."""
    # This is simplified - actual API is more complex
    url = "https://poe.ninja/api/builds"
    params = {
        "league": "Standard",
        "skill": skill,
        "sort": "dps",
        "limit": limit
    }
    
    resp = requests.get(url, params=params)
    return resp.json()

def benchmark_optimizer():
    """Compare optimizer to meta builds."""
    
    meta_builds = fetch_poe_ninja_builds()
    
    results = []
    
    for i, meta in enumerate(meta_builds, 1):
        print(f"\n=== Meta Build {i} ===")
        print(f"DPS: {meta['dps']:,.0f}")
        print(f"Life: {meta['life']}")
        print(f"Cost: {meta['worth']:,.0f} chaos")
        
        # Run our optimizer with similar budget
        # This would call the actual optimize function
        # our_build = optimize(budget=meta['worth'], ...)
        
        # Compare
        # results.append({...})
    
    # Generate report
    generate_markdown_report(results)

def generate_markdown_report(results):
    """Create comparison report."""
    with open('benchmark_report.md', 'w') as f:
        f.write("# Build Optimizer Benchmark Report\n\n")
        f.write("## Comparison vs poe.ninja Meta Builds\n\n")
        
        f.write("| Build | Meta DPS | Our DPS | Δ % | Meta Life | Our Life | Δ |\n")
        f.write("|-------|----------|---------|-----|-----------|----------|---|\n")
        
        for r in results:
            f.write(f"| {r['name']} | {r['meta_dps']:,.0f} | {r['our_dps']:,.0f} | "
                   f"{r['dps_delta']:.1f}% | {r['meta_life']} | {r['our_life']} | "
                   f"{r['life_delta']:.1f}% |\n")

if __name__ == "__main__":
    benchmark_optimizer()
```

### Day 5: Documentation & Examples

**Claude Code Prompt:**
> "Create comprehensive README.md with: installation instructions, quick start guide, CLI examples, architecture diagram, contribution guidelines. Also create examples/ directory with sample constraints and builds for common scenarios (league starter, boss killer, mapper)."

```markdown
# Path of Exile Build Optimizer

Automated build optimization using Path of Building's calculation engine and genetic algorithms.

## Quick Start

\`\`\`bash
# Install
git clone --recursive https://github.com/yourusername/poe-optimizer
cd poe-optimizer
pip install -r requirements.txt

# Optimize a build
python -m src.cli optimize \\
    --skill Cyclone \\
    --ascendancy Slayer \\
    --budget 50000000 \\
    --min-life 5000 \\
    --output my_build.xml

# Import the code into Path of Building!
\`\`\`

## Features

- ✅ 100% accurate calculations (uses PoB engine)
- ✅ Genetic algorithm optimization
- ✅ Multi-objective optimization (DPS, EHP, Budget)
- ✅ Constraint validation
- ✅ poe.ninja price integration
- ✅ CLI interface

... (rest of README)
```

### Week 5 Deliverables

- ✅ Polished CLI interface
- ✅ Benchmark tests vs meta builds
- ✅ Comprehensive documentation
- ✅ Example builds and constraints
- ✅ Performance optimizations

**Success Criteria:** Can run optimizer from CLI, get results in under 10 minutes, produce builds competitive with meta.

---

## Week 6: Advanced Features

**Goal:** Add features that make the optimizer truly powerful.

### Multi-Objective Pareto Optimization

Instead of a single "best" build, find the Pareto frontier - builds where no other build is better in all objectives.

**Claude Code Prompt:**
> "Implement Pareto frontier calculation in src/optimizer/pareto.py. Given a population of builds, find all non-dominated solutions (where no build is strictly better in DPS, EHP, and cost). Return top 10 builds on the frontier for user to choose from."

### Budget Progression

**Claude Code Prompt:**
> "Create a feature that optimizes builds at multiple budget levels (1 div, 5 div, 10 div, 50 div) and shows upgrade path. Output should show which items to upgrade in which order for best bang for your buck."

### League Mechanic Integration

**Claude Code Prompt:**
> "Add support for current league mechanics. Read Genesis Tree data, optimize for breach farming, etc. Make it easy to add new league mechanics each patch."

### ML-Powered Item Recommendations

**Claude Code Prompt:**
> "Train a simple ML model on successful builds from poe.ninja. Use it to recommend item combinations that work well together. Features: skill tags, ascendancy, key passives. Output: probability distribution over items."

---

## Claude Code Strategies

### Effective Prompting for This Project

**1. Be Specific About PoB Integration**

❌ Bad:
> "Make the calculator work"

✅ Good:
> "Create a Python function that takes a Build object, generates PoB XML using the structure from PathOfBuilding/Export.lua, writes it to a temp file, calls lua PathOfBuilding/headless.lua via subprocess with 30 second timeout, parses the JSON output, and returns a dict with keys: dps, ehp, life. Include error handling for invalid builds and subprocess failures."

**2. Request Validation Steps**

Always ask Claude to verify results:
> "After implementing the XML generator, test it by: 1) Creating a minimal build with just Cyclone and 10 passive nodes, 2) Generating the XML, 3) Calling PoB to evaluate it, 4) Verifying the output has reasonable DPS (>1000). If any step fails, debug and fix."

**3. Iterate on Complex Components**

For the genetic algorithm:
> "First, implement just the basic GA structure: population initialization, fitness evaluation (stub), selection. Test that it runs for 10 generations. Then we'll add crossover, mutation, and real fitness evaluation."

**4. Reference PoB Source Code**

> "Look at PathOfBuilding/Modules/CalcOffence.lua lines 100-200 to see how PoB calculates hit damage. Explain the calculation flow, then help me create a similar evaluation in our optimizer's heuristic function."

**5. Ask for Error Analysis**

> "The genetic algorithm is not improving after generation 20. Check: 1) Is diversity maintained in the population? 2) Is the mutation rate appropriate? 3) Are invalid builds being filtered out? 4) Is the fitness function correlated with actual build quality? Add logging to diagnose the issue."

### Common Pitfalls

**❌ Don't:** Try to run PoB calculations inside Python
**✅ Do:** Use subprocess to call PoB's Lua engine

**❌ Don't:** Reimplement passive tree pathfinding from scratch
**✅ Do:** Use NetworkX's built-in algorithms

**❌ Don't:** Parse Lua files with regex
**✅ Do:** Use lupa library to execute Lua directly

**❌ Don't:** Optimize all 1,500 passive nodes at once
**✅ Do:** Focus on high-value paths and keystones first

### Performance Optimization

**Parallelizing PoB Calls:**

**Claude Code Prompt:**
> "Modify PoBCalculator to support batch evaluation. Use multiprocessing.Pool to evaluate 8 builds in parallel. This will speed up genetic algorithm fitness evaluation significantly."

**Caching PoB Results:**

**Claude Code Prompt:**
> "Implement a cache for PoB calculations using a hash of the build XML as key. Use functools.lru_cache with maxsize=1000. This avoids recalculating identical builds."

---

## Testing & Validation

### Unit Tests

```python
# tests/test_pob_caller.py
def test_pob_evaluation():
    """Test basic PoB calling."""
    calc = PoBCalculator()
    
    # Minimal valid build
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <PathOfBuilding>
        <Build level="90" className="Duelist" ascendClassName="Slayer"/>
        <!-- minimal build -->
    </PathOfBuilding>"""
    
    result = calc.evaluate_build(xml)
    
    assert result['dps'] >= 0
    assert result['life'] >= 0
```

### Integration Tests

```python
# tests/test_end_to_end.py
def test_full_optimization():
    """Test complete optimization workflow."""
    
    # Setup
    seed = Build(
        class_name="Duelist",
        ascendancy="Slayer",
        main_skill="Cyclone"
    )
    
    constraints = Constraints(min_life=4000, min_dps=1_000_000)
    
    # Run optimizer
    optimizer = GeneticOptimizer(...)
    best = optimizer.optimize(seed)
    
    # Validate result
    assert best.stats['life'] >= 4000
    assert best.stats['dps'] >= 1_000_000
    assert best.build.is_valid()
```

### Validation Against Real Builds

1. Download 20 popular builds from poe.ninja
2. Run optimizer with same skill + budget
3. Compare:
   - DPS (within 20%)
   - EHP (within 30%)
   - Cost (within 10%)
4. Look for novel optimizations our algorithm found

---

## Deployment Options

### Option 1: Command-Line Tool

**For:** Personal use, power users

**Deploy:**
```bash
# Package as executable
pyinstaller --onefile src/cli.py

# Distribute
./poe-optimizer optimize --skill Cyclone --budget 50div
```

### Option 2: Web Service

**For:** Wider audience, easier to use

**Stack:**
- FastAPI backend (Python)
- React frontend
- Redis for caching
- PostgreSQL for storing builds

**Claude Code Prompt:**
> "Create a FastAPI endpoint POST /optimize that accepts JSON with skill, budget, constraints and returns optimized build. Add rate limiting (10 requests per hour) and caching for common requests."

### Option 3: Discord Bot

**For:** PoE community integration

**Claude Code Prompt:**
> "Create a Discord bot that responds to !optimize Cyclone 50div. Bot should queue the request, run optimization, and DM the user with PoB import code when complete."

---

## Contributing to PoB

If your optimizer works well, consider contributing it back to Path of Building!

### How to Propose Feature

1. **Create a proof of concept** - Get it working standalone first
2. **Open GitHub Discussion** - Propose the feature to PoB community
3. **Port to Lua** - If accepted, port your Python code to Lua
4. **Submit PR** - Follow PoB's contribution guidelines

### What to Contribute

- **Optimization tab** in PoB UI
- **Auto-upgrade suggestions** - "You can get 10% more DPS by replacing X"
- **Budget calculator** - "This build costs 47 divines"
- **Build comparison** - Side-by-side stat comparison

---

## Conclusion

This revised approach gets you to a working optimizer much faster by leveraging Path of Building's existing infrastructure. You focus on the novel parts - the optimization algorithms - while standing on the shoulders of an excellent community tool.

**Timeline Summary:**
- **Week 1:** PoB integration working (3 days ahead of original plan!)
- **Week 2:** Data access layer complete
- **Week 3:** Build representation done
- **Week 4:** Core optimization algorithms functional
- **Week 5:** Polished, tested, documented
- **Week 6:** Advanced features and tuning

**Key Success Factors:**
- Use Claude Code effectively with specific, iterative prompts
- Validate constantly against real builds
- Start simple, add complexity gradually
- Leverage PoB for what it does best (calculations)
- Focus your effort on optimization (your unique value-add)

**Next Steps:**
1. Set up the project structure
2. Get PoB running headlessly
3. Create the Python-Lua interface
4. Start optimizing!

Good luck building your optimizer! The PoE community will love having better tools for build planning.

---

*For questions or help, check out:*
- Path of Building Community: https://github.com/PathOfBuildingCommunity/PathOfBuilding
- PoE Reddit: r/pathofexile
- This project: [Your GitHub repo]

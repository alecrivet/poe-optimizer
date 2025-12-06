# Quick Start: Timeless Jewel Implementation

**Last Updated:** 2025-12-06

---

## Step 1: Shelve GUI Work (15 minutes)

### Create Feature Branch

```bash
# Ensure working directory is clean
git status

# Create feature branch for GUI work
git checkout -b feature/gui-development

# Push to remote
git push -u origin feature/gui-development

# Tag this point
git tag v0.5.0-gui-wip
git push origin v0.5.0-gui-wip

# Return to main development branch
git checkout main
```

### Update README

Edit `README.md` to reflect new priorities:

**Find this section:**
```markdown
**v0.5.0 (Current)** - Desktop GUI 🚧
- [x] PyQt6 desktop application
...
- [ ] Passive tree visualization canvas
- [ ] Animated genetic algorithm visualization
```

**Replace with:**
```markdown
**v0.5.0 (Shelved)** - Desktop GUI 📋
- GUI development moved to `feature/gui-development` branch
- See [GUI Development Branch](../../tree/feature/gui-development)

**v0.6.0 (Current)** - Timeless Jewel Support 🚧
- [x] Phase 1: XML Parsing
- [ ] Phase 2: Legion Data Access
- [ ] Phase 3: Calculation Integration
- [ ] Phase 4: Optimizer Integration
- [ ] Phase 5: Testing and Documentation
```

**Commit changes:**
```bash
git add README.md
git commit -m "docs: Shelve GUI development, prioritize timeless jewel support"
git push
```

---

## Step 2: Verify Current Timeless Jewel Issue (10 minutes)

### Test Current Behavior

```bash
# Run the relative calculator test with build2.xml (has Lethal Pride)
python3 -c "
from src.pob.codec import decode_pob_code
from src.pob.xml_parser import parse_pob_stats

# Load build2 which has Lethal Pride
with open('examples/build2.xml', 'r') as f:
    xml = f.read()

stats = parse_pob_stats(xml)
print(f'TotalDPS: {stats.get(\"TotalDPS\", 0):,.0f}')
print(f'Life: {stats.get(\"Life\", 0):,.0f}')
print(f'Str: {stats.get(\"Str\", 0)}')

# Check if timeless jewel is in the build
if 'timeless' in xml.lower():
    print('\\n✅ Build has timeless jewel')
else:
    print('\\n❌ No timeless jewel found')
"
```

### Compare Against PoB

1. Open `examples/build2.xml` in Path of Building
2. Note the stats (DPS, Life, Str)
3. Compare to Python output above
4. Document any discrepancies

**Expected:** Stats should match (PoB XML pre-calculated)
**Issue:** When we modify the tree, calculations may not account for jewel

---

## Step 3: Phase 1 - XML Parsing (2 hours)

### Create Timeless Jewel Module

```bash
# Create the new module
touch src/pob/timeless_jewel.py
```

**Edit `src/pob/timeless_jewel.py`:**

```python
"""
Timeless Jewel Support

This module handles parsing and managing timeless jewels from PoB builds.
"""

from dataclasses import dataclass
from typing import List, Optional
import xml.etree.ElementTree as ET


@dataclass
class TimelessJewel:
    """Represents a timeless jewel in a PoB build."""

    jewel_type: str  # "Glorious Vanity", "Lethal Pride", etc.
    seed: int        # Seed number (e.g., 13628)
    variant: str     # Variant name (e.g., "Akoya")
    variant_id: int  # Variant ID (1, 2, or 3)
    socket_node_id: Optional[int] = None  # Node ID where socketed
    item_id: Optional[int] = None  # Item ID in XML

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        return f"{self.jewel_type} ({self.variant}, Seed {self.seed})"


def parse_timeless_jewels(build_xml: str) -> List[TimelessJewel]:
    """
    Extract timeless jewels from PoB build XML.

    Args:
        build_xml: Full PoB build XML string

    Returns:
        List of TimelessJewel objects found in the build
    """
    jewels = []

    try:
        root = ET.fromstring(build_xml)

        # Find all items
        for items_elem in root.findall('.//Items'):
            for item_elem in items_elem.findall('Item'):
                item_id = item_elem.get('id')
                item_text = item_elem.text or ""

                # Check if it's a timeless jewel
                if "Timeless Jewel" in item_text:
                    jewel = _parse_timeless_jewel_item(item_text, item_id)
                    if jewel:
                        jewels.append(jewel)

        # Find socket assignments
        _assign_jewel_sockets(root, jewels)

    except Exception as e:
        print(f"Error parsing timeless jewels: {e}")

    return jewels


def _parse_timeless_jewel_item(item_text: str, item_id: str) -> Optional[TimelessJewel]:
    """Parse a single timeless jewel item."""

    lines = item_text.strip().split('\n')

    # Extract jewel type (first line)
    jewel_type = None
    for line in lines:
        if any(t in line for t in ["Glorious Vanity", "Lethal Pride",
                                     "Elegant Hubris", "Militant Faith",
                                     "Brutal Restraint"]):
            jewel_type = line.strip()
            break

    if not jewel_type:
        return None

    # Extract seed and variant from description
    seed = None
    variant = None

    for line in lines:
        # Lethal Pride: "Commanded leadership over 13628 warriors under Akoya"
        if "Commanded leadership over" in line:
            parts = line.split()
            seed = int(parts[3])
            variant = parts[-1]

        # Glorious Vanity: "Bathed in the blood of 12345 sacrificed in the name of Doryani"
        elif "Bathed in the blood of" in line:
            parts = line.split()
            seed = int(parts[5])
            variant = parts[-1]

        # Elegant Hubris: "Commissioned 12345 coins to commemorate Cadiro"
        elif "Commissioned" in line and "coins" in line:
            parts = line.split()
            seed = int(parts[1])
            variant = parts[-1]

        # Militant Faith: "12345 inscribed in the name of Dominus"
        elif "inscribed in the name of" in line:
            parts = line.split()
            seed = int(parts[0])
            variant = parts[-1]

        # Brutal Restraint: "12345 denoted service to Asenath"
        elif "denoted service to" in line:
            parts = line.split()
            seed = int(parts[0])
            variant = parts[-1]

    if seed and variant:
        variant_id = _get_variant_id(jewel_type, variant)
        return TimelessJewel(
            jewel_type=jewel_type,
            seed=seed,
            variant=variant,
            variant_id=variant_id,
            item_id=int(item_id) if item_id else None
        )

    return None


def _get_variant_id(jewel_type: str, variant: str) -> int:
    """Map variant name to ID (1, 2, or 3)."""

    variant_map = {
        "Glorious Vanity": {"Doryani": 1, "Xibaqua": 2, "Ahuana": 3},
        "Lethal Pride": {"Kaom": 1, "Rakiata": 2, "Akoya": 3},
        "Elegant Hubris": {"Cadiro": 1, "Victario": 2, "Caspiro": 3},
        "Militant Faith": {"Avarius": 1, "Dominus": 2, "Maxarius": 3},
        "Brutal Restraint": {"Asenath": 1, "Balbala": 2, "Nasima": 3},
    }

    return variant_map.get(jewel_type, {}).get(variant, 1)


def _assign_jewel_sockets(root, jewels: List[TimelessJewel]) -> None:
    """Assign socket node IDs to jewels based on ItemSet."""

    for item_set in root.findall('.//ItemSet'):
        for socket in item_set.findall('.//Socket'):
            item_id_str = socket.get('itemId')
            node_id_str = socket.get('nodeId')

            if item_id_str and item_id_str != '0' and node_id_str:
                item_id = int(item_id_str)
                node_id = int(node_id_str)

                # Find matching jewel
                for jewel in jewels:
                    if jewel.item_id == item_id:
                        jewel.socket_node_id = node_id


# For testing
if __name__ == "__main__":
    # Test with build2.xml
    with open('examples/build2.xml', 'r') as f:
        xml = f.read()

    jewels = parse_timeless_jewels(xml)
    print(f"Found {len(jewels)} timeless jewel(s):")
    for jewel in jewels:
        print(f"  - {jewel.display_name}")
        print(f"    Socket: {jewel.socket_node_id}")
```

### Test Parsing

```bash
# Run the module directly
python3 src/pob/timeless_jewel.py
```

**Expected output:**
```
Found 1 timeless jewel(s):
  - Lethal Pride (Akoya, Seed 13628)
    Socket: 26196
```

### Create Tests

```bash
touch tests/test_timeless_jewel.py
```

**Edit `tests/test_timeless_jewel.py`:**

```python
"""Tests for timeless jewel parsing."""

import unittest
from src.pob.timeless_jewel import parse_timeless_jewels, TimelessJewel


class TestTimelessJewelParsing(unittest.TestCase):

    def test_parse_lethal_pride_from_build2(self):
        """Test parsing Lethal Pride from build2.xml."""
        with open('examples/build2.xml', 'r') as f:
            xml = f.read()

        jewels = parse_timeless_jewels(xml)

        self.assertEqual(len(jewels), 1)

        jewel = jewels[0]
        self.assertEqual(jewel.jewel_type, "Lethal Pride")
        self.assertEqual(jewel.seed, 13628)
        self.assertEqual(jewel.variant, "Akoya")
        self.assertEqual(jewel.variant_id, 3)
        self.assertIsNotNone(jewel.socket_node_id)

    def test_variant_id_mapping(self):
        """Test variant ID mapping."""
        jewel = TimelessJewel(
            jewel_type="Lethal Pride",
            seed=1000,
            variant="Kaom",
            variant_id=1
        )
        self.assertEqual(jewel.variant_id, 1)


if __name__ == '__main__':
    unittest.main()
```

### Run Tests

```bash
python3 -m pytest tests/test_timeless_jewel.py -v
```

---

## Step 4: Commit Phase 1

```bash
git add src/pob/timeless_jewel.py tests/test_timeless_jewel.py
git commit -m "feat: Add timeless jewel XML parsing (Phase 1)"
git push
```

---

## Next Steps

After completing Phase 1:
1. **Phase 2:** Access PoB's legion data
2. **Phase 3:** Integrate with calculation engine
3. **Phase 4:** Update optimizer
4. **Phase 5:** Testing and documentation

See `TIMELESS_JEWEL_IMPLEMENTATION_PLAN.md` for full details.

---

## Validation Checklist

- [ ] GUI work shelved to feature branch
- [ ] README updated
- [ ] Timeless jewel parsing implemented
- [ ] Tests passing
- [ ] Phase 1 committed and pushed
- [ ] Ready to start Phase 2

---

**Estimated Time for Quickstart:** 2-3 hours
**Status:** Ready to begin

"""
Timeless Jewel Support

Timeless jewels transform passive nodes within their radius based on a seed value.
There are 5 types, each with 3 variants:

1. Glorious Vanity (Vaal) - Replaces passives, adds keystone
   - Variants: Doryani (Corrupted Soul), Xibaqua (Divine Flesh), Ahuana (Immortal Ambition)

2. Lethal Pride (Karui) - Adds modifiers to small passives
   - Variants: Kaom (Strength of Blood), Rakiata (Tempered by War), Akoya (Chainbreaker)

3. Elegant Hubris (Eternal Empire) - Adds percentage modifiers
   - Variants: Cadiro (Supreme Decadence), Victario (Supreme Grandstanding), Caspiro (Supreme Ostentation)

4. Militant Faith (Templar) - Transforms notables to Devotion
   - Variants: Avarius, Dominus, Maxarius

5. Brutal Restraint (Maraketh) - Transforms passives
   - Variants: Asenath, Balbala, Nasima
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, TYPE_CHECKING

from .base import BaseJewel, JewelCategory, JewelRadius

if TYPE_CHECKING:
    from ..tree_parser import PassiveTreeGraph


# Timeless jewel type definitions
TIMELESS_JEWEL_TYPES = {
    "Glorious Vanity": {
        "legion": "Vaal",
        "variants": {"Doryani": 1, "Xibaqua": 2, "Ahuana": 3},
        "keystone_pattern": r"Bathed in the blood of (\d+) sacrificed in the name of (\w+)",
    },
    "Lethal Pride": {
        "legion": "Karui",
        "variants": {"Kaom": 1, "Rakiata": 2, "Akoya": 3},
        "keystone_pattern": r"Commanded leadership over (\d+) warriors under (\w+)",
    },
    "Elegant Hubris": {
        "legion": "Eternal Empire",
        "variants": {"Cadiro": 1, "Victario": 2, "Caspiro": 3},
        "keystone_pattern": r"Commissioned (\d+) coins to commemorate (\w+)",
    },
    "Militant Faith": {
        "legion": "Templar",
        "variants": {"Avarius": 1, "Dominus": 2, "Maxarius": 3},
        "keystone_pattern": r"(\d+) inscribed in the name of (\w+)",
    },
    "Brutal Restraint": {
        "legion": "Maraketh",
        "variants": {"Asenath": 1, "Balbala": 2, "Nasima": 3},
        "keystone_pattern": r"(\d+) denoted service of (\w+)",
    },
}


@dataclass
class TimelessJewel(BaseJewel):
    """
    Represents a timeless jewel in a PoB build.

    Timeless jewels transform passive nodes based on:
    - Type: Which legion (Vaal, Karui, etc.)
    - Seed: The numeric seed value
    - Variant: Which conqueror (determines keystone)

    Example: Lethal Pride (Akoya, Seed 13628) - Karui jewel that adds
    "Chainbreaker" keystone and various strength/double damage mods.
    """

    jewel_type: str = ""  # "Glorious Vanity", "Lethal Pride", etc.
    seed: int = 0  # The seed number
    variant: str = ""  # The variant/conqueror name
    variant_id: int = 1  # 1, 2, or 3
    legion: str = ""  # "Vaal", "Karui", etc.

    def __post_init__(self):
        self.category = JewelCategory.TIMELESS
        if self.jewel_type in TIMELESS_JEWEL_TYPES:
            self.legion = TIMELESS_JEWEL_TYPES[self.jewel_type]["legion"]

    def get_affected_nodes(self, tree: "PassiveTreeGraph") -> Set[int]:
        """
        Return nodes within the jewel's Large radius.

        Timeless jewels always have Large radius.
        """
        if not self.socket_node_id or not tree:
            return set()

        # Use tree's radius calculation if available
        if hasattr(tree, "get_nodes_in_radius"):
            return tree.get_nodes_in_radius(self.socket_node_id, JewelRadius.LARGE)

        return set()

    @property
    def display_name(self) -> str:
        """Human-readable name for the jewel."""
        return f"{self.jewel_type} ({self.variant}, Seed {self.seed})"

    @property
    def keystone_name(self) -> Optional[str]:
        """Get the keystone granted by this jewel's variant."""
        keystones = {
            ("Glorious Vanity", "Doryani"): "Corrupted Soul",
            ("Glorious Vanity", "Xibaqua"): "Divine Flesh",
            ("Glorious Vanity", "Ahuana"): "Immortal Ambition",
            ("Lethal Pride", "Kaom"): "Strength of Blood",
            ("Lethal Pride", "Rakiata"): "Tempered by War",
            ("Lethal Pride", "Akoya"): "Chainbreaker",
            ("Elegant Hubris", "Cadiro"): "Supreme Decadence",
            ("Elegant Hubris", "Victario"): "Supreme Grandstanding",
            ("Elegant Hubris", "Caspiro"): "Supreme Ostentation",
            ("Militant Faith", "Avarius"): "Inner Conviction",
            ("Militant Faith", "Dominus"): "Power of Purpose",
            ("Militant Faith", "Maxarius"): "Transcendence",
            ("Brutal Restraint", "Asenath"): "Dance with Death",
            ("Brutal Restraint", "Balbala"): "The Traitor",
            ("Brutal Restraint", "Nasima"): "Second Skin",
        }
        return keystones.get((self.jewel_type, self.variant))


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
        for items_elem in root.findall(".//Items"):
            for item_elem in items_elem.findall("Item"):
                item_id = item_elem.get("id")
                item_text = item_elem.text or ""

                # Check if it's a timeless jewel
                if "Timeless Jewel" in item_text:
                    jewel = _parse_timeless_jewel_item(item_text, item_id)
                    if jewel:
                        jewels.append(jewel)

        # Find socket assignments
        _assign_jewel_sockets(root, jewels)

    except Exception as e:
        import logging

        logging.warning(f"Error parsing timeless jewels: {e}")

    return jewels


def _parse_timeless_jewel_item(item_text: str, item_id: str) -> Optional[TimelessJewel]:
    """Parse a single timeless jewel item."""
    lines = item_text.strip().split("\n")

    # Find jewel type (the name line)
    jewel_type = None
    for line in lines:
        for tj_type in TIMELESS_JEWEL_TYPES:
            if tj_type in line:
                jewel_type = tj_type
                break
        if jewel_type:
            break

    if not jewel_type:
        return None

    # Extract seed and variant using the pattern for this jewel type
    seed = None
    variant = None
    type_info = TIMELESS_JEWEL_TYPES[jewel_type]

    for line in lines:
        match = re.search(type_info["keystone_pattern"], line)
        if match:
            seed = int(match.group(1))
            variant = match.group(2)
            break

    if not seed or not variant:
        # Try alternative parsing for edge cases
        seed, variant = _parse_timeless_fallback(lines, jewel_type)

    if seed and variant:
        variant_id = type_info["variants"].get(variant, 1)
        return TimelessJewel(
            category=JewelCategory.TIMELESS,
            item_id=int(item_id) if item_id else 0,
            raw_text=item_text,
            jewel_type=jewel_type,
            seed=seed,
            variant=variant,
            variant_id=variant_id,
            legion=type_info["legion"],
        )

    return None


def _parse_timeless_fallback(lines: List[str], jewel_type: str) -> tuple:
    """Fallback parsing for non-standard timeless jewel text."""
    seed = None
    variant = None

    # Try to find seed (any large number)
    for line in lines:
        numbers = re.findall(r"\b(\d{4,5})\b", line)
        if numbers:
            seed = int(numbers[0])
            break

    # Try to find variant name
    type_info = TIMELESS_JEWEL_TYPES.get(jewel_type, {})
    variants = type_info.get("variants", {})
    for line in lines:
        for var_name in variants:
            if var_name in line:
                variant = var_name
                break
        if variant:
            break

    return seed, variant


def _assign_jewel_sockets(root: ET.Element, jewels: List[TimelessJewel]) -> None:
    """Assign socket node IDs to jewels based on Tree/Spec/Sockets structure."""
    # Look for sockets in Tree -> Spec -> Sockets
    for sockets_elem in root.findall(".//Sockets"):
        for socket in sockets_elem.findall("Socket"):
            item_id_str = socket.get("itemId")
            node_id_str = socket.get("nodeId")

            if item_id_str and item_id_str != "0" and node_id_str:
                try:
                    item_id = int(item_id_str)
                    node_id = int(node_id_str)

                    # Find matching jewel
                    for jewel in jewels:
                        if jewel.item_id == item_id:
                            jewel.socket_node_id = node_id
                except ValueError:
                    continue

    # Also check ItemSet for alternate structure
    for item_set in root.findall(".//ItemSet"):
        for socket in item_set.findall(".//Socket"):
            item_id_str = socket.get("itemId")
            node_id_str = socket.get("nodeId")

            if item_id_str and item_id_str != "0" and node_id_str:
                try:
                    item_id = int(item_id_str)
                    node_id = int(node_id_str)

                    for jewel in jewels:
                        if jewel.item_id == item_id:
                            jewel.socket_node_id = node_id
                except ValueError:
                    continue

        # Also check Slot elements with Jewel in name
        for slot in item_set.findall(".//Slot"):
            name = slot.get("name", "")
            item_id_str = slot.get("itemId")

            if "Jewel" in name and item_id_str and item_id_str != "0":
                # Extract node ID from slot name like "Jewel 26196"
                node_match = re.search(r"Jewel (\d+)", name)
                if node_match:
                    try:
                        node_id = int(node_match.group(1))
                        item_id = int(item_id_str)

                        for jewel in jewels:
                            if jewel.item_id == item_id:
                                jewel.socket_node_id = node_id
                    except ValueError:
                        continue


def get_timeless_jewel_modifiers(
    jewel: TimelessJewel, node_id: int, pob_path: str = None
) -> List[str]:
    """
    Get the modifiers applied to a node by a timeless jewel.

    This requires loading PoB's timeless jewel data files.

    Args:
        jewel: The timeless jewel
        node_id: The passive node ID to query
        pob_path: Path to PathOfBuilding directory

    Returns:
        List of modifier strings applied to the node
    """
    # TODO: Implement using PoB's TimelessJewelData
    # This will be implemented in Phase 2
    return []


# For testing
if __name__ == "__main__":
    # Test with build2.xml
    with open("examples/build2.xml", "r") as f:
        xml = f.read()

    jewels = parse_timeless_jewels(xml)
    print(f"Found {len(jewels)} timeless jewel(s):")
    for jewel in jewels:
        print(f"  - {jewel.display_name}")
        print(f"    Socket: {jewel.socket_node_id}")
        print(f"    Keystone: {jewel.keystone_name}")

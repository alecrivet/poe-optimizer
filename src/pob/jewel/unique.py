"""
Unique Jewel Support

Handles the 178+ unique jewels in Path of Exile. Most unique jewels
are handled by PoB's calculation engine; we just need to ensure they
are properly passed through.

Categories:
1. Simple Stat Jewels - Direct stat bonuses (handled by PoB)
2. Radius Jewels - Affect passives in radius (need radius calculation)
3. Build-Altering Jewels - Major mechanical changes (handled by PoB)
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Set, TYPE_CHECKING

from .base import BaseJewel, JewelCategory, JewelRadius, is_timeless_jewel, is_cluster_jewel

if TYPE_CHECKING:
    from ..tree_parser import PassiveTreeGraph


# Notable unique jewels with special mechanics
NOTABLE_UNIQUE_JEWELS = {
    # Pathing bypass jewels
    "Thread of Hope": {"radius_effect": True, "mechanic": "allocate_in_radius"},
    "Impossible Escape": {"radius_effect": True, "mechanic": "allocate_in_radius"},
    # Radius transformation jewels
    "Fireborn": {"radius_effect": True, "mechanic": "transform_damage"},
    "Cold Steel": {"radius_effect": True, "mechanic": "transform_damage"},
    "Anatomical Knowledge": {"radius_effect": True, "mechanic": "stat_per_attribute"},
    "Eldritch Knowledge": {"radius_effect": True, "mechanic": "stat_per_attribute"},
    # Build-altering jewels
    "Dissolution of the Flesh": {"mechanic": "life_reservation"},
    "Bloodnotch": {"mechanic": "stun_recovery"},
    "Watcher's Eye": {"mechanic": "aura_conditional"},
    "Calamitous Visions": {"mechanic": "adds_keystone"},
    "The Anima Stone": {"mechanic": "golem_limit"},
    # Breach jewels
    "The Blue Dream": {"radius_effect": True},
    "The Blue Nightmare": {"radius_effect": True},
    "The Green Dream": {"radius_effect": True},
    "The Green Nightmare": {"radius_effect": True},
    "The Red Dream": {"radius_effect": True},
    "The Red Nightmare": {"radius_effect": True},
}


@dataclass
class UniqueJewel(BaseJewel):
    """
    Represents a unique jewel in a PoB build.

    Most unique jewels are handled entirely by PoB. This class
    tracks them for constraint generation and radius calculations.
    """

    name: str = ""  # The unique jewel name
    base_type: str = ""  # "Cobalt Jewel", "Crimson Jewel", etc.
    radius: Optional[JewelRadius] = None
    modifiers: List[str] = field(default_factory=list)
    has_radius_effect: bool = False

    def __post_init__(self):
        self.category = JewelCategory.UNIQUE
        # Check if this jewel has radius effects
        if self.name in NOTABLE_UNIQUE_JEWELS:
            info = NOTABLE_UNIQUE_JEWELS[self.name]
            self.has_radius_effect = info.get("radius_effect", False)

    def get_affected_nodes(self, tree: "PassiveTreeGraph") -> Set[int]:
        """
        Return nodes affected by this jewel's radius effect.

        Only applicable for radius jewels like Thread of Hope.
        """
        if not self.has_radius_effect or not self.radius or not self.socket_node_id:
            return set()

        if hasattr(tree, "get_nodes_in_radius"):
            return tree.get_nodes_in_radius(self.socket_node_id, self.radius)

        return set()

    @property
    def display_name(self) -> str:
        """Human-readable name for the jewel."""
        return self.name or "Unknown Unique Jewel"

    @property
    def is_radius_jewel(self) -> bool:
        """Check if this jewel has radius effects."""
        return self.has_radius_effect and self.radius is not None


def parse_unique_jewels(build_xml: str) -> List[UniqueJewel]:
    """
    Extract unique jewels from PoB build XML.

    This excludes timeless and cluster jewels, which are handled separately.

    Args:
        build_xml: Full PoB build XML string

    Returns:
        List of UniqueJewel objects found in the build
    """
    jewels = []

    try:
        root = ET.fromstring(build_xml)

        # Find all items
        for items_elem in root.findall(".//Items"):
            for item_elem in items_elem.findall("Item"):
                item_id = item_elem.get("id")
                item_text = item_elem.text or ""

                # Skip non-jewels
                if not _is_jewel_item(item_text):
                    continue

                # Skip timeless and cluster jewels (handled separately)
                if is_timeless_jewel(item_text) or is_cluster_jewel(item_text):
                    continue

                # Check if it's a unique jewel
                if "Rarity: UNIQUE" in item_text:
                    jewel = _parse_unique_jewel_item(item_text, item_id)
                    if jewel:
                        jewels.append(jewel)

        # Find socket assignments
        _assign_jewel_sockets(root, jewels)

    except Exception as e:
        import logging

        logging.warning(f"Error parsing unique jewels: {e}")

    return jewels


def _is_jewel_item(item_text: str) -> bool:
    """Check if item text describes a jewel."""
    jewel_bases = [
        "Cobalt Jewel",
        "Crimson Jewel",
        "Viridian Jewel",
        "Prismatic Jewel",
        "Murderous Eye Jewel",
        "Searching Eye Jewel",
        "Hypnotic Eye Jewel",
        "Ghastly Eye Jewel",
    ]
    return any(base in item_text for base in jewel_bases)


def _parse_unique_jewel_item(item_text: str, item_id: str) -> Optional[UniqueJewel]:
    """Parse a single unique jewel item."""
    lines = item_text.strip().split("\n")

    # Find the jewel name (usually the first non-empty line after Rarity)
    name = None
    base_type = None

    for i, line in enumerate(lines):
        line = line.strip()

        # Find base type
        for base in [
            "Cobalt Jewel",
            "Crimson Jewel",
            "Viridian Jewel",
            "Prismatic Jewel",
            "Murderous Eye Jewel",
            "Searching Eye Jewel",
            "Hypnotic Eye Jewel",
            "Ghastly Eye Jewel",
        ]:
            if base in line:
                base_type = base
                break

        # The name is usually right after "Rarity: UNIQUE"
        if line == "Rarity: UNIQUE" and i + 1 < len(lines):
            name = lines[i + 1].strip()

    if not name:
        # Try first capitalized line
        for line in lines:
            line = line.strip()
            if line and not line.startswith("Rarity") and line[0].isupper():
                name = line
                break

    # Parse radius if present
    radius = None
    for line in lines:
        if "Radius:" in line:
            if "Small" in line:
                radius = JewelRadius.SMALL
            elif "Medium" in line:
                radius = JewelRadius.MEDIUM
            elif "Large" in line:
                radius = JewelRadius.LARGE
            break

    # Parse modifiers (lines that look like mods)
    modifiers = []
    for line in lines:
        line = line.strip()
        # Skip metadata lines
        if any(
            skip in line
            for skip in [
                "Rarity:",
                "Jewel",
                "Radius:",
                "Limited to:",
                "Implicits:",
                "Requires",
                "Item Level:",
            ]
        ):
            continue
        # Skip empty and short lines
        if len(line) < 5:
            continue
        # This is probably a modifier
        modifiers.append(line)

    return UniqueJewel(
        category=JewelCategory.UNIQUE,
        item_id=int(item_id) if item_id else 0,
        raw_text=item_text,
        name=name or "Unknown",
        base_type=base_type or "Unknown",
        radius=radius,
        modifiers=modifiers,
    )


def _assign_jewel_sockets(root: ET.Element, jewels: List[UniqueJewel]) -> None:
    """Assign socket node IDs to jewels."""
    # Look for sockets in Tree -> Spec -> Sockets
    for sockets_elem in root.findall(".//Sockets"):
        for socket in sockets_elem.findall("Socket"):
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


# For testing
if __name__ == "__main__":
    print("Unique jewel module loaded successfully")
    print(f"Notable unique jewels tracked: {len(NOTABLE_UNIQUE_JEWELS)}")

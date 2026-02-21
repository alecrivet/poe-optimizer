"""
Converter from GGG API JSON format to Path of Building XML format.

This module handles the transformation between GGG's character
representation and PoB's XML structure.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..pob.tree_version import get_latest_tree_version
import logging

from .models import Character, CharacterItems, PassiveTree, Item

logger = logging.getLogger(__name__)


# Class ID to PoB class name and ID mapping
# GGG class IDs: 0=Scion, 1=Marauder, 2=Ranger, 3=Witch, 4=Duelist, 5=Templar, 6=Shadow
# PoB class IDs: 1=Marauder, 2=Ranger, 3=Witch, 4=Duelist, 5=Templar, 6=Shadow, 7=Scion
CLASS_MAP = {
    0: ("Scion", 7),
    1: ("Marauder", 1),
    2: ("Ranger", 2),
    3: ("Witch", 3),
    4: ("Duelist", 4),
    5: ("Templar", 5),
    6: ("Shadow", 6),
}

# Ascendancy mappings (class_id, ascendancy_id) -> name
ASCENDANCY_MAP = {
    # Scion
    (0, 1): "Ascendant",
    # Marauder
    (1, 1): "Juggernaut",
    (1, 2): "Berserker",
    (1, 3): "Chieftain",
    # Ranger
    (2, 1): "Raider",
    (2, 2): "Deadeye",
    (2, 3): "Pathfinder",
    # Witch
    (3, 1): "Necromancer",
    (3, 2): "Elementalist",
    (3, 3): "Occultist",
    # Duelist
    (4, 1): "Slayer",
    (4, 2): "Gladiator",
    (4, 3): "Champion",
    # Templar
    (5, 1): "Inquisitor",
    (5, 2): "Hierophant",
    (5, 3): "Guardian",
    # Shadow
    (6, 1): "Assassin",
    (6, 2): "Trickster",
    (6, 3): "Saboteur",
}

# Inventory slot to PoB slot name mapping
SLOT_MAP = {
    "Weapon": "Weapon 1",
    "Offhand": "Weapon 2",
    "Weapon2": "Weapon 1 Swap",
    "Offhand2": "Weapon 2 Swap",
    "Helm": "Helmet",
    "BodyArmour": "Body Armour",
    "Gloves": "Gloves",
    "Boots": "Boots",
    "Amulet": "Amulet",
    "Ring": "Ring 1",
    "Ring2": "Ring 2",
    "Belt": "Belt",
    "Flask": "Flask 1",
    "Flask2": "Flask 2",
    "Flask3": "Flask 3",
    "Flask4": "Flask 4",
    "Flask5": "Flask 5",
}


@dataclass
class ConversionOptions:
    """Options for controlling the conversion process."""
    include_items: bool = True
    include_passives: bool = True
    tree_version: Optional[str] = None
    default_gem_level: int = 20
    default_gem_quality: int = 20

    def __post_init__(self):
        if self.tree_version is None:
            self.tree_version = get_latest_tree_version() or "3_27"


class GGGToPoB:
    """
    Converter from GGG API format to PoB XML format.

    Usage:
        converter = GGGToPoB()
        xml_str = converter.convert(character, items, passives)

        # Or convert to PoB code
        from src.pob.codec import encode_pob_code
        pob_code = encode_pob_code(xml_str)
    """

    def __init__(self, options: Optional[ConversionOptions] = None):
        self.options = options or ConversionOptions()

    def convert(
        self,
        character: Character,
        items: Optional[CharacterItems] = None,
        passives: Optional[PassiveTree] = None,
    ) -> str:
        """
        Convert GGG character data to PoB XML.

        Args:
            character: Character info from get-characters
            items: Items from get-items (optional)
            passives: Passive tree from get-passive-skills (optional)

        Returns:
            PoB-compatible XML string
        """
        root = ET.Element("PathOfBuilding")

        # Build section
        build_elem = self._create_build_element(character)
        root.append(build_elem)

        # Tree section
        tree_elem = self._create_tree_element(character, passives)
        root.append(tree_elem)

        # Skills section (placeholder)
        skills_elem = self._create_skills_element()
        root.append(skills_elem)

        # Items section
        if items and self.options.include_items:
            items_elem = self._create_items_element(items)
            root.append(items_elem)
        else:
            items_elem = self._create_empty_items_element()
            root.append(items_elem)

        # Config section
        config_elem = self._create_config_element()
        root.append(config_elem)

        # Notes section
        notes_elem = ET.SubElement(root, "Notes")
        notes_elem.text = f"Imported from GGG API: {character.name} ({character.league})"

        return ET.tostring(root, encoding="unicode")

    def _create_build_element(self, character: Character) -> ET.Element:
        """Create the <Build> element with character info."""
        class_name, pob_class_id = CLASS_MAP.get(
            character.class_id, ("Scion", 7)
        )

        ascendancy_name = ASCENDANCY_MAP.get(
            (character.class_id, character.ascendancy_class), ""
        )

        build = ET.Element("Build")
        build.set("level", str(character.level))
        build.set("targetVersion", "3_0")
        build.set("className", class_name)
        build.set("ascendClassName", ascendancy_name)
        build.set("bandit", "None")
        build.set("mainSocketGroup", "1")

        return build

    def _create_tree_element(
        self,
        character: Character,
        passives: Optional[PassiveTree] = None,
    ) -> ET.Element:
        """Create the <Tree> element with passive nodes."""
        tree = ET.Element("Tree")
        tree.set("activeSpec", "1")

        spec = ET.SubElement(tree, "Spec")
        spec.set("title", f"Imported: {character.name}")
        spec.set("treeVersion", self.options.tree_version)

        # Class info for tree
        class_name, pob_class_id = CLASS_MAP.get(
            character.class_id, ("Scion", 7)
        )
        spec.set("classId", str(pob_class_id))
        spec.set("ascendClassId", str(character.ascendancy_class))

        if passives and self.options.include_passives:
            # Combine regular hashes and extended hashes (cluster nodes)
            all_nodes = passives.hashes + passives.hashes_ex
            if all_nodes:
                spec.set("nodes", ",".join(str(n) for n in sorted(all_nodes)))
                logger.info(f"Converted {len(all_nodes)} passive nodes")
            else:
                spec.set("nodes", "")

            # Format mastery effects as {node_id,effect_id} pairs
            if passives.mastery_effects:
                mastery_str = ",".join(
                    f"{{{node_id},{effect_id}}}"
                    for node_id, effect_id in sorted(passives.mastery_effects.items())
                )
                spec.set("masteryEffects", mastery_str)
                logger.info(f"Converted {len(passives.mastery_effects)} mastery effects")

            # Jewel sockets placeholder
            sockets_elem = ET.SubElement(spec, "Sockets")
            # NOTE: jewel_data to socket mapping not yet implemented (tracked: S2-001)

        else:
            spec.set("nodes", "")

        # URL placeholder
        url_elem = ET.SubElement(spec, "URL")

        return tree

    def _create_skills_element(self) -> ET.Element:
        """Create the <Skills> element (placeholder)."""
        skills = ET.Element("Skills")
        skills.set("activeSkillSet", "1")
        skills.set("defaultGemLevel", str(self.options.default_gem_level))
        skills.set("defaultGemQuality", str(self.options.default_gem_quality))

        skill_set = ET.SubElement(skills, "SkillSet")
        skill_set.set("id", "1")

        return skills

    def _create_items_element(self, items: CharacterItems) -> ET.Element:
        """Create the <Items> element with equipped gear."""
        items_elem = ET.Element("Items")
        items_elem.set("activeItemSet", "1")

        # Track slot assignments
        slot_assignments = []
        item_id = 1

        for item in items.items:
            # Skip items without inventory slot (e.g., stash items)
            if not item.inventory_id:
                continue

            item_elem = self._item_to_xml(item, item_id)
            items_elem.append(item_elem)

            # Map to PoB slot
            pob_slot = SLOT_MAP.get(item.inventory_id)
            if pob_slot:
                slot_assignments.append((pob_slot, item_id))

            item_id += 1

        logger.info(f"Converted {item_id - 1} items")

        # Create ItemSet with slot assignments
        item_set = ET.SubElement(items_elem, "ItemSet")
        item_set.set("id", "1")
        item_set.set("useSecondWeaponSet", "nil")

        for slot_name, slot_item_id in slot_assignments:
            slot = ET.SubElement(item_set, "Slot")
            slot.set("name", slot_name)
            slot.set("itemId", str(slot_item_id))

        return items_elem

    def _create_empty_items_element(self) -> ET.Element:
        """Create an empty <Items> element."""
        items = ET.Element("Items")
        items.set("activeItemSet", "1")

        item_set = ET.SubElement(items, "ItemSet")
        item_set.set("id", "1")

        return items

    def _item_to_xml(self, item: Item, item_id: int) -> ET.Element:
        """
        Convert a single item to PoB XML format.

        PoB uses a text-based format inside <Item> tags.
        """
        item_elem = ET.Element("Item")
        item_elem.set("id", str(item_id))

        # Build the text content
        lines = []

        # Rarity
        lines.append(f"Rarity: {item.rarity.upper()}")

        # Name (for rare/unique)
        if item.name:
            lines.append(item.name)

        # Base type
        lines.append(item.type_line)

        # Item level
        lines.append(f"Item Level: {item.ilvl}")

        # Sockets (if any)
        if item.sockets:
            socket_str = self._format_sockets(item.sockets)
            if socket_str:
                lines.append(f"Sockets: {socket_str}")

        # Influence tags
        influences = []
        if item.shaper:
            influences.append("Shaper Item")
        if item.elder:
            influences.append("Elder Item")
        if item.crusader:
            influences.append("Crusader Item")
        if item.redeemer:
            influences.append("Redeemer Item")
        if item.hunter:
            influences.append("Hunter Item")
        if item.warlord:
            influences.append("Warlord Item")
        for inf in influences:
            lines.append(inf)

        # Implicits count
        num_implicits = len(item.implicit_mods) + len(item.enchant_mods)
        lines.append(f"Implicits: {num_implicits}")

        # Enchants (as implicits)
        for mod in item.enchant_mods:
            lines.append(f"{{crafted}}{mod}")

        # Implicits
        for mod in item.implicit_mods:
            lines.append(mod)

        # Explicit mods
        for mod in item.explicit_mods:
            if mod in item.fractured_mods:
                lines.append(f"{{fractured}}{mod}")
            else:
                lines.append(mod)

        # Crafted mods
        for mod in item.crafted_mods:
            lines.append(f"{{crafted}}{mod}")

        # Corrupted
        if item.corrupted:
            lines.append("Corrupted")

        item_elem.text = "\n".join(lines)

        return item_elem

    def _format_sockets(self, sockets: List) -> str:
        """Format socket list into PoB socket string (e.g., 'R-R-G-G B B')."""
        if not sockets:
            return ""

        # Map socket attrs to colors
        color_map = {
            "S": "R",  # Strength = Red
            "D": "G",  # Dexterity = Green
            "I": "B",  # Intelligence = Blue
            "G": "W",  # White
            "A": "A",  # Abyss
            "DV": "W",  # Delve = White
        }

        groups = {}
        for socket in sockets:
            group = socket.group
            color = color_map.get(socket.attr, "W")
            if group not in groups:
                groups[group] = []
            groups[group].append(color)

        # Join sockets within groups with '-', separate groups with ' '
        result_parts = []
        for group_id in sorted(groups.keys()):
            group_colors = groups[group_id]
            result_parts.append("-".join(group_colors))

        return " ".join(result_parts)

    def _create_config_element(self) -> ET.Element:
        """Create the <Config> element with default settings."""
        config = ET.Element("Config")

        return config


def convert_character_to_pob(
    character: Character,
    items: Optional[CharacterItems] = None,
    passives: Optional[PassiveTree] = None,
    options: Optional[ConversionOptions] = None,
) -> str:
    """
    Convenience function to convert character data to PoB XML.

    Args:
        character: Character info from get-characters
        items: Items from get-items (optional)
        passives: Passive tree from get-passive-skills (optional)
        options: Conversion options

    Returns:
        PoB-compatible XML string
    """
    converter = GGGToPoB(options)
    return converter.convert(character, items, passives)

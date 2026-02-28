"""
Converter from GGG API JSON format to Path of Building XML format.

This module handles the transformation between GGG's character
representation and PoB's XML structure.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..pob.tree_version import get_latest_tree_version_or_raise
import logging

from .models import Character, CharacterItems, PassiveTree, Item

# Lazy-loaded gem database for resolving gem IDs
_gem_db = None

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
            self.tree_version = get_latest_tree_version_or_raise()


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
        self._main_socket_group = 1
        build_elem = self._create_build_element(character)
        root.append(build_elem)

        # Tree section
        tree_elem = self._create_tree_element(character, passives)
        root.append(tree_elem)

        # Skills section (populated from item socket data)
        skills_elem = self._create_skills_element(items)
        root.append(skills_elem)

        # Update mainSocketGroup based on gem extraction
        build_elem.set("mainSocketGroup", str(self._main_socket_group))

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
        # Try class_id mapping first (if API returned it)
        if character.class_id > 0:
            class_name, pob_class_id = CLASS_MAP.get(
                character.class_id, ("Scion", 7)
            )
            ascendancy_name = ASCENDANCY_MAP.get(
                (character.class_id, character.ascendancy_class), ""
            )
        else:
            # Fall back to name-based detection from Character model
            class_name = character.class_name or "Scion"
            ascendancy_name = character.ascendancy_name or ""

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
        if character.class_id > 0:
            class_name, pob_class_id = CLASS_MAP.get(
                character.class_id, ("Scion", 7)
            )
        else:
            # Reverse lookup: find class_id from class_name
            class_name = character.class_name or "Scion"
            pob_class_id = 7  # Default to Scion
            for ggg_id, (name, pob_id) in CLASS_MAP.items():
                if name == class_name:
                    pob_class_id = pob_id
                    break
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

    def _create_skills_element(
        self, items: Optional[CharacterItems] = None
    ) -> ET.Element:
        """
        Create the <Skills> element from item socket data.

        Extracts gems from each item's socketedItems, groups them by
        socket group (linked sockets), and creates PoB Skill/Gem elements.
        """
        skills = ET.Element("Skills")
        skills.set("activeSkillSet", "1")
        skills.set("defaultGemLevel", str(self.options.default_gem_level))
        skills.set("defaultGemQuality", str(self.options.default_gem_quality))

        skill_set = ET.SubElement(skills, "SkillSet")
        skill_set.set("id", "1")

        if not items:
            return skills

        main_group_idx = 0  # Track which group has the most gems (likely main skill)
        max_gems = 0
        group_counter = 0

        for item in items.items:
            if not item.inventory_id:
                continue

            # Get raw item data to access socketedItems
            # We need to get this from the original API data
            raw_data = getattr(item, '_raw_data', None)
            if raw_data is None:
                continue

            socketed_items = raw_data.get("socketedItems", [])
            if not socketed_items:
                continue

            # Group gems by socket group (linked sockets)
            socket_groups: Dict[int, List[Dict]] = {}
            for gem_data in socketed_items:
                socket_idx = gem_data.get("socket", 0)
                # Find which socket group this gem belongs to
                gem_group = self._get_socket_group(item, socket_idx)
                if gem_group not in socket_groups:
                    socket_groups[gem_group] = []
                socket_groups[gem_group].append(gem_data)

            pob_slot = SLOT_MAP.get(item.inventory_id, item.inventory_id)

            for group_id in sorted(socket_groups.keys()):
                gems = socket_groups[group_id]
                group_counter += 1

                skill_elem = ET.SubElement(skill_set, "Skill")
                skill_elem.set("slot", pob_slot)
                skill_elem.set("enabled", "true")
                skill_elem.set("label", "")
                skill_elem.set("mainActiveSkill", "1")
                skill_elem.set("includeInFullDPS", "nil")

                for gem_data in gems:
                    gem_elem = self._gem_to_xml(gem_data)
                    skill_elem.append(gem_elem)

                # Track the group with the most gems as the main skill
                # Prefer body armour (most common main skill slot) on ties
                is_body = pob_slot == "Body Armour"
                score = len(gems) + (1 if is_body else 0)
                if score > max_gems:
                    max_gems = score
                    main_group_idx = group_counter

        # Update mainSocketGroup on the Build element later
        self._main_socket_group = main_group_idx

        logger.info(f"Created {group_counter} skill groups from equipped gems")

        return skills

    def _get_socket_group(self, item: Item, socket_idx: int) -> int:
        """Get the socket group number for a given socket index."""
        if not item.sockets or socket_idx >= len(item.sockets):
            return 0
        return item.sockets[socket_idx].group

    def _gem_to_xml(self, gem_data: Dict[str, Any]) -> ET.Element:
        """Convert a GGG gem JSON object to a PoB <Gem> XML element."""
        global _gem_db

        gem = ET.Element("Gem")

        gem_name = gem_data.get("typeLine", "")
        gem.set("nameSpec", gem_name)
        gem.set("enabled", "true")

        # Extract level and quality from properties
        level = self.options.default_gem_level
        quality = 0
        for prop in gem_data.get("properties", []):
            if prop["name"] == "Level":
                try:
                    # Format: [["20 (Max)", 0]] or [["20", 0]]
                    level_str = prop["values"][0][0].split(" ")[0]
                    level = int(level_str)
                except (IndexError, ValueError):
                    pass
            elif prop["name"] == "Quality":
                try:
                    # Format: [["+20%", 1]]
                    qual_str = prop["values"][0][0].replace("+", "").replace("%", "")
                    quality = int(qual_str)
                except (IndexError, ValueError):
                    pass

        gem.set("level", str(level))
        gem.set("quality", str(quality))

        # Resolve gem IDs from the GemDatabase for PoB compatibility
        # PoB needs gemId, variantId, and skillId to evaluate gems correctly
        if _gem_db is None:
            try:
                from ..pob.gem_database import GemDatabase
                _gem_db = GemDatabase.from_pob_data()
            except Exception as e:
                logger.debug(f"Could not load GemDatabase: {e}")
                _gem_db = False  # Sentinel to avoid retrying

        if _gem_db:
            # Try exact name match, then without " Support" suffix,
            # then baseType (GGG API appends " Support" to support gem names
            # but PoB's Gems.lua omits it)
            db_gem = _gem_db.get_gem_by_name(gem_name)
            if not db_gem and gem_name.endswith(" Support"):
                db_gem = _gem_db.get_gem_by_name(gem_name[:-8])
            if not db_gem:
                base_type = gem_data.get("baseType", "")
                db_gem = _gem_db.get_gem_by_name(base_type)
                if not db_gem and base_type.endswith(" Support"):
                    db_gem = _gem_db.get_gem_by_name(base_type[:-8])
            if db_gem:
                gem.set("nameSpec", db_gem.name)  # Use canonical PoB name
                gem.set("gemId", db_gem.game_id)
                gem.set("variantId", db_gem.variant_id)
                gem.set("skillId", db_gem.granted_effect_id)

        return gem

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

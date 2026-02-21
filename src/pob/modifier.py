"""
Build Modifier - XML Modification Functions

This module provides functions to modify Path of Building builds at the XML level.
These modifications prepare builds for recalculation via PoB desktop app.

Modification Strategy:
1. Parse XML to ElementTree
2. Modify desired elements
3. Return modified XML string
4. Encode to PoB code → Send to PoB app → Get recalculated stats
"""

import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Set
import logging

logger = logging.getLogger(__name__)


class BuildModificationError(Exception):
    """Raised when build modification fails."""
    pass


def modify_passive_tree_nodes(
    xml: str,
    nodes_to_add: Optional[List[int]] = None,
    nodes_to_remove: Optional[List[int]] = None,
    mastery_effects_to_add: Optional[Dict[int, int]] = None
) -> str:
    """
    Add or remove passive tree nodes from a build.

    Args:
        xml: PoB build XML string
        nodes_to_add: List of node IDs to allocate
        nodes_to_remove: List of node IDs to deallocate
        mastery_effects_to_add: Dict of {mastery_node_id: effect_id} to add
            If not provided, mastery effects are automatically cleaned up

    Returns:
        Modified XML string

    Example:
        >>> xml = decode_pob_code(code)
        >>> # Remove node 12345, add nodes 23456 and 34567
        >>> modified = modify_passive_tree_nodes(xml, [23456, 34567], [12345])
        >>> new_code = encode_pob_code(modified)

    Note on Mastery Nodes:
        Mastery nodes are special nodes that allow selecting one of several effects.
        When removing a node with a mastery effect, its effect is automatically removed.
        When adding a mastery node, you must specify the effect in mastery_effects_to_add,
        otherwise NO effect will be selected (optimizer should handle this separately).
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise BuildModificationError(f"Invalid XML: {e}")

    nodes_to_add = set(nodes_to_add or [])
    nodes_to_remove = set(nodes_to_remove or [])
    mastery_effects_to_add = mastery_effects_to_add or {}

    # Find the Tree element
    tree_elem = root.find(".//Tree")
    if tree_elem is None:
        raise BuildModificationError("No <Tree> element found in build")

    # Get current spec (usually Spec with activeSpec="true")
    spec_elem = tree_elem.find(".//Spec[@activeSpec='true']")
    if spec_elem is None:
        # Fallback to first Spec
        spec_elem = tree_elem.find(".//Spec")
    if spec_elem is None:
        raise BuildModificationError("No <Spec> element found in tree")

    # Parse current allocated nodes
    current_nodes_str = spec_elem.get("nodes", "")
    if current_nodes_str:
        current_nodes = set(int(n) for n in current_nodes_str.split(",") if n.strip())
    else:
        current_nodes = set()

    # Parse current mastery effects
    # Format: "{nodeId,effectId},{nodeId,effectId},..."
    mastery_effects_str = spec_elem.get("masteryEffects", "")
    mastery_effects = _parse_mastery_effects(mastery_effects_str)

    logger.debug(f"Current nodes: {len(current_nodes)}")
    logger.debug(f"Current mastery effects: {len(mastery_effects)}")
    logger.debug(f"Adding: {nodes_to_add}")
    logger.debug(f"Removing: {nodes_to_remove}")

    # Apply node modifications
    current_nodes = (current_nodes | nodes_to_add) - nodes_to_remove

    # Handle mastery effects:
    # 1. Remove mastery effects for removed nodes
    for removed_node in nodes_to_remove:
        if removed_node in mastery_effects:
            logger.debug(f"Removing mastery effect for node {removed_node}")
            del mastery_effects[removed_node]

    # 2. Add new mastery effects (with validation)
    if mastery_effects_to_add:
        # Lazy import to avoid circular imports
        from .mastery_optimizer import get_mastery_database

        try:
            mastery_db = get_mastery_database()
        except Exception as e:
            logger.debug(f"Could not load mastery database for validation: {e}")
            mastery_db = None

        for node_id, effect_id in mastery_effects_to_add.items():
            if mastery_db is not None:
                mastery_node = mastery_db.get_mastery(node_id)
                if mastery_node is None:
                    logger.warning(
                        f"Mastery node {node_id} not found in database; "
                        f"applying effect {effect_id} anyway (database may be incomplete)"
                    )
                else:
                    valid_effect_ids = [e.effect_id for e in mastery_node.available_effects]
                    if effect_id not in valid_effect_ids:
                        logger.warning(
                            f"Effect {effect_id} is not valid for mastery node {node_id} "
                            f"({mastery_node.name}); valid effects: {valid_effect_ids}. "
                            f"Applying anyway (database may be incomplete)"
                        )

            mastery_effects[node_id] = effect_id

    # 3. Clean up orphaned mastery effects (mastery node not allocated)
    orphaned = set(mastery_effects.keys()) - current_nodes
    for orphaned_node in orphaned:
        logger.warning(f"Removing orphaned mastery effect for unallocated node {orphaned_node}")
        del mastery_effects[orphaned_node]

    # Update the XML
    spec_elem.set("nodes", ",".join(str(n) for n in sorted(current_nodes)))
    spec_elem.set("masteryEffects", _format_mastery_effects(mastery_effects))

    logger.info(
        f"Modified passive tree: {len(current_nodes)} nodes allocated, "
        f"{len(mastery_effects)} mastery effects"
    )

    return ET.tostring(root, encoding="unicode")


def modify_character_level(xml: str, new_level: int) -> str:
    """
    Change the character level.

    Args:
        xml: PoB build XML string
        new_level: New level (1-100)

    Returns:
        Modified XML string
    """
    if not 1 <= new_level <= 100:
        raise BuildModificationError(f"Invalid level: {new_level}. Must be 1-100.")

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise BuildModificationError(f"Invalid XML: {e}")

    # Modify Build element's level attribute
    build_elem = root.find("Build")
    if build_elem is None:
        raise BuildModificationError("No <Build> element found")

    old_level = build_elem.get("level", "unknown")
    build_elem.set("level", str(new_level))

    logger.info(f"Changed character level: {old_level} → {new_level}")

    return ET.tostring(root, encoding="unicode")


def modify_gem_level(
    xml: str,
    socket_group_index: int,
    gem_name: str,
    new_level: Optional[int] = None,
    new_quality: Optional[int] = None
) -> str:
    """
    Modify a gem's level and/or quality.

    Args:
        xml: PoB build XML string
        socket_group_index: Index of socket group (1-based)
        gem_name: Name of gem to modify (e.g., "Cyclone of Tumult")
        new_level: New gem level (1-21+)
        new_quality: New gem quality (0-23+)

    Returns:
        Modified XML string
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise BuildModificationError(f"Invalid XML: {e}")

    # Find the Skills section
    skills_elem = root.find("Skills")
    if skills_elem is None:
        raise BuildModificationError("No <Skills> element found")

    # Find the active skill set
    active_set_id = skills_elem.get("activeSkillSet", "1")
    skill_set = skills_elem.find(f".//SkillSet[@id='{active_set_id}']")
    if skill_set is None:
        raise BuildModificationError(f"No SkillSet with id={active_set_id} found")

    # Get all Skill elements
    skill_elements = list(skill_set.findall("Skill"))
    if socket_group_index < 1 or socket_group_index > len(skill_elements):
        raise BuildModificationError(
            f"Invalid socket group index: {socket_group_index}. "
            f"Build has {len(skill_elements)} socket groups."
        )

    skill_elem = skill_elements[socket_group_index - 1]

    # Find the gem
    gem_found = False
    for gem_elem in skill_elem.findall("Gem"):
        if gem_elem.get("nameSpec") == gem_name:
            if new_level is not None:
                old_level = gem_elem.get("level", "unknown")
                gem_elem.set("level", str(new_level))
                logger.debug(f"{gem_name} level: {old_level} → {new_level}")

            if new_quality is not None:
                old_quality = gem_elem.get("quality", "unknown")
                gem_elem.set("quality", str(new_quality))
                logger.debug(f"{gem_name} quality: {old_quality} → {new_quality}")

            gem_found = True
            break

    if not gem_found:
        raise BuildModificationError(
            f"Gem '{gem_name}' not found in socket group {socket_group_index}"
        )

    logger.info(f"Modified gem: {gem_name} in group {socket_group_index}")

    return ET.tostring(root, encoding="unicode")


def get_passive_tree_summary(xml: str) -> Dict:
    """
    Get summary information about the passive tree.

    Args:
        xml: PoB build XML string

    Returns:
        Dict with tree info: {
            'total_nodes': int,
            'allocated_nodes': Set[int],
            'mastery_effects': Dict[int, int],  # node_id -> effect_id
            'class_name': str,
            'ascendancy_name': str,
        }
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise BuildModificationError(f"Invalid XML: {e}")

    # Get class info from Build element
    build_elem = root.find("Build")
    class_name = build_elem.get("className", "Unknown") if build_elem else "Unknown"
    ascendancy_name = build_elem.get("ascendClassName", "None") if build_elem else "None"

    tree_elem = root.find(".//Tree")
    if tree_elem is None:
        return {
            'total_nodes': 0,
            'allocated_nodes': set(),
            'mastery_effects': {},
            'class_name': class_name,
            'ascendancy_name': ascendancy_name,
        }

    spec_elem = tree_elem.find(".//Spec[@activeSpec='true']") or tree_elem.find(".//Spec")
    if spec_elem is None:
        return {
            'total_nodes': 0,
            'allocated_nodes': set(),
            'mastery_effects': {},
            'class_name': class_name,
            'ascendancy_name': ascendancy_name,
            'tree_version': None,
        }

    nodes_str = spec_elem.get("nodes", "")
    allocated = set(int(n) for n in nodes_str.split(",") if n.strip())

    mastery_effects_str = spec_elem.get("masteryEffects", "")
    mastery_effects = _parse_mastery_effects(mastery_effects_str)

    return {
        'total_nodes': len(allocated),
        'allocated_nodes': allocated,
        'mastery_effects': mastery_effects,
        'class_name': class_name,
        'ascendancy_name': ascendancy_name,
        'tree_version': spec_elem.get("treeVersion"),
    }


def get_skill_groups_summary(xml: str) -> List[Dict]:
    """
    Get summary of all skill groups in the build.

    Args:
        xml: PoB build XML string

    Returns:
        List of dicts with skill group info
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise BuildModificationError(f"Invalid XML: {e}")

    skills_elem = root.find("Skills")
    if skills_elem is None:
        return []

    active_set_id = skills_elem.get("activeSkillSet", "1")
    skill_set = skills_elem.find(f".//SkillSet[@id='{active_set_id}']")
    if skill_set is None:
        return []

    result = []
    for idx, skill_elem in enumerate(skill_set.findall("Skill"), 1):
        gems = []
        for gem_elem in skill_elem.findall("Gem"):
            gems.append({
                'name': gem_elem.get("nameSpec", "Unknown"),
                'level': int(gem_elem.get("level", 1)),
                'quality': int(gem_elem.get("quality", 0)),
                'enabled': gem_elem.get("enabled", "true") == "true",
            })

        result.append({
            'index': idx,
            'slot': skill_elem.get("slot", "None"),
            'enabled': skill_elem.get("enabled", "true") == "true",
            'label': skill_elem.get("label"),
            'gems': gems,
        })

    return result


def _parse_mastery_effects(mastery_effects_str: str) -> Dict[int, int]:
    """
    Parse mastery effects string into dict.

    Format: "{nodeId,effectId},{nodeId,effectId},..."
    Example: "{53188,64875},{27872,29161}"

    Args:
        mastery_effects_str: Mastery effects string from XML

    Returns:
        Dict mapping node_id -> effect_id
    """
    if not mastery_effects_str or not mastery_effects_str.strip():
        return {}

    result = {}

    # Remove outer braces and split by },{
    pairs_str = mastery_effects_str.strip()
    if not pairs_str:
        return result

    # Split into individual {nodeId,effectId} pairs
    pairs = []
    current_pair = ""
    brace_count = 0

    for char in pairs_str:
        if char == '{':
            brace_count += 1
            if brace_count == 1:
                current_pair = ""
                continue
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                if current_pair:
                    pairs.append(current_pair)
                current_pair = ""
                continue

        if brace_count > 0:
            current_pair += char

    # Parse each pair
    for pair in pairs:
        parts = pair.split(',')
        if len(parts) == 2:
            try:
                node_id = int(parts[0].strip())
                effect_id = int(parts[1].strip())
                result[node_id] = effect_id
            except ValueError:
                logger.warning(f"Failed to parse mastery effect pair: {pair}")

    return result


def _format_mastery_effects(mastery_effects: Dict[int, int]) -> str:
    """
    Format mastery effects dict into XML string.

    Args:
        mastery_effects: Dict mapping node_id -> effect_id

    Returns:
        Formatted string: "{nodeId,effectId},{nodeId,effectId},..."
    """
    if not mastery_effects:
        return ""

    # Sort by node ID for consistency
    sorted_effects = sorted(mastery_effects.items())

    # Format as {nodeId,effectId} pairs
    pairs = [f"{{{node_id},{effect_id}}}" for node_id, effect_id in sorted_effects]

    return ",".join(pairs)

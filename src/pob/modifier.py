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
    nodes_to_remove: Optional[List[int]] = None
) -> str:
    """
    Add or remove passive tree nodes from a build.

    Args:
        xml: PoB build XML string
        nodes_to_add: List of node IDs to allocate
        nodes_to_remove: List of node IDs to deallocate

    Returns:
        Modified XML string

    Example:
        >>> xml = decode_pob_code(code)
        >>> # Remove node 12345, add nodes 23456 and 34567
        >>> modified = modify_passive_tree_nodes(xml, [23456, 34567], [12345])
        >>> new_code = encode_pob_code(modified)
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise BuildModificationError(f"Invalid XML: {e}")

    nodes_to_add = set(nodes_to_add or [])
    nodes_to_remove = set(nodes_to_remove or [])

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

    logger.debug(f"Current nodes: {len(current_nodes)}")
    logger.debug(f"Adding: {nodes_to_add}")
    logger.debug(f"Removing: {nodes_to_remove}")

    # Apply modifications
    current_nodes = (current_nodes | nodes_to_add) - nodes_to_remove

    # Update the XML
    spec_elem.set("nodes", ",".join(str(n) for n in sorted(current_nodes)))

    logger.info(f"Modified passive tree: {len(current_nodes)} nodes allocated")

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
            'class_name': class_name,
            'ascendancy_name': ascendancy_name,
        }

    spec_elem = tree_elem.find(".//Spec[@activeSpec='true']") or tree_elem.find(".//Spec")
    if spec_elem is None:
        return {
            'total_nodes': 0,
            'allocated_nodes': set(),
            'class_name': class_name,
            'ascendancy_name': ascendancy_name,
        }

    nodes_str = spec_elem.get("nodes", "")
    allocated = set(int(n) for n in nodes_str.split(",") if n.strip())

    return {
        'total_nodes': len(allocated),
        'allocated_nodes': allocated,
        'class_name': class_name,
        'ascendancy_name': ascendancy_name,
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

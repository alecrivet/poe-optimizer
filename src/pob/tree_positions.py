"""
Tree Position Parsing Module

Parses node X,Y coordinates from Path of Building tree data.
Nodes can be positioned either:
1. Directly via x,y coordinates
2. Via group + orbit + orbitIndex (computed from group position)

This module handles both cases and provides a unified position interface.
"""

import re
import math
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .tree_version import get_latest_tree_version

logger = logging.getLogger(__name__)


@dataclass
class NodePosition:
    """Represents a node position on the passive tree."""
    node_id: int
    x: float
    y: float
    group: int  # Node group ID
    orbit: int  # Orbit within group (0-6)
    orbit_index: int  # Position in orbit

    def distance_to(self, other: "NodePosition") -> float:
        """Calculate Euclidean distance to another node."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)


@dataclass
class GroupData:
    """Represents a group position and orbit configuration."""
    group_id: int
    x: float
    y: float
    orbits: List[int]  # Which orbits this group uses
    node_ids: List[int]  # Nodes belonging to this group


class TreePositionLoader:
    """
    Loads and calculates node positions from PoB tree.lua files.

    The passive tree uses a group/orbit system for node positioning:
    - Groups are located at specific x,y coordinates
    - Nodes within a group are placed on orbits (concentric circles)
    - Each orbit has a fixed number of positions (skillsPerOrbit)
    - Node position = group center + orbit offset based on orbitIndex

    Orbit configuration (from tree.lua constants):
    - skillsPerOrbit: [1, 6, 16, 16, 40, 72, 72] - positions per orbit
    - orbitRadii: [0, 82, 162, 335, 493, 662, 846] - radius of each orbit
    """

    # Default orbit configuration (from 3.27 tree.lua)
    DEFAULT_SKILLS_PER_ORBIT = [1, 6, 16, 16, 40, 72, 72]
    DEFAULT_ORBIT_RADII = [0, 82, 162, 335, 493, 662, 846]

    def __init__(self, tree_version: Optional[str] = None, pob_path: str = "./PathOfBuilding"):
        """
        Initialize with PoE tree version.

        Args:
            tree_version: Tree version string (e.g., "3_27").
                          If None, auto-detects latest from TreeData.
            pob_path: Path to PathOfBuilding installation
        """
        if tree_version is None:
            tree_version = get_latest_tree_version(pob_path) or "3_27"
        self.tree_version = tree_version
        self.pob_path = Path(pob_path)

        # Computed data
        self._positions: Optional[Dict[int, NodePosition]] = None
        self._groups: Optional[Dict[int, GroupData]] = None
        self._skills_per_orbit: List[int] = list(self.DEFAULT_SKILLS_PER_ORBIT)
        self._orbit_radii: List[int] = list(self.DEFAULT_ORBIT_RADII)

    def load_positions(self) -> Dict[int, NodePosition]:
        """
        Load all node positions from tree.lua.

        Returns:
            Dictionary mapping node_id -> NodePosition
        """
        if self._positions is not None:
            return self._positions

        tree_file = self.pob_path / "src" / "TreeData" / self.tree_version / "tree.lua"

        if not tree_file.exists():
            logger.warning(f"Tree file not found: {tree_file}")
            return {}

        logger.info(f"Loading tree positions from {tree_file}")

        with open(tree_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse constants first (orbit configuration)
        self._parse_constants(content)

        # Parse groups to get group positions
        self._groups = self._parse_groups(content)

        # Parse nodes and calculate positions
        self._positions = self._parse_nodes(content)

        logger.info(f"Loaded {len(self._positions)} node positions")
        return self._positions

    def get_position(self, node_id: int) -> Optional[NodePosition]:
        """
        Get position for a single node.

        Args:
            node_id: The node ID to look up

        Returns:
            NodePosition if found, None otherwise
        """
        positions = self.load_positions()
        return positions.get(node_id)

    def get_groups(self) -> Dict[int, GroupData]:
        """Get all parsed group data."""
        if self._groups is None:
            self.load_positions()
        return self._groups or {}

    def _parse_constants(self, content: str) -> None:
        """Parse orbit configuration constants from tree.lua."""
        # Parse skillsPerOrbit
        skills_match = re.search(
            r'\["skillsPerOrbit"\]\s*=\s*\{([^}]+)\}',
            content
        )
        if skills_match:
            skills_text = skills_match.group(1)
            skills = re.findall(r"(\d+)", skills_text)
            if skills:
                self._skills_per_orbit = [int(s) for s in skills]
                logger.debug(f"Parsed skillsPerOrbit: {self._skills_per_orbit}")

        # Parse orbitRadii
        radii_match = re.search(
            r'\["orbitRadii"\]\s*=\s*\{([^}]+)\}',
            content
        )
        if radii_match:
            radii_text = radii_match.group(1)
            radii = re.findall(r"(\d+)", radii_text)
            if radii:
                self._orbit_radii = [int(r) for r in radii]
                logger.debug(f"Parsed orbitRadii: {self._orbit_radii}")

    def _parse_groups(self, content: str) -> Dict[int, GroupData]:
        """Parse group definitions from tree.lua."""
        groups: Dict[int, GroupData] = {}

        # Find the groups section
        groups_match = re.search(r'\["groups"\]\s*=\s*\{', content)
        if not groups_match:
            logger.warning("Could not find groups section in tree.lua")
            return groups

        # Start after the ["groups"]= { marker
        groups_start = groups_match.end()

        # Find the end of groups section - the main nodes section has ["root"] right after
        # We need to find ["nodes"]= { followed by ["root"]
        main_nodes_match = re.search(r'\["nodes"\]\s*=\s*\{\s*\["root"\]', content[groups_start:])
        if main_nodes_match:
            groups_section = content[groups_start:groups_start + main_nodes_match.start()]
        else:
            # Fallback: find the last ["nodes"]= that's preceded by closing braces
            groups_section = content[groups_start:]

        # Split by group entries
        group_blocks = re.split(r"\[(\d+)\]\s*=\s*\{", groups_section)

        for i in range(1, len(group_blocks), 2):
            try:
                group_id = int(group_blocks[i])
                block_content = group_blocks[i + 1] if i + 1 < len(group_blocks) else ""

                # Parse x coordinate
                x_match = re.search(r'\["x"\]\s*=\s*([-\d.eE+]+)', block_content)
                y_match = re.search(r'\["y"\]\s*=\s*([-\d.eE+]+)', block_content)

                if not x_match or not y_match:
                    continue

                x = float(x_match.group(1))
                y = float(y_match.group(1))

                # Parse orbits
                orbits = []
                orbits_match = re.search(r'\["orbits"\]\s*=\s*\{([^}]*)\}', block_content)
                if orbits_match:
                    orbits_text = orbits_match.group(1)
                    orbits = [int(o) for o in re.findall(r"(\d+)", orbits_text)]

                # Parse node IDs
                node_ids = []
                nodes_match = re.search(r'\["nodes"\]\s*=\s*\{([^}]*)\}', block_content)
                if nodes_match:
                    nodes_text = nodes_match.group(1)
                    node_ids = [int(n) for n in re.findall(r'"(\d+)"', nodes_text)]

                groups[group_id] = GroupData(
                    group_id=group_id,
                    x=x,
                    y=y,
                    orbits=orbits,
                    node_ids=node_ids
                )

            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse group block: {e}")
                continue

        logger.info(f"Parsed {len(groups)} groups")
        return groups

    def _parse_nodes(self, content: str) -> Dict[int, NodePosition]:
        """Parse node definitions and calculate positions."""
        positions: Dict[int, NodePosition] = {}

        # Find the MAIN nodes section - it's followed by ["root"]
        # This distinguishes it from the ["nodes"] arrays within groups
        nodes_match = re.search(r'\["nodes"\]\s*=\s*\{\s*\["root"\]', content)
        if not nodes_match:
            logger.warning("Could not find main nodes section in tree.lua")
            return positions

        # Start just before ["root"]
        nodes_start = nodes_match.end() - len('["root"]')

        # Split by node definitions [nodeId]=
        node_blocks = re.split(r"\[(\d+)\]\s*=\s*\{", content[nodes_start:])

        parsed_count = 0

        for i in range(1, len(node_blocks), 2):
            try:
                node_id_str = node_blocks[i]
                block_content = node_blocks[i + 1] if i + 1 < len(node_blocks) else ""

                # Skip if not a skill node
                if '"skill"' not in block_content and '["skill"]' not in block_content:
                    continue

                node_id = int(node_id_str)

                # Extract group, orbit, orbitIndex
                group_match = re.search(r'\["group"\]\s*=\s*(\d+)', block_content)
                orbit_match = re.search(r'\["orbit"\]\s*=\s*(\d+)', block_content)
                orbit_index_match = re.search(r'\["orbitIndex"\]\s*=\s*(\d+)', block_content)

                if not all([group_match, orbit_match, orbit_index_match]):
                    continue

                group_id = int(group_match.group(1))
                orbit = int(orbit_match.group(1))
                orbit_index = int(orbit_index_match.group(1))

                # Calculate position
                x, y = self._calculate_node_position(group_id, orbit, orbit_index)

                if x is not None and y is not None:
                    positions[node_id] = NodePosition(
                        node_id=node_id,
                        x=x,
                        y=y,
                        group=group_id,
                        orbit=orbit,
                        orbit_index=orbit_index
                    )
                    parsed_count += 1

            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse node: {e}")
                continue

        logger.info(f"Calculated positions for {parsed_count} nodes")
        return positions

    def _calculate_node_position(
        self,
        group_id: int,
        orbit: int,
        orbit_index: int
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate x,y position from group/orbit/orbitIndex.

        The orbit system works like clock positions:
        - orbit 0: center (single position)
        - orbit 1-6: concentric rings with increasing positions

        Position is calculated as:
        x = group_x + radius * cos(angle)
        y = group_y + radius * sin(angle)
        """
        if self._groups is None or group_id not in self._groups:
            return None, None

        group = self._groups[group_id]

        # Get orbit radius
        if orbit >= len(self._orbit_radii):
            return None, None

        radius = self._orbit_radii[orbit]

        if radius == 0:
            # Center of group
            return group.x, group.y

        # Get number of positions in this orbit
        if orbit >= len(self._skills_per_orbit):
            return None, None

        skills_in_orbit = self._skills_per_orbit[orbit]

        if skills_in_orbit == 0:
            return group.x, group.y

        # Calculate angle (radians)
        angle = 2 * math.pi * orbit_index / skills_in_orbit

        # Apply rotation - PoE tree starts at top and goes clockwise
        angle = angle - math.pi / 2

        x = group.x + radius * math.cos(angle)
        y = group.y + radius * math.sin(angle)

        return x, y


# Singleton instance for caching
_loader_cache: Dict[str, TreePositionLoader] = {}


def get_position_loader(tree_version: Optional[str] = None) -> TreePositionLoader:
    """
    Get a cached TreePositionLoader instance.

    Args:
        tree_version: Tree version string. If None, auto-detects latest.

    Returns:
        TreePositionLoader instance (cached)
    """
    if tree_version is None:
        tree_version = get_latest_tree_version() or "3_27"
    if tree_version not in _loader_cache:
        _loader_cache[tree_version] = TreePositionLoader(tree_version)
    return _loader_cache[tree_version]


def load_tree_positions(tree_version: Optional[str] = None) -> Dict[int, NodePosition]:
    """
    Convenience function to load tree positions.

    Args:
        tree_version: Tree version string

    Returns:
        Dictionary mapping node_id -> NodePosition
    """
    loader = get_position_loader(tree_version)
    return loader.load_positions()

"""
Radius Calculator Module

Calculates which passive tree nodes fall within jewel radii.
Supports different radius sizes and ring calculations for Thread of Hope.
"""

import math
import logging
from typing import Dict, Set, Optional, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..tree_parser import PassiveTreeGraph

from ..tree_positions import NodePosition, TreePositionLoader, load_tree_positions

logger = logging.getLogger(__name__)


class RadiusCalculator:
    """
    Calculate which nodes fall within jewel radii.

    Jewels in Path of Exile affect nodes within a radius of their socket.
    Different jewel types have different radius sizes:
    - Small: 800 units
    - Medium: 1200 units
    - Large: 1800 units

    Thread of Hope is special - it affects nodes in a ring (between inner and outer radius).
    """

    # Radius thresholds (PoB distance units)
    SMALL_RADIUS = 800
    MEDIUM_RADIUS = 1200
    LARGE_RADIUS = 1800

    # Thread of Hope ring distances (inner/outer)
    THREAD_OF_HOPE_RINGS = {
        "Small": (800, 1000),
        "Medium": (1000, 1300),
        "Large": (1300, 1500),
        "Very Large": (1500, 1800),
    }

    def __init__(self, positions: Dict[int, NodePosition]):
        """
        Initialize with node positions.

        Args:
            positions: Dictionary mapping node_id -> NodePosition
        """
        self.positions = positions
        self._distance_cache: Dict[Tuple[int, int], float] = {}

    @classmethod
    def from_tree_version(cls, tree_version: Optional[str] = None) -> "RadiusCalculator":
        """
        Create RadiusCalculator from tree version.

        Args:
            tree_version: Tree version string (e.g., "3_28")

        Returns:
            RadiusCalculator instance
        """
        positions = load_tree_positions(tree_version)
        return cls(positions)

    def distance(self, node1_id: int, node2_id: int) -> float:
        """
        Calculate distance between two nodes.

        Uses caching for performance since distance calculations are symmetric.

        Args:
            node1_id: First node ID
            node2_id: Second node ID

        Returns:
            Distance in PoB units, or float(inf) if either node not found
        """
        cache_key = (min(node1_id, node2_id), max(node1_id, node2_id))
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]

        pos1 = self.positions.get(node1_id)
        pos2 = self.positions.get(node2_id)

        if pos1 is None or pos2 is None:
            return float("inf")

        dist = pos1.distance_to(pos2)
        self._distance_cache[cache_key] = dist
        return dist

    def get_nodes_in_radius(self, center_node_id: int, radius: int) -> Set[int]:
        """
        Get all nodes within radius of center node.

        Args:
            center_node_id: The node ID to measure from
            radius: Radius in PoB distance units

        Returns:
            Set of node IDs within the radius (excluding center)
        """
        center_pos = self.positions.get(center_node_id)
        if center_pos is None:
            logger.warning(f"Center node {center_node_id} not found in positions")
            return set()

        nodes_in_radius = set()
        radius_sq = radius * radius

        for node_id, pos in self.positions.items():
            if node_id == center_node_id:
                continue

            dx = pos.x - center_pos.x
            dy = pos.y - center_pos.y
            dist_sq = dx * dx + dy * dy

            if dist_sq <= radius_sq:
                nodes_in_radius.add(node_id)

        return nodes_in_radius

    def get_nodes_in_ring(
        self,
        center_node_id: int,
        inner_radius: int,
        outer_radius: int
    ) -> Set[int]:
        """
        Get nodes in ring (for Thread of Hope).

        Thread of Hope allows allocation of passives in a ring around
        the socket, but not the passives between the socket and the ring.

        Args:
            center_node_id: Socket node ID
            inner_radius: Inner edge of ring
            outer_radius: Outer edge of ring

        Returns:
            Set of node IDs in the ring
        """
        center_pos = self.positions.get(center_node_id)
        if center_pos is None:
            logger.warning(f"Center node {center_node_id} not found in positions")
            return set()

        nodes_in_ring = set()
        inner_sq = inner_radius * inner_radius
        outer_sq = outer_radius * outer_radius

        for node_id, pos in self.positions.items():
            if node_id == center_node_id:
                continue

            dx = pos.x - center_pos.x
            dy = pos.y - center_pos.y
            dist_sq = dx * dx + dy * dy

            if inner_sq <= dist_sq <= outer_sq:
                nodes_in_ring.add(node_id)

        return nodes_in_ring

    def get_thread_of_hope_nodes(
        self,
        socket_node_id: int,
        ring_size: str
    ) -> Set[int]:
        """
        Get nodes allocatable via Thread of Hope.

        Args:
            socket_node_id: Socket node ID where Thread of Hope is placed
            ring_size: One of "Small", "Medium", "Large", "Very Large"

        Returns:
            Set of node IDs in the Thread of Hope ring
        """
        if ring_size not in self.THREAD_OF_HOPE_RINGS:
            logger.warning(f"Unknown ring size: {ring_size}")
            return set()

        inner, outer = self.THREAD_OF_HOPE_RINGS[ring_size]
        return self.get_nodes_in_ring(socket_node_id, inner, outer)

    def precompute_socket_radii(
        self,
        socket_ids: Set[int]
    ) -> Dict[int, Dict[str, Set[int]]]:
        """
        Precompute radius nodes for all sockets.

        This is useful for optimization algorithms that need to
        quickly look up which nodes are affected by each socket.

        Args:
            socket_ids: Set of jewel socket node IDs

        Returns:
            Dict mapping socket_id -> radius_name -> Set[int]
        """
        result: Dict[int, Dict[str, Set[int]]] = {}

        for socket_id in socket_ids:
            socket_radii = {
                "small": self.get_nodes_in_radius(socket_id, self.SMALL_RADIUS),
                "medium": self.get_nodes_in_radius(socket_id, self.MEDIUM_RADIUS),
                "large": self.get_nodes_in_radius(socket_id, self.LARGE_RADIUS),
            }

            for ring_name, (inner, outer) in self.THREAD_OF_HOPE_RINGS.items():
                key = f"thread_{ring_name.lower().replace(' ', '_')}"
                socket_radii[key] = self.get_nodes_in_ring(socket_id, inner, outer)

            result[socket_id] = socket_radii

        return result

    def get_closest_socket(
        self,
        node_id: int,
        socket_ids: Set[int]
    ) -> Optional[Tuple[int, float]]:
        """
        Find the closest socket to a given node.

        Args:
            node_id: Target node ID
            socket_ids: Set of socket node IDs to consider

        Returns:
            Tuple of (socket_id, distance) or None if no valid socket found
        """
        node_pos = self.positions.get(node_id)
        if node_pos is None:
            return None

        closest_socket = None
        closest_dist = float("inf")

        for socket_id in socket_ids:
            dist = self.distance(node_id, socket_id)
            if dist < closest_dist:
                closest_dist = dist
                closest_socket = socket_id

        if closest_socket is None:
            return None

        return (closest_socket, closest_dist)

    def filter_by_node_type(
        self,
        node_ids: Set[int],
        tree_graph: "PassiveTreeGraph",
        node_types: List[str]
    ) -> Set[int]:
        """
        Filter nodes by type (notable, keystone, etc.).

        Args:
            node_ids: Set of node IDs to filter
            tree_graph: PassiveTreeGraph for node type lookup
            node_types: List of node types to include

        Returns:
            Filtered set of node IDs
        """
        filtered = set()
        for node_id in node_ids:
            node = tree_graph.get_node(node_id)
            if node and node.node_type in node_types:
                filtered.add(node_id)
        return filtered

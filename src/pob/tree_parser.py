"""
Passive Tree Graph Parser

Parses Path of Building's passive tree data to build a graph structure
that allows us to:
1. Find neighbors of allocated nodes
2. Validate tree connectivity
3. Identify candidate nodes for addition

The passive tree is a large graph with ~1,500 nodes connected by edges.
Each node has:
- ID (unique identifier)
- Name (display name)
- Stats (list of modifiers)
- Type (normal, notable, keystone, jewel socket, etc.)
- Connections (list of adjacent node IDs)
- Position (x, y coordinates)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PassiveNode:
    """Represents a single passive tree node."""

    node_id: int
    name: str
    stats: List[str]
    node_type: str  # 'normal', 'notable', 'keystone', 'jewel', 'ascendancy_start', 'mastery'
    connections: List[int]  # Adjacent node IDs
    x: float = 0.0
    y: float = 0.0
    is_ascendancy: bool = False
    ascendancy_name: Optional[str] = None
    is_mastery: bool = False

    def __repr__(self):
        return f"PassiveNode({self.node_id}, {self.name!r}, type={self.node_type})"


class PassiveTreeGraph:
    """
    Graph representation of the passive skill tree.

    Provides efficient access to nodes and their neighbors for optimization algorithms.
    """

    def __init__(self):
        self.nodes: Dict[int, PassiveNode] = {}
        self.tree_version: Optional[str] = None
        self.class_start_nodes: Dict[str, int] = {}

    def add_node(self, node: PassiveNode):
        """Add a node to the graph."""
        self.nodes[node.node_id] = node

    def get_node(self, node_id: int) -> Optional[PassiveNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: int) -> List[int]:
        """Get all nodes connected to this node."""
        node = self.get_node(node_id)
        if node:
            return node.connections
        return []

    def find_unallocated_neighbors(
        self,
        allocated_nodes: Set[int]
    ) -> Set[int]:
        """
        Find all unallocated nodes that are adjacent to the current tree.

        These are candidates for addition.

        Args:
            allocated_nodes: Set of currently allocated node IDs

        Returns:
            Set of node IDs that are neighbors of allocated nodes but not allocated
        """
        candidates = set()

        for node_id in allocated_nodes:
            neighbors = self.get_neighbors(node_id)
            for neighbor_id in neighbors:
                if neighbor_id not in allocated_nodes:
                    candidates.add(neighbor_id)

        return candidates

    def is_path_connected(
        self,
        start_node: int,
        allocated_nodes: Set[int]
    ) -> bool:
        """
        Check if all allocated nodes form a connected path from start_node.

        Uses BFS to verify connectivity.

        Args:
            start_node: Starting position (class start node)
            allocated_nodes: Set of allocated node IDs

        Returns:
            True if all nodes are reachable from start_node
        """
        if not allocated_nodes:
            return True

        if start_node not in allocated_nodes:
            # Start node should always be allocated
            return False

        # BFS from start_node
        visited = {start_node}
        queue = [start_node]

        while queue:
            current = queue.pop(0)
            neighbors = self.get_neighbors(current)

            for neighbor_id in neighbors:
                if neighbor_id in allocated_nodes and neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)

        # All allocated nodes should be reachable
        return visited == allocated_nodes

    def get_shortest_path(
        self,
        from_node: int,
        to_node: int,
        allocated_nodes: Set[int]
    ) -> Optional[List[int]]:
        """
        Find shortest path between two nodes, preferring allocated nodes.

        Uses BFS with cost (unallocated nodes have cost 1, allocated have cost 0).

        Args:
            from_node: Starting node ID
            to_node: Target node ID
            allocated_nodes: Currently allocated nodes

        Returns:
            List of node IDs forming the path, or None if no path exists
        """
        if from_node == to_node:
            return [from_node]

        # Simple BFS for now (can optimize with A* later)
        visited = {from_node}
        queue = [(from_node, [from_node])]

        while queue:
            current, path = queue.pop(0)
            neighbors = self.get_neighbors(current)

            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    new_path = path + [neighbor_id]

                    if neighbor_id == to_node:
                        return new_path

                    visited.add(neighbor_id)
                    queue.append((neighbor_id, new_path))

        return None  # No path found

    def count_nodes(self) -> int:
        """Get total number of nodes in tree."""
        return len(self.nodes)

    def get_keystones(self) -> List[PassiveNode]:
        """Get all keystone nodes."""
        return [node for node in self.nodes.values() if node.node_type == 'keystone']

    def get_notables(self) -> List[PassiveNode]:
        """Get all notable nodes."""
        return [node for node in self.nodes.values() if node.node_type == 'notable']

    def get_jewel_sockets(self) -> List[PassiveNode]:
        """Get all jewel socket nodes."""
        return [node for node in self.nodes.values() if node.node_type == 'jewel']


class TreeParser:
    """
    Parser for Path of Building passive tree data.

    Loads tree structure from PoB's Data/ directory and builds a graph.
    """

    def __init__(self, pob_path: str = "./PathOfBuilding"):
        self.pob_path = Path(pob_path)
        self.tree_cache: Optional[PassiveTreeGraph] = None

    def load_tree(self, tree_version: str = "3_27") -> PassiveTreeGraph:
        """
        Load passive tree for a specific game version.

        Args:
            tree_version: Tree version (e.g., "3_27" for PoE 3.27)

        Returns:
            PassiveTreeGraph with all nodes and connections
        """
        if self.tree_cache and self.tree_cache.tree_version == tree_version:
            logger.info(f"Using cached tree version {tree_version}")
            return self.tree_cache

        logger.info(f"Loading passive tree version {tree_version}...")

        # TODO: Once PathOfBuilding submodule is loaded, parse actual tree data
        # For now, return an empty graph as a placeholder

        tree_file = self.pob_path / "Data" / tree_version / "tree.json"

        if not tree_file.exists():
            logger.warning(f"Tree file not found: {tree_file}")
            logger.warning("PathOfBuilding submodule may not be loaded yet")
            logger.warning("Returning empty graph - node addition will not work")

            graph = PassiveTreeGraph()
            graph.tree_version = tree_version
            return graph

        # Parse tree data
        graph = self._parse_tree_file(tree_file)
        graph.tree_version = tree_version

        self.tree_cache = graph
        logger.info(f"Loaded {graph.count_nodes()} nodes from tree version {tree_version}")

        return graph

    def _parse_tree_file(self, tree_file: Path) -> PassiveTreeGraph:
        """
        Parse tree JSON file into graph structure.

        PoB tree format (from PathOfBuilding/Data/):
        - nodes: Dict of node_id -> node_data
        - groups: Visual groupings
        - classes: Starting positions
        """
        graph = PassiveTreeGraph()

        with open(tree_file, 'r', encoding='utf-8') as f:
            tree_data = json.load(f)

        # TODO: Implement actual parsing logic
        # This will parse PoB's tree format and build PassiveNode objects

        return graph


# Singleton instance for easy access
_tree_parser: Optional[TreeParser] = None


def get_tree_parser() -> TreeParser:
    """Get the global tree parser instance."""
    global _tree_parser
    if _tree_parser is None:
        _tree_parser = TreeParser()
    return _tree_parser


def load_passive_tree(tree_version: str = "3_27") -> PassiveTreeGraph:
    """
    Convenience function to load the passive tree.

    Args:
        tree_version: Tree version (e.g., "3_27")

    Returns:
        PassiveTreeGraph instance
    """
    parser = get_tree_parser()
    return parser.load_tree(tree_version)

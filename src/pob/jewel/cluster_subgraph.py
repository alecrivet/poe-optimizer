"""
Cluster Subgraph Modeling

This module models cluster jewel subgraphs for optimization purposes.
Cluster jewels create dynamic subgraphs attached to the passive tree.

Key concepts:
- ClusterNode: A single node within a cluster subgraph
- ClusterSubgraph: The full subgraph structure with pathing information
- ClusterSubgraphBuilder: Constructs subgraphs from jewels and build data

Node ID Encoding (from PoB PassiveSpec.lua):
- Bits 0-3:  Node index (0-11)
- Bits 4-5:  Group size (0=Small, 1=Medium, 2=Large)
- Bits 6-8:  Large socket index (0-5)
- Bits 9-10: Medium socket index (0-2)
- Bit 16:    Signal bit (always 1)
"""

import re
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Set, Optional, Tuple, TYPE_CHECKING

from .cluster import ClusterJewel, ClusterJewelSize, CLUSTER_NODE_MIN_ID, decode_cluster_node_id

if TYPE_CHECKING:
    from ..tree_parser import PassiveTreeGraph


@dataclass
class ClusterNode:
    """
    Represents a single node within a cluster jewel subgraph.

    Cluster nodes are dynamically generated when a cluster jewel is socketed.
    They have special IDs >= 65536 and exist in a tree-like subgraph structure.

    Attributes:
        node_id: Unique identifier (>= 65536 for cluster nodes)
        name: Display name of the passive node
        is_notable: True if this is a notable passive (stronger effect)
        is_socket: True if this node can socket another cluster jewel
        stats: List of stat modifiers this node grants
        connections: Set of connected node IDs within the subgraph
    """
    node_id: int
    name: str
    is_notable: bool = False
    is_socket: bool = False
    stats: List[str] = field(default_factory=list)
    connections: Set[int] = field(default_factory=set)

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ClusterNode):
            return False
        return self.node_id == other.node_id


@dataclass
class ClusterSubgraph:
    """
    Represents a complete cluster jewel subgraph structure.

    A cluster subgraph is a tree of nodes attached to the main passive tree
    at a socket node. It contains:
    - Small passives (basic stats from the cluster enchant)
    - Notable passives (powerful named passives)
    - Nested sockets (for medium/small cluster jewels)

    The structure is always rooted at the socket_node, which is the
    entry point from the main tree.

    Attributes:
        jewel: The ClusterJewel that created this subgraph
        socket_node: Entry point node ID from main tree
        nodes: Dict mapping node_id to ClusterNode
        notables: List of notable node IDs
        small_passives: List of small passive node IDs
        nested_sockets: List of nested socket node IDs
    """
    jewel: ClusterJewel
    socket_node: int
    nodes: Dict[int, ClusterNode] = field(default_factory=dict)
    notables: List[int] = field(default_factory=list)
    small_passives: List[int] = field(default_factory=list)
    nested_sockets: List[int] = field(default_factory=list)

    def get_paths_to_notable(self, notable_id: int) -> List[List[int]]:
        """
        Get all paths from socket to a notable.

        Uses BFS to find all shortest paths from the socket node to the
        specified notable. In cluster jewels, there is typically one path,
        but the structure allows for branching.

        Args:
            notable_id: The target notable node ID

        Returns:
            List of paths, where each path is a list of node IDs
            from socket to notable (inclusive)
        """
        if notable_id not in self.nodes:
            return []

        if notable_id == self.socket_node:
            return [[notable_id]]

        # BFS to find all shortest paths
        queue: deque[Tuple[int, List[int]]] = deque([(self.socket_node, [self.socket_node])])
        visited_at_depth: Dict[int, int] = {self.socket_node: 0}
        all_paths: List[List[int]] = []
        target_depth: Optional[int] = None

        while queue:
            current, path = queue.popleft()
            current_depth = len(path) - 1

            # If we have found paths and are past target depth, stop
            if target_depth is not None and current_depth > target_depth:
                break

            node = self.nodes.get(current)
            if not node:
                continue

            for neighbor_id in node.connections:
                if neighbor_id not in self.nodes:
                    continue

                new_path = path + [neighbor_id]
                new_depth = len(new_path) - 1

                if neighbor_id == notable_id:
                    if target_depth is None:
                        target_depth = new_depth
                    if new_depth == target_depth:
                        all_paths.append(new_path)
                elif neighbor_id not in visited_at_depth or visited_at_depth[neighbor_id] >= new_depth:
                    visited_at_depth[neighbor_id] = new_depth
                    queue.append((neighbor_id, new_path))

        return all_paths

    def get_minimum_allocation(self, notables: Set[int]) -> Set[int]:
        """
        Get minimum nodes needed to allocate given notables.

        Computes the Steiner tree - the minimum set of nodes that connects
        the socket to all specified notables.

        Args:
            notables: Set of notable node IDs to allocate

        Returns:
            Set of all node IDs needed (including path nodes and notables)
        """
        if not notables:
            return {self.socket_node}

        # Validate all notables exist
        valid_notables = notables & set(self.nodes.keys())
        if not valid_notables:
            return {self.socket_node}

        # For small sets, we can compute optimal Steiner tree
        # For larger sets, use greedy approximation
        if len(valid_notables) <= 4:
            return self._steiner_tree_exact(valid_notables)
        else:
            return self._steiner_tree_greedy(valid_notables)

    def _steiner_tree_exact(self, notables: Set[int]) -> Set[int]:
        """Compute exact Steiner tree for small notable sets."""
        # Get paths to each notable
        notable_paths: Dict[int, List[List[int]]] = {}
        for notable_id in notables:
            paths = self.get_paths_to_notable(notable_id)
            if paths:
                notable_paths[notable_id] = paths

        if len(notable_paths) != len(notables):
            # Some notables unreachable
            return {self.socket_node}

        # Try all combinations of paths
        best_allocation: Set[int] = set()
        best_cost = float('inf')

        # Generate all path combinations
        path_options = list(notable_paths.values())

        def try_combinations(index: int, current_nodes: Set[int]) -> None:
            nonlocal best_allocation, best_cost

            if index == len(path_options):
                if len(current_nodes) < best_cost:
                    best_cost = len(current_nodes)
                    best_allocation = current_nodes.copy()
                return

            for path in path_options[index]:
                new_nodes = current_nodes | set(path)
                if len(new_nodes) < best_cost:  # Prune
                    try_combinations(index + 1, new_nodes)

        try_combinations(0, {self.socket_node})
        return best_allocation

    def _steiner_tree_greedy(self, notables: Set[int]) -> Set[int]:
        """Greedy approximation for larger notable sets."""
        allocated: Set[int] = {self.socket_node}
        remaining = set(notables)

        while remaining:
            # Find notable with shortest path to current allocation
            best_notable = None
            best_path: List[int] = []
            best_new_nodes = float('inf')

            for notable_id in remaining:
                paths = self.get_paths_to_notable(notable_id)
                for path in paths:
                    # Count how many new nodes this path adds
                    new_nodes = len(set(path) - allocated)
                    if new_nodes < best_new_nodes:
                        best_new_nodes = new_nodes
                        best_notable = notable_id
                        best_path = path

            if best_notable is None:
                break

            allocated.update(best_path)
            remaining.remove(best_notable)

        return allocated

    def get_allocation_cost(self, notables: Set[int]) -> int:
        """
        Get point cost for allocating given notables.

        This is the total number of nodes that need to be allocated,
        including the path nodes to reach the notables.

        Args:
            notables: Set of notable node IDs to allocate

        Returns:
            Number of passive points needed
        """
        allocation = self.get_minimum_allocation(notables)
        # Do not count socket node as it is already allocated
        return len(allocation) - 1 if self.socket_node in allocation else len(allocation)

    def is_valid_allocation(self, nodes: Set[int]) -> bool:
        """
        Check if allocation is connected to socket.

        A valid allocation must form a connected subgraph that includes
        the socket node (entry point).

        Args:
            nodes: Set of allocated node IDs to validate

        Returns:
            True if all nodes are reachable from socket_node
        """
        if not nodes:
            return True

        if self.socket_node not in nodes:
            return False

        # BFS from socket to verify connectivity
        visited: Set[int] = {self.socket_node}
        queue: deque[int] = deque([self.socket_node])

        while queue:
            current = queue.popleft()
            node = self.nodes.get(current)
            if not node:
                continue

            for neighbor_id in node.connections:
                if neighbor_id in nodes and neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)

        return visited == nodes

    def get_allocated_notables(self, allocated_nodes: Set[int]) -> Set[int]:
        """Get which notables are currently allocated."""
        return set(self.notables) & allocated_nodes

    def get_unallocated_notables(self, allocated_nodes: Set[int]) -> Set[int]:
        """Get which notables are not currently allocated."""
        return set(self.notables) - allocated_nodes


def encode_cluster_node_id(
    node_index: int,
    size_index: int,
    large_socket_index: int = 0,
    medium_socket_index: int = 0
) -> int:
    """
    Encode cluster node components into a node ID.

    This is the inverse of decode_cluster_node_id.

    Args:
        node_index: Node index within cluster (0-11)
        size_index: Size (0=Small, 1=Medium, 2=Large)
        large_socket_index: Large socket index (0-5)
        medium_socket_index: Medium socket index (0-2)

    Returns:
        Encoded node ID (>= 65536)
    """
    base_id = (
        (node_index & 0xF) |
        ((size_index & 0x3) << 4) |
        ((large_socket_index & 0x7) << 6) |
        ((medium_socket_index & 0x3) << 9)
    )
    return CLUSTER_NODE_MIN_ID + base_id


class ClusterSubgraphBuilder:
    """
    Builds ClusterSubgraph models from cluster jewels and build data.

    This builder can construct subgraph models either from:
    1. A ClusterJewel with a set of allocated nodes
    2. PoB build XML with detailed node information

    The resulting subgraph can be used for optimization decisions.
    """

    def build_from_jewel(
        self,
        cluster: ClusterJewel,
        allocated_nodes: Set[int]
    ) -> ClusterSubgraph:
        """
        Build subgraph model from cluster jewel and allocated nodes.

        This method infers the subgraph structure from the cluster jewel
        properties and which nodes are currently allocated.

        Args:
            cluster: The ClusterJewel to model
            allocated_nodes: Set of currently allocated node IDs

        Returns:
            ClusterSubgraph model with inferred structure
        """
        socket_node = cluster.socket_node_id or 0

        # Filter to only cluster nodes related to this jewel
        cluster_allocated = {
            node_id for node_id in allocated_nodes
            if node_id >= CLUSTER_NODE_MIN_ID
        }

        # Build nodes dict
        nodes: Dict[int, ClusterNode] = {}
        notables: List[int] = []
        small_passives: List[int] = []
        nested_sockets: List[int] = []

        # Add socket node
        if socket_node > 0:
            nodes[socket_node] = ClusterNode(
                node_id=socket_node,
                name="Cluster Entry",
                is_socket=False,  # Entry point, not a nested socket
                connections=set()
            )

        # Infer structure from allocated nodes
        # Cluster nodes are arranged in a specific pattern based on size
        size_index = cluster.size.size_index

        # Decode each allocated node to understand structure
        for node_id in cluster_allocated:
            try:
                decoded = decode_cluster_node_id(node_id)

                # Determine node type based on position
                node_index = decoded['node_index']

                # Notable positions depend on cluster size
                is_notable = self._is_notable_position(node_index, cluster.size)
                is_nested_socket = self._is_socket_position(node_index, cluster.size)

                node = ClusterNode(
                    node_id=node_id,
                    name=f"Cluster Node {node_index}",
                    is_notable=is_notable,
                    is_socket=is_nested_socket,
                    connections=set()
                )
                nodes[node_id] = node

                if is_notable:
                    notables.append(node_id)
                elif is_nested_socket:
                    nested_sockets.append(node_id)
                else:
                    small_passives.append(node_id)

            except ValueError:
                # Not a valid cluster node ID
                continue

        # Build connections between nodes
        self._infer_connections(nodes, socket_node, cluster.size)

        return ClusterSubgraph(
            jewel=cluster,
            socket_node=socket_node,
            nodes=nodes,
            notables=notables,
            small_passives=small_passives,
            nested_sockets=nested_sockets
        )

    def build_from_xml(
        self,
        build_xml: str,
        cluster: ClusterJewel
    ) -> ClusterSubgraph:
        """
        Build subgraph with node details from PoB XML.

        This method extracts detailed node information from the build XML,
        including node names, stats, and connections.

        Args:
            build_xml: Full PoB build XML string
            cluster: The ClusterJewel to build subgraph for

        Returns:
            ClusterSubgraph model with full node details
        """
        socket_node = cluster.socket_node_id or 0

        try:
            root = ET.fromstring(build_xml)
        except ET.ParseError:
            # Fall back to basic inference
            return self.build_from_jewel(cluster, set())

        # Parse allocated nodes from Tree spec
        allocated_nodes: Set[int] = set()
        tree_elem = root.find(".//Tree")
        if tree_elem is not None:
            spec_elem = tree_elem.find(".//Spec[@activeSpec='true']")
            if spec_elem is None:
                spec_elem = tree_elem.find(".//Spec")
            if spec_elem is not None:
                nodes_str = spec_elem.get("nodes", "")
                if nodes_str:
                    allocated_nodes = {
                        int(n) for n in nodes_str.split(",") if n.strip()
                    }

        # Build basic structure first
        subgraph = self.build_from_jewel(cluster, allocated_nodes)

        # Enhance with notable names from jewel
        if cluster.notables:
            for i, notable_id in enumerate(subgraph.notables):
                if i < len(cluster.notables):
                    if notable_id in subgraph.nodes:
                        subgraph.nodes[notable_id].name = cluster.notables[i]

        return subgraph

    def _is_notable_position(self, node_index: int, size: ClusterJewelSize) -> bool:
        """
        Determine if a node index is a notable position.

        Notable positions in cluster jewels:
        - Large (8 nodes): positions 4, 6
        - Large (12 nodes): positions 4, 6, 10
        - Medium (4 nodes): position 2
        - Medium (6 nodes): positions 2, 4
        - Small (2-3 nodes): position 1 or 2
        """
        if size == ClusterJewelSize.LARGE:
            return node_index in {4, 6, 10}
        elif size == ClusterJewelSize.MEDIUM:
            return node_index in {2, 4}
        else:  # SMALL
            return node_index in {1, 2}

    def _is_socket_position(self, node_index: int, size: ClusterJewelSize) -> bool:
        """
        Determine if a node index is a socket position.

        Socket positions for nested cluster jewels:
        - Large: positions 2, 8 (for medium clusters)
        - Medium: position 3 (for small clusters)
        - Small: no sockets
        """
        if size == ClusterJewelSize.LARGE:
            return node_index in {2, 8}
        elif size == ClusterJewelSize.MEDIUM:
            return node_index == 3
        else:  # SMALL
            return False

    def _infer_connections(
        self,
        nodes: Dict[int, ClusterNode],
        socket_node: int,
        size: ClusterJewelSize
    ) -> None:
        """
        Infer connections between cluster nodes.

        Cluster nodes form a tree structure from the entry socket.
        The exact structure depends on the cluster size.
        """
        if not nodes:
            return

        # Get node IDs sorted by node_index
        node_list = []
        for node_id, node in nodes.items():
            if node_id >= CLUSTER_NODE_MIN_ID:
                try:
                    decoded = decode_cluster_node_id(node_id)
                    node_list.append((decoded['node_index'], node_id))
                except ValueError:
                    continue

        node_list.sort()

        if not node_list:
            return

        # Connect socket to first node
        first_node_id = node_list[0][1] if node_list else None
        if socket_node > 0 and first_node_id and socket_node in nodes:
            nodes[socket_node].connections.add(first_node_id)
            if first_node_id in nodes:
                nodes[first_node_id].connections.add(socket_node)

        # Connect sequential nodes (simplified linear structure)
        for i in range(len(node_list) - 1):
            current_id = node_list[i][1]
            next_id = node_list[i + 1][1]

            if current_id in nodes and next_id in nodes:
                nodes[current_id].connections.add(next_id)
                nodes[next_id].connections.add(current_id)


def get_cluster_nodes_for_jewel(
    cluster: ClusterJewel,
    allocated_nodes: Set[int]
) -> Set[int]:
    """
    Get all cluster node IDs that belong to a specific jewel.

    This filters allocated nodes to only those that belong to the
    cluster subgraph based on the socket encoding.

    Args:
        cluster: The ClusterJewel to get nodes for
        allocated_nodes: Set of all allocated node IDs

    Returns:
        Set of cluster node IDs belonging to this jewel
    """
    if not cluster.socket_node_id:
        return set()

    # Cluster nodes for this jewel should share the same socket indices
    socket_id = cluster.socket_node_id
    if socket_id < CLUSTER_NODE_MIN_ID:
        # Socket is on main tree (outer socket)
        # All cluster nodes with matching large_socket_index belong here
        return {
            node_id for node_id in allocated_nodes
            if node_id >= CLUSTER_NODE_MIN_ID
        }

    # Socket is nested - decode to find matching nodes
    try:
        socket_decoded = decode_cluster_node_id(socket_id)
    except ValueError:
        return set()

    result = set()
    for node_id in allocated_nodes:
        if node_id < CLUSTER_NODE_MIN_ID:
            continue
        try:
            decoded = decode_cluster_node_id(node_id)
            # Check if indices match for nested clusters
            if (decoded['large_socket_index'] == socket_decoded['large_socket_index'] and
                decoded['medium_socket_index'] == socket_decoded['medium_socket_index']):
                result.add(node_id)
        except ValueError:
            continue

    return result

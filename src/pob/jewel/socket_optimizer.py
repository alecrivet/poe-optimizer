"""
Jewel Socket Optimization Module

Handles intelligent placement of jewels across different socket types while
respecting jewel-specific constraints (timeless immutability, cluster sizing).
"""

from enum import Enum
from dataclasses import dataclass
from typing import Set, Dict, List, Optional, Tuple
from .base import BaseJewel, JewelCategory
from .timeless import TimelessJewel
from .cluster import ClusterJewel, ClusterJewelSize
from .unique import UniqueJewel


class SocketType(Enum):
    """Types of jewel sockets on the passive tree."""
    REGULAR = "regular"              # Standard jewel socket (unique/rare jewels)
    LARGE_CLUSTER = "large_cluster"  # Outer rim socket for large clusters
    MEDIUM_CLUSTER = "medium_cluster" # Socket created by large cluster
    SMALL_CLUSTER = "small_cluster"   # Socket created by medium cluster


@dataclass
class JewelSocket:
    """
    Represents a jewel socket on the passive tree.

    Attributes:
        node_id: Passive tree node ID
        socket_type: Type of socket (regular, cluster, etc.)
        is_allocated: Whether the socket node is currently allocated
        is_outer_rim: Whether socket is on the outer edge of tree
        distance_from_start: Minimum point cost to reach from starting class
        position: (x, y) coordinates on tree (optional, for radius calculations)
    """
    node_id: int
    socket_type: SocketType
    is_allocated: bool = False
    is_outer_rim: bool = False
    distance_from_start: Optional[int] = None
    position: Optional[Tuple[float, float]] = None

    def can_hold_jewel(self, jewel: BaseJewel) -> bool:
        """Check if this socket can hold the given jewel."""
        if jewel.category == JewelCategory.TIMELESS:
            # Timeless jewels are location-specific, handled separately
            return False

        if jewel.category == JewelCategory.CLUSTER:
            cluster = jewel
            # Cluster jewels must match socket type
            if cluster.size == ClusterJewelSize.LARGE:
                return self.socket_type == SocketType.LARGE_CLUSTER
            elif cluster.size == ClusterJewelSize.MEDIUM:
                return self.socket_type == SocketType.MEDIUM_CLUSTER
            elif cluster.size == ClusterJewelSize.SMALL:
                return self.socket_type == SocketType.SMALL_CLUSTER

        # Unique and rare jewels can go in any regular socket
        return self.socket_type == SocketType.REGULAR


@dataclass
class JewelAssignment:
    """
    Represents an assignment of a jewel to a socket.

    Attributes:
        jewel: The jewel being assigned
        socket_node_id: The socket node ID where jewel is placed
        can_move: Whether this jewel can be reassigned (False for timeless)
        original_socket_id: The socket where jewel was originally placed
        move_cost: Point cost to move to this socket (0 if already allocated)
    """
    jewel: BaseJewel
    socket_node_id: int
    can_move: bool
    original_socket_id: Optional[int]
    move_cost: int = 0

    @property
    def is_timeless(self) -> bool:
        """Check if this is a timeless jewel (immutable)."""
        return isinstance(self.jewel, TimelessJewel)

    @property
    def is_cluster(self) -> bool:
        """Check if this is a cluster jewel."""
        return isinstance(self.jewel, ClusterJewel)


class SocketDiscovery:
    """
    Discovers and classifies all jewel sockets on the passive tree.
    """

    # Known outer rim large cluster socket node IDs (from PoB data)
    # These are the sockets on the edge of the tree that can hold large clusters
    OUTER_RIM_SOCKETS = {
        2491,   # Top-right outer socket
        6230,   # Top-left outer socket
        7960,   # Left outer socket
        12613,  # Bottom-left outer socket
        26725,  # Right outer socket
        33631,  # Bottom outer socket
        36634,  # Top outer socket
        41263,  # Bottom-right outer socket
        46519,  # Right-center outer socket
        54127,  # Top-right outer socket
        61419,  # Left-center outer socket
    }

    def __init__(self, tree_graph):
        """
        Initialize socket discovery.

        Args:
            tree_graph: PassiveTreeGraph instance
        """
        self.tree_graph = tree_graph
        self._socket_cache: Optional[Dict[int, JewelSocket]] = None

    def discover_all_sockets(self) -> Dict[int, JewelSocket]:
        """
        Discover all jewel sockets on the passive tree.

        Returns:
            Dictionary mapping node_id -> JewelSocket
        """
        if self._socket_cache is not None:
            return self._socket_cache

        sockets = {}

        for node_id, node_data in self.tree_graph.nodes.items():
            # Check if node is a jewel socket
            if not self._is_jewel_socket_node(node_data):
                continue

            # Classify socket type
            socket_type = self._classify_socket_type(node_id, node_data)

            # Create socket object
            socket = JewelSocket(
                node_id=node_id,
                socket_type=socket_type,
                is_outer_rim=(node_id in self.OUTER_RIM_SOCKETS),
                position=self._get_node_position(node_data),
            )

            sockets[node_id] = socket

        self._socket_cache = sockets
        return sockets

    def _is_jewel_socket_node(self, node_data) -> bool:
        """Check if a node is a jewel socket.

        Args:
            node_data: Either a dict or a PassiveNode object
        """
        # Handle PassiveNode objects (from load_passive_tree)
        if hasattr(node_data, 'node_type'):
            return node_data.node_type == 'jewel'

        # Handle dict format (legacy or test mocks)
        if isinstance(node_data, dict):
            return node_data.get('isJewelSocket', False) or \
                   node_data.get('is', '') == 'JewelSocket' or \
                   node_data.get('node_type', '') == 'jewel' or \
                   'JewelSocket' in node_data.get('name', '')

        return False

    def _classify_socket_type(self, node_id: int, node_data) -> SocketType:
        """
        Classify the type of jewel socket.

        Args:
            node_id: Socket node ID
            node_data: Either a dict or a PassiveNode object

        Returns:
            SocketType classification
        """
        # Cluster nodes have IDs >= 65536
        if node_id >= 65536:
            # Determine cluster size based on node properties or ID range
            # This is a simplified classification - actual logic may vary
            if node_id < 70000:
                return SocketType.LARGE_CLUSTER
            elif node_id < 75000:
                return SocketType.MEDIUM_CLUSTER
            else:
                return SocketType.SMALL_CLUSTER

        # Outer rim sockets can hold large clusters
        if node_id in self.OUTER_RIM_SOCKETS:
            return SocketType.LARGE_CLUSTER

        # Default to regular socket
        return SocketType.REGULAR

    def _get_node_position(self, node_data) -> Optional[Tuple[float, float]]:
        """Extract (x, y) position from node data.

        Args:
            node_data: Either a dict or a PassiveNode object
        """
        # Handle PassiveNode objects
        if hasattr(node_data, 'x') and hasattr(node_data, 'y'):
            return (float(node_data.x), float(node_data.y))

        # Handle dict format
        if isinstance(node_data, dict):
            x = node_data.get('x') or node_data.get('group', {}).get('x')
            y = node_data.get('y') or node_data.get('group', {}).get('y')
            if x is not None and y is not None:
                return (float(x), float(y))

        return None

    def find_compatible_sockets(
        self,
        jewel: BaseJewel,
        occupied_sockets: Set[int],
        include_empty: bool = True
    ) -> Set[int]:
        """
        Find all sockets compatible with the given jewel.

        Args:
            jewel: Jewel to find sockets for
            occupied_sockets: Set of socket node IDs that currently hold jewels
            include_empty: If True, include unoccupied sockets in results.
                          If False, only return sockets that are currently occupied.

        Returns:
            Set of compatible socket node IDs
        """
        all_sockets = self.discover_all_sockets()
        compatible = set()

        for node_id, socket in all_sockets.items():
            # Skip if occupied by ANOTHER jewel (not this one)
            if node_id in occupied_sockets and node_id != jewel.socket_node_id:
                continue

            # Skip empty sockets if not requested
            if not include_empty and node_id not in occupied_sockets:
                continue

            # Check if socket can hold this jewel type
            if socket.can_hold_jewel(jewel):
                compatible.add(node_id)

        return compatible

    def calculate_socket_distances(
        self,
        allocated_nodes: Set[int]
    ) -> Dict[int, int]:
        """
        Calculate minimum pathing cost from allocated tree to each socket.

        This tells us how many points it would cost to reach each socket
        from the current tree. Sockets already in the allocated tree cost 0.

        Args:
            allocated_nodes: Currently allocated passive nodes

        Returns:
            Dict mapping socket_node_id -> minimum_points_to_reach
            Unreachable sockets are not included in the result.
        """
        sockets = self.discover_all_sockets()
        distances = {}

        for socket_id in sockets:
            if socket_id in allocated_nodes:
                # Already allocated - 0 additional cost
                distances[socket_id] = 0
            else:
                # Calculate shortest path from any allocated node to this socket
                min_distance = self.tree_graph.shortest_path_length(
                    from_nodes=allocated_nodes,
                    to_node=socket_id
                )
                if min_distance is not None:
                    distances[socket_id] = min_distance

        return distances


class JewelConstraintValidator:
    """
    Validates jewel placement constraints.

    Ensures:
    - Timeless jewels cannot move from original socket
    - Cluster jewels go in appropriate outer rim sockets
    - Cluster subgraphs remain connected
    """

    def __init__(self, tree_graph, socket_discovery: SocketDiscovery):
        """
        Initialize constraint validator.

        Args:
            tree_graph: PassiveTreeGraph instance
            socket_discovery: SocketDiscovery instance
        """
        self.tree_graph = tree_graph
        self.socket_discovery = socket_discovery

    def validate_assignment(
        self,
        assignment: JewelAssignment,
        allocated_nodes: Set[int]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a jewel assignment.

        Args:
            assignment: The proposed jewel assignment
            allocated_nodes: Currently allocated passive nodes

        Returns:
            (is_valid, error_message)
        """
        # Rule 1: Timeless jewels cannot move
        if assignment.is_timeless:
            if assignment.socket_node_id != assignment.original_socket_id:
                return False, "Timeless jewels cannot be moved from original socket"

        # Rule 2: Cluster jewels must go in compatible sockets
        if assignment.is_cluster:
            sockets = self.socket_discovery.discover_all_sockets()
            target_socket = sockets.get(assignment.socket_node_id)

            if not target_socket:
                return False, f"Socket {assignment.socket_node_id} not found"

            if not target_socket.can_hold_jewel(assignment.jewel):
                return False, f"Socket type mismatch for cluster jewel"

            # Rule 3: Cluster subgraph must remain connected
            if not self._validate_cluster_connectivity(assignment, allocated_nodes):
                return False, "Moving cluster would orphan allocated cluster nodes"

        return True, None

    def _validate_cluster_connectivity(
        self,
        assignment: JewelAssignment,
        allocated_nodes: Set[int]
    ) -> bool:
        """
        Validate that cluster jewel's passive nodes remain connected.

        Args:
            assignment: Cluster jewel assignment
            allocated_nodes: Currently allocated nodes

        Returns:
            True if cluster subgraph remains connected
        """
        if not assignment.is_cluster:
            return True

        cluster = assignment.jewel

        # Get all cluster nodes belonging to this jewel
        # Cluster nodes have IDs >= 65536 and belong to the cluster's subgraph
        cluster_nodes = {
            node_id for node_id in allocated_nodes
            if node_id >= 65536  # Cluster node ID range
        }

        # If no cluster nodes allocated, connectivity is trivial
        if not cluster_nodes:
            return True

        # Check if cluster socket is in the allocated set
        # (simplified check - full implementation would verify full subgraph)
        return assignment.socket_node_id in allocated_nodes


class JewelSocketOptimizer:
    """
    Optimizes jewel socket assignments for a build.

    Finds the best socket placement for each jewel while respecting:
    - Timeless jewels are immutable (cannot move)
    - Cluster jewels must go in compatible outer rim sockets
    - Unique/rare jewels can swap between regular sockets
    """

    def __init__(
        self,
        tree_graph,
        pob_caller,
        max_swaps: int = 20,
        min_improvement: float = 0.1,
    ):
        """
        Initialize socket optimizer.

        Args:
            tree_graph: PassiveTreeGraph instance
            pob_caller: PoBCaller instance for build evaluation
            max_swaps: Maximum number of socket swaps to try
            min_improvement: Minimum improvement to accept a swap (%)
        """
        self.tree_graph = tree_graph
        self.pob_caller = pob_caller
        self.max_swaps = max_swaps
        self.min_improvement = min_improvement

        self.discovery = SocketDiscovery(tree_graph)
        self.validator = JewelConstraintValidator(tree_graph, self.discovery)

    def optimize_sockets(
        self,
        build_xml: str,
        jewel_registry,
        objective: str = "dps",
        allocated_nodes: Optional[Set[int]] = None,
    ) -> Tuple[List[JewelAssignment], float]:
        """
        Optimize jewel socket assignments.

        Args:
            build_xml: Current build XML
            jewel_registry: JewelRegistry with current jewels
            objective: Optimization objective ("dps", "life", "ehp", "balanced")
            allocated_nodes: Set of allocated passive nodes

        Returns:
            (best_assignments, improvement_score)
        """
        if allocated_nodes is None:
            from ..modifier import get_passive_tree_summary
            summary = get_passive_tree_summary(build_xml)
            allocated_nodes = set(summary["allocated_nodes"])

        # Create initial assignment from current build
        current_assignments = self._create_initial_assignments(
            jewel_registry,
            allocated_nodes
        )

        # Get baseline fitness
        baseline_fitness = self._evaluate_fitness(build_xml, objective)
        best_fitness = baseline_fitness
        best_assignments = current_assignments.copy()

        # Try socket swaps
        swaps_tried = 0
        improvements = 0

        while swaps_tried < self.max_swaps:
            # Find candidate swaps
            candidate_swaps = self._find_candidate_swaps(
                current_assignments,
                allocated_nodes
            )

            if not candidate_swaps:
                break  # No more valid swaps

            # Try each swap
            improved = False
            for swap in candidate_swaps:
                swaps_tried += 1

                # Apply swap
                test_assignments = self._apply_swap(current_assignments, swap)

                # Validate
                if not self._validate_assignments(test_assignments, allocated_nodes):
                    continue

                # Evaluate
                test_xml = self._apply_assignments_to_xml(build_xml, test_assignments)
                test_fitness = self._evaluate_fitness(test_xml, objective)

                # Check improvement
                improvement_pct = ((test_fitness - best_fitness) / best_fitness) * 100

                if improvement_pct >= self.min_improvement:
                    # Accept improvement
                    current_assignments = test_assignments
                    best_fitness = test_fitness
                    best_assignments = test_assignments.copy()
                    improvements += 1
                    improved = True
                    break  # Try finding more swaps from this state

                if swaps_tried >= self.max_swaps:
                    break

            if not improved:
                break  # No improvement found, stop

        total_improvement = ((best_fitness - baseline_fitness) / baseline_fitness) * 100

        return best_assignments, total_improvement

    def _create_initial_assignments(
        self,
        jewel_registry,
        allocated_nodes: Set[int]
    ) -> List[JewelAssignment]:
        """Create initial assignments from current build."""
        assignments = []

        for jewel in jewel_registry.all_jewels:
            # Timeless jewels cannot move
            can_move = jewel.category != JewelCategory.TIMELESS

            assignment = JewelAssignment(
                jewel=jewel,
                socket_node_id=jewel.socket_node_id or 0,
                can_move=can_move,
                original_socket_id=jewel.socket_node_id,
                move_cost=0,
            )
            assignments.append(assignment)

        return assignments

    def _find_candidate_swaps(
        self,
        assignments: List[JewelAssignment],
        allocated_nodes: Set[int]
    ) -> List[Tuple[int, int]]:
        """
        Find candidate jewel swaps.

        Returns:
            List of (assignment_idx1, assignment_idx2) pairs that can swap
        """
        candidates = []

        # Only swap jewels of the same category
        movable_assignments = [
            (i, a) for i, a in enumerate(assignments)
            if a.can_move
        ]

        for i, (idx1, a1) in enumerate(movable_assignments):
            for idx2, a2 in movable_assignments[i + 1:]:
                # Check if jewels can swap sockets
                if self._can_swap(a1, a2, allocated_nodes):
                    candidates.append((idx1, idx2))

        return candidates

    def _can_swap(
        self,
        assignment1: JewelAssignment,
        assignment2: JewelAssignment,
        allocated_nodes: Set[int]
    ) -> bool:
        """Check if two assignments can swap sockets."""
        # Get sockets
        sockets = self.discovery.discover_all_sockets()
        socket1 = sockets.get(assignment1.socket_node_id)
        socket2 = sockets.get(assignment2.socket_node_id)

        if not socket1 or not socket2:
            return False

        # Check if each jewel can go in the other's socket
        return (
            socket1.can_hold_jewel(assignment2.jewel) and
            socket2.can_hold_jewel(assignment1.jewel)
        )

    def _apply_swap(
        self,
        assignments: List[JewelAssignment],
        swap: Tuple[int, int]
    ) -> List[JewelAssignment]:
        """Apply a socket swap to assignments."""
        idx1, idx2 = swap
        new_assignments = assignments.copy()

        # Swap socket_node_id between the two assignments
        socket1 = assignments[idx1].socket_node_id
        socket2 = assignments[idx2].socket_node_id

        new_assignments[idx1] = JewelAssignment(
            jewel=assignments[idx1].jewel,
            socket_node_id=socket2,
            can_move=assignments[idx1].can_move,
            original_socket_id=assignments[idx1].original_socket_id,
            move_cost=assignments[idx1].move_cost,
        )

        new_assignments[idx2] = JewelAssignment(
            jewel=assignments[idx2].jewel,
            socket_node_id=socket1,
            can_move=assignments[idx2].can_move,
            original_socket_id=assignments[idx2].original_socket_id,
            move_cost=assignments[idx2].move_cost,
        )

        return new_assignments

    def _validate_assignments(
        self,
        assignments: List[JewelAssignment],
        allocated_nodes: Set[int]
    ) -> bool:
        """Validate all assignments."""
        for assignment in assignments:
            is_valid, _ = self.validator.validate_assignment(
                assignment,
                allocated_nodes
            )
            if not is_valid:
                return False
        return True

    def _apply_assignments_to_xml(
        self,
        build_xml: str,
        assignments: List[JewelAssignment]
    ) -> str:
        """Apply jewel socket assignments to build XML."""
        import xml.etree.ElementTree as ET

        root = ET.fromstring(build_xml)

        # Update socket assignments in XML
        for sockets_elem in root.findall(".//Sockets"):
            for socket in sockets_elem.findall("Socket"):
                item_id_str = socket.get("itemId")

                if item_id_str and item_id_str != "0":
                    try:
                        item_id = int(item_id_str)

                        # Find assignment for this item
                        for assignment in assignments:
                            if assignment.jewel.item_id == item_id:
                                socket.set("nodeId", str(assignment.socket_node_id))
                                break
                    except ValueError:
                        continue

        return ET.tostring(root, encoding='unicode')

    def _evaluate_fitness(self, build_xml: str, objective: str) -> float:
        """Evaluate build fitness for the given objective."""
        result = self.pob_caller.calculate_build(build_xml)

        if objective == "dps":
            return result.total_dps
        elif objective == "life":
            return result.life
        elif objective == "ehp":
            return result.total_ehp
        elif objective == "balanced":
            # Balanced objective: weighted combination
            # Normalize each metric to similar scale
            dps_norm = result.total_dps / 1_000_000  # Normalize to millions
            life_norm = result.life / 1000  # Normalize to thousands
            ehp_norm = result.total_ehp / 10_000  # Normalize to 10k units

            return dps_norm + life_norm + ehp_norm
        else:
            return result.total_dps


# Export public API
__all__ = [
    'SocketType',
    'JewelSocket',
    'JewelAssignment',
    'SocketDiscovery',
    'JewelConstraintValidator',
    'JewelSocketOptimizer',
]

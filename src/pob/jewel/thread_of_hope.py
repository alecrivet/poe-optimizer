"""
Thread of Hope Optimizer Module

Optimizes Thread of Hope jewel placement by analyzing which socket provides
the best value based on accessible notables and pathing efficiency.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..tree_parser import PassiveTreeGraph
    from ..relative_calculator import RelativeCalculator

from .radius_calculator import RadiusCalculator

logger = logging.getLogger(__name__)


@dataclass
class ThreadOfHopePlacement:
    """Represents a potential Thread of Hope placement analysis."""
    socket_node_id: int
    ring_nodes: Set[int]  # All nodes allocatable via ring
    ring_notables: Set[int]  # Notable nodes in ring
    ring_keystones: Set[int] = field(default_factory=set)  # Keystone nodes in ring
    pathing_cost: int = 0  # Points to reach socket from current tree
    potential_savings: int = 0  # Points saved vs normal pathing to ring notables
    value_score: float = 0.0  # Estimated value of ring notables
    ring_size: str = ""  # Size of ring (Small, Medium, Large, Very Large)

    @property
    def notable_count(self) -> int:
        """Number of notables accessible in ring."""
        return len(self.ring_notables)

    @property
    def efficiency(self) -> float:
        """Efficiency metric: value per point spent."""
        if self.pathing_cost == 0:
            return self.value_score
        return self.value_score / self.pathing_cost


class ThreadOfHopeOptimizer:
    """
    Optimizes Thread of Hope placement for builds.

    Thread of Hope allows allocation of passives in a ring around a jewel socket,
    without needing to path to them. This can save significant passive points
    when valuable notables are within the ring but would require many points
    to path to normally.

    Ring sizes (inner/outer distances):
    - Small: 800-1000
    - Medium: 1000-1300
    - Large: 1300-1500
    - Very Large: 1500-1800
    """

    def __init__(
        self,
        radius_calc: RadiusCalculator,
        tree_graph: "PassiveTreeGraph"
    ):
        """
        Initialize with radius calculator and tree graph.

        Args:
            radius_calc: RadiusCalculator for computing node distances
            tree_graph: PassiveTreeGraph for node lookups and pathing
        """
        self.radius_calc = radius_calc
        self.tree_graph = tree_graph

    def analyze_socket(
        self,
        socket_id: int,
        allocated_nodes: Set[int],
        ring_size: str
    ) -> ThreadOfHopePlacement:
        """
        Analyze a single socket for Thread of Hope potential.

        Args:
            socket_id: Socket node ID to analyze
            allocated_nodes: Currently allocated nodes in build
            ring_size: Ring size ("Small", "Medium", "Large", "Very Large")

        Returns:
            ThreadOfHopePlacement with analysis results
        """
        # Get nodes in ring
        ring_nodes = self.radius_calc.get_thread_of_hope_nodes(socket_id, ring_size)

        # Filter for notables and keystones
        ring_notables = set()
        ring_keystones = set()

        for node_id in ring_nodes:
            node = self.tree_graph.get_node(node_id)
            if node:
                if node.node_type == "notable":
                    ring_notables.add(node_id)
                elif node.node_type == "keystone":
                    ring_keystones.add(node_id)

        # Calculate pathing cost to socket
        pathing_cost = 0
        if socket_id not in allocated_nodes:
            path_len = self.tree_graph.shortest_path_length(allocated_nodes, socket_id)
            pathing_cost = path_len if path_len is not None else 999

        # Calculate potential savings
        # For each notable in ring, calculate how many points it would take
        # to path there normally vs using Thread of Hope
        potential_savings = 0
        for notable_id in ring_notables:
            if notable_id not in allocated_nodes:
                normal_path = self.tree_graph.shortest_path_length(
                    allocated_nodes, notable_id
                )
                if normal_path is not None:
                    # With Thread of Hope, we just need 1 point (the notable itself)
                    # Normal pathing requires normal_path points
                    # But we also need to account for pathing to the socket
                    savings = normal_path - 1  # -1 because we still allocate the notable
                    if savings > 0:
                        potential_savings += savings

        # Calculate value score
        # Simple heuristic: notables are worth more, keystones even more
        value_score = len(ring_notables) * 10.0 + len(ring_keystones) * 25.0

        return ThreadOfHopePlacement(
            socket_node_id=socket_id,
            ring_nodes=ring_nodes,
            ring_notables=ring_notables,
            ring_keystones=ring_keystones,
            pathing_cost=pathing_cost,
            potential_savings=potential_savings,
            value_score=value_score,
            ring_size=ring_size
        )

    def find_optimal_placement(
        self,
        build_xml: str,
        ring_size: str,
        objective: str = "value",
        calculator: Optional["RelativeCalculator"] = None
    ) -> List[ThreadOfHopePlacement]:
        """
        Find best sockets for Thread of Hope across the tree.

        Args:
            build_xml: PoB build XML string
            ring_size: Ring size to analyze
            objective: Optimization objective:
                - "value": Maximize raw value score
                - "efficiency": Maximize value per point spent
                - "savings": Maximize points saved vs normal pathing
                - "dps": Use RelativeCalculator to estimate DPS impact
            calculator: Optional RelativeCalculator for DPS-based optimization

        Returns:
            List of ThreadOfHopePlacement sorted by objective (best first)
        """
        from ..modifier import get_passive_tree_summary

        # Parse allocated nodes from build
        try:
            summary = get_passive_tree_summary(build_xml)
            allocated_nodes = set(summary.get("allocated_nodes", []))
        except Exception as e:
            logger.warning(f"Could not parse build: {e}")
            allocated_nodes = set()

        # Get all jewel sockets
        jewel_sockets = self.tree_graph.get_jewel_sockets()
        socket_ids = {s.node_id for s in jewel_sockets}

        # Analyze each socket
        placements: List[ThreadOfHopePlacement] = []

        for socket_id in socket_ids:
            placement = self.analyze_socket(socket_id, allocated_nodes, ring_size)
            
            # Only include sockets that have at least one notable in ring
            if placement.notable_count > 0:
                placements.append(placement)

        # Sort by objective
        if objective == "value":
            placements.sort(key=lambda p: p.value_score, reverse=True)
        elif objective == "efficiency":
            placements.sort(key=lambda p: p.efficiency, reverse=True)
        elif objective == "savings":
            placements.sort(key=lambda p: p.potential_savings, reverse=True)
        elif objective == "dps" and calculator is not None:
            # Use RelativeCalculator to estimate DPS impact
            placements = self._sort_by_dps_impact(
                placements, build_xml, calculator, allocated_nodes
            )
        else:
            # Default to value
            placements.sort(key=lambda p: p.value_score, reverse=True)

        return placements

    def _sort_by_dps_impact(
        self,
        placements: List[ThreadOfHopePlacement],
        build_xml: str,
        calculator: "RelativeCalculator",
        allocated_nodes: Set[int]
    ) -> List[ThreadOfHopePlacement]:
        """
        Sort placements by estimated DPS impact using RelativeCalculator.

        This uses the relative calculator to estimate how much DPS each
        notable in the ring would add to the build.

        Args:
            placements: List of ThreadOfHopePlacement to sort
            build_xml: Build XML for calculations
            calculator: RelativeCalculator instance
            allocated_nodes: Currently allocated nodes

        Returns:
            Placements sorted by estimated DPS impact
        """
        placement_scores: List[tuple] = []

        for placement in placements:
            total_impact = 0.0

            # Estimate DPS impact of each unallocated notable in ring
            for notable_id in placement.ring_notables:
                if notable_id not in allocated_nodes:
                    try:
                        # Calculate relative impact of adding this notable
                        impact = calculator.calculate_node_impact(
                            build_xml, notable_id
                        )
                        if impact:
                            total_impact += impact.get("dps_change_percent", 0)
                    except Exception:
                        # If calculation fails, use default value
                        total_impact += 1.0

            placement.value_score = total_impact
            placement_scores.append((placement, total_impact))

        # Sort by DPS impact
        placement_scores.sort(key=lambda x: x[1], reverse=True)

        return [p for p, _ in placement_scores]

    def get_socket_analysis_report(
        self,
        placement: ThreadOfHopePlacement
    ) -> str:
        """
        Generate a human-readable report for a placement analysis.

        Args:
            placement: ThreadOfHopePlacement to report on

        Returns:
            Formatted string report
        """
        lines = [
            f"Socket {placement.socket_node_id} Analysis ({placement.ring_size} ring):",
            f"  Notables in ring: {placement.notable_count}",
            f"  Keystones in ring: {len(placement.ring_keystones)}",
            f"  Total nodes in ring: {len(placement.ring_nodes)}",
            f"  Pathing cost to socket: {placement.pathing_cost} points",
            f"  Potential point savings: {placement.potential_savings}",
            f"  Value score: {placement.value_score:.1f}",
            f"  Efficiency: {placement.efficiency:.2f}",
        ]

        if placement.ring_notables:
            lines.append("  Notable nodes:")
            for notable_id in sorted(placement.ring_notables):
                node = self.tree_graph.get_node(notable_id)
                if node:
                    lines.append(f"    - {node.name} ({notable_id})")

        if placement.ring_keystones:
            lines.append("  Keystone nodes:")
            for keystone_id in sorted(placement.ring_keystones):
                node = self.tree_graph.get_node(keystone_id)
                if node:
                    lines.append(f"    - {node.name} ({keystone_id})")

        return "
".join(lines)

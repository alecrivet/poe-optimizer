"""
Cluster Notable Optimizer

This module provides optimization for notable selection within cluster jewel
subgraphs. It evaluates the value of different notable combinations and
finds the optimal allocation given point constraints.

Key concepts:
- ClusterAllocation: A specific allocation of nodes within a cluster
- ClusterNotableOptimizer: Finds optimal notable selections

Optimization Strategy:
1. Start with socket node only (entry point)
2. Evaluate each notable: value gained vs point cost
3. Greedy add highest efficiency notables
4. Or exhaustive search if few notables (3-4)
"""

import logging
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Set, Optional, TYPE_CHECKING

from .cluster_subgraph import ClusterSubgraph, ClusterNode
from .cluster import ClusterJewel, CLUSTER_NODE_MIN_ID
from ..modifier import modify_passive_tree_nodes

if TYPE_CHECKING:
    from ..relative_calculator import RelativeCalculator

logger = logging.getLogger(__name__)


@dataclass
class ClusterAllocation:
    """
    Represents a specific allocation of nodes within a cluster subgraph.

    This captures the current state of a cluster jewel's allocated nodes,
    including which notables are taken and the associated costs.

    Attributes:
        subgraph: The ClusterSubgraph this allocation belongs to
        allocated_notables: Set of notable node IDs that are allocated
        allocated_small: Set of small passive node IDs that are allocated
        total_points: Total number of points spent in this cluster
        value_score: Computed value score for this allocation (objective-dependent)
    """
    subgraph: ClusterSubgraph
    allocated_notables: Set[int] = field(default_factory=set)
    allocated_small: Set[int] = field(default_factory=set)
    total_points: int = 0
    value_score: float = 0.0

    @property
    def all_allocated(self) -> Set[int]:
        """Get all allocated nodes (notables + small passives + socket)."""
        result = self.allocated_notables | self.allocated_small
        if self.subgraph.socket_node > 0:
            result.add(self.subgraph.socket_node)
        return result

    def get_notable_names(self) -> List[str]:
        """Get names of allocated notables."""
        names = []
        for notable_id in self.allocated_notables:
            node = self.subgraph.nodes.get(notable_id)
            if node:
                names.append(node.name)
        return names


@dataclass
class NotableEvaluation:
    """Evaluation result for a single notable."""
    notable_id: int
    notable_name: str
    value_gained: float
    point_cost: int
    efficiency: float  # value_gained / point_cost

    def __lt__(self, other: "NotableEvaluation") -> bool:
        """Sort by efficiency (descending)."""
        return self.efficiency > other.efficiency


class ClusterNotableOptimizer:
    """
    Optimizes notable selection within cluster jewel subgraphs.

    This optimizer evaluates different notable combinations and finds
    the allocation that maximizes value while respecting point constraints.

    Usage:
        optimizer = ClusterNotableOptimizer(calculator)
        allocation = optimizer.optimize_allocation(
            subgraph, base_xml, objective="dps", max_points=5
        )
    """

    def __init__(self, calculator: Optional["RelativeCalculator"] = None):
        """
        Initialize the cluster notable optimizer.

        Args:
            calculator: Optional RelativeCalculator for evaluating build changes.
                       If not provided, a simple heuristic scoring is used.
        """
        self.calculator = calculator

    def evaluate_notable(
        self,
        subgraph: ClusterSubgraph,
        notable_id: int,
        current_allocation: Set[int],
        base_xml: str,
        objective: str
    ) -> float:
        """
        Evaluate the value of adding a notable to the current allocation.

        This computes how much value (DPS, life, etc.) would be gained by
        allocating the path to the specified notable.

        Args:
            subgraph: The cluster subgraph being optimized
            notable_id: The notable node ID to evaluate
            current_allocation: Set of currently allocated node IDs
            base_xml: The current build XML
            objective: Optimization objective ("dps", "life", "ehp", "balanced")

        Returns:
            Value score for adding this notable (higher is better)
        """
        if notable_id not in subgraph.nodes:
            return 0.0

        if notable_id in current_allocation:
            return 0.0  # Already allocated

        # Get the nodes needed to reach this notable
        needed_nodes = subgraph.get_minimum_allocation({notable_id})
        new_nodes = needed_nodes - current_allocation

        if not new_nodes:
            return 0.0  # No new nodes needed (shouldn't happen)

        if self.calculator is None:
            # Heuristic: notables are worth more than small passives
            node = subgraph.nodes.get(notable_id)
            if node and node.is_notable:
                return 10.0  # Base notable value
            return 1.0  # Small passive value

        # Evaluate using the calculator
        try:
            # Create modified XML with the new nodes
            modified_xml = modify_passive_tree_nodes(
                base_xml,
                nodes_to_add=list(new_nodes)
            )

            # Evaluate the modification
            result = self.calculator.evaluate_modification(base_xml, modified_xml)

            # Return value based on objective
            if objective == "dps":
                return result.dps_change_percent
            elif objective == "life":
                return result.life_change_percent
            elif objective == "ehp":
                return result.ehp_change_percent
            elif objective == "balanced":
                return (result.dps_change_percent +
                        result.life_change_percent +
                        result.ehp_change_percent) / 3
            else:
                return result.dps_change_percent  # Default to DPS

        except Exception as e:
            logger.warning(f"Failed to evaluate notable {notable_id}: {e}")
            # Fall back to heuristic
            node = subgraph.nodes.get(notable_id)
            if node and node.is_notable:
                return 10.0
            return 1.0

    def optimize_allocation(
        self,
        subgraph: ClusterSubgraph,
        base_xml: str,
        objective: str,
        max_points: Optional[int] = None
    ) -> ClusterAllocation:
        """
        Find optimal notable allocation for a cluster.

        This method finds the best set of notables to allocate within
        the cluster, maximizing value while respecting point constraints.

        Args:
            subgraph: The cluster subgraph to optimize
            base_xml: The current build XML
            objective: Optimization objective ("dps", "life", "ehp", "balanced")
            max_points: Maximum points to spend in this cluster (optional)

        Returns:
            ClusterAllocation with the optimal allocation
        """
        notables = set(subgraph.notables)

        if not notables:
            # No notables, just return socket-only allocation
            return ClusterAllocation(
                subgraph=subgraph,
                allocated_notables=set(),
                allocated_small=set(),
                total_points=0,
                value_score=0.0
            )

        # For small notable counts, try exhaustive search
        if len(notables) <= 4:
            return self._exhaustive_search(subgraph, base_xml, objective, max_points)
        else:
            return self._greedy_search(subgraph, base_xml, objective, max_points)

    def _exhaustive_search(
        self,
        subgraph: ClusterSubgraph,
        base_xml: str,
        objective: str,
        max_points: Optional[int]
    ) -> ClusterAllocation:
        """Try all combinations of notables to find optimal."""
        notables = list(subgraph.notables)
        best_allocation = ClusterAllocation(
            subgraph=subgraph,
            allocated_notables=set(),
            allocated_small=set(),
            total_points=0,
            value_score=0.0
        )

        # Try all subsets of notables
        for r in range(len(notables) + 1):
            for notable_combo in combinations(notables, r):
                notable_set = set(notable_combo)

                # Get minimum allocation for this combination
                min_allocation = subgraph.get_minimum_allocation(notable_set)
                point_cost = len(min_allocation) - 1  # Exclude socket

                # Check point constraint
                if max_points is not None and point_cost > max_points:
                    continue

                # Evaluate this combination
                value = self._evaluate_allocation(
                    subgraph, notable_set, min_allocation, base_xml, objective
                )

                if value > best_allocation.value_score:
                    # Separate notables and small passives
                    notable_nodes = notable_set
                    small_nodes = min_allocation - notable_set - {subgraph.socket_node}

                    best_allocation = ClusterAllocation(
                        subgraph=subgraph,
                        allocated_notables=notable_nodes,
                        allocated_small=small_nodes,
                        total_points=point_cost,
                        value_score=value
                    )

        return best_allocation

    def _greedy_search(
        self,
        subgraph: ClusterSubgraph,
        base_xml: str,
        objective: str,
        max_points: Optional[int]
    ) -> ClusterAllocation:
        """Greedily add highest-value notables."""
        current_allocation = {subgraph.socket_node} if subgraph.socket_node > 0 else set()
        allocated_notables: Set[int] = set()
        total_points = 0
        total_value = 0.0

        remaining_notables = set(subgraph.notables)

        while remaining_notables:
            # Evaluate each remaining notable
            evaluations: List[NotableEvaluation] = []

            for notable_id in remaining_notables:
                # Get cost to add this notable
                needed = subgraph.get_minimum_allocation(
                    allocated_notables | {notable_id}
                )
                additional_nodes = needed - current_allocation
                point_cost = len(additional_nodes)

                if point_cost == 0:
                    continue  # Already reachable

                # Check point constraint
                if max_points is not None and total_points + point_cost > max_points:
                    continue

                # Evaluate value
                value = self.evaluate_notable(
                    subgraph, notable_id, current_allocation, base_xml, objective
                )

                node = subgraph.nodes.get(notable_id)
                name = node.name if node else f"Notable {notable_id}"

                evaluations.append(NotableEvaluation(
                    notable_id=notable_id,
                    notable_name=name,
                    value_gained=value,
                    point_cost=point_cost,
                    efficiency=value / point_cost if point_cost > 0 else 0
                ))

            if not evaluations:
                break  # No more notables can be added

            # Sort by efficiency and take the best
            evaluations.sort()
            best = evaluations[0]

            if best.value_gained <= 0:
                break  # No positive value remaining

            # Add the best notable
            needed = subgraph.get_minimum_allocation(
                allocated_notables | {best.notable_id}
            )
            new_nodes = needed - current_allocation

            current_allocation.update(needed)
            allocated_notables.add(best.notable_id)
            remaining_notables.remove(best.notable_id)
            total_points += best.point_cost
            total_value += best.value_gained

            logger.debug(
                f"Added notable {best.notable_name}: "
                f"+{best.value_gained:.1f} value for {best.point_cost} points"
            )

        # Separate notables and small passives
        small_nodes = current_allocation - allocated_notables - {subgraph.socket_node}

        return ClusterAllocation(
            subgraph=subgraph,
            allocated_notables=allocated_notables,
            allocated_small=small_nodes,
            total_points=total_points,
            value_score=total_value
        )

    def _evaluate_allocation(
        self,
        subgraph: ClusterSubgraph,
        notables: Set[int],
        all_nodes: Set[int],
        base_xml: str,
        objective: str
    ) -> float:
        """Evaluate the total value of an allocation."""
        if not notables and not all_nodes:
            return 0.0

        if self.calculator is None:
            # Heuristic: 10 points per notable, 1 per small
            notable_count = len(notables)
            small_count = len(all_nodes - notables - {subgraph.socket_node})
            return notable_count * 10.0 + small_count * 1.0

        # Use calculator to evaluate
        try:
            # Get nodes to add (exclude socket as it should already be allocated)
            nodes_to_add = list(all_nodes - {subgraph.socket_node})

            if not nodes_to_add:
                return 0.0

            modified_xml = modify_passive_tree_nodes(
                base_xml,
                nodes_to_add=nodes_to_add
            )

            result = self.calculator.evaluate_modification(base_xml, modified_xml)

            if objective == "dps":
                return result.dps_change_percent
            elif objective == "life":
                return result.life_change_percent
            elif objective == "ehp":
                return result.ehp_change_percent
            elif objective == "balanced":
                return (result.dps_change_percent +
                        result.life_change_percent +
                        result.ehp_change_percent) / 3
            else:
                return result.dps_change_percent

        except Exception as e:
            logger.warning(f"Failed to evaluate allocation: {e}")
            # Fall back to heuristic
            notable_count = len(notables)
            small_count = len(all_nodes - notables - {subgraph.socket_node})
            return notable_count * 10.0 + small_count * 1.0

    def generate_candidates(
        self,
        subgraph: ClusterSubgraph,
        current_xml: str,
        objective: str
    ) -> Dict[str, str]:
        """
        Generate optimizer candidates for cluster changes.

        This method generates multiple build variants with different
        cluster allocations for the optimizer to evaluate.

        Args:
            subgraph: The cluster subgraph to generate candidates for
            current_xml: The current build XML
            objective: Optimization objective

        Returns:
            Dict mapping candidate names to modified XML strings
        """
        candidates: Dict[str, str] = {}
        notables = list(subgraph.notables)

        if not notables:
            return candidates

        # Generate candidates for each individual notable
        for notable_id in notables:
            node = subgraph.nodes.get(notable_id)
            name = node.name if node else f"Notable_{notable_id}"

            # Get nodes needed for this notable
            needed = subgraph.get_minimum_allocation({notable_id})
            nodes_to_add = list(needed - {subgraph.socket_node})

            if nodes_to_add:
                try:
                    modified_xml = modify_passive_tree_nodes(
                        current_xml,
                        nodes_to_add=nodes_to_add
                    )
                    candidates[f"cluster_add_{name}"] = modified_xml
                except Exception as e:
                    logger.warning(f"Failed to generate candidate for {name}: {e}")

        # Generate candidate for all notables
        if len(notables) > 1:
            all_notable_set = set(notables)
            needed = subgraph.get_minimum_allocation(all_notable_set)
            nodes_to_add = list(needed - {subgraph.socket_node})

            if nodes_to_add:
                try:
                    modified_xml = modify_passive_tree_nodes(
                        current_xml,
                        nodes_to_add=nodes_to_add
                    )
                    candidates["cluster_add_all_notables"] = modified_xml
                except Exception as e:
                    logger.warning(f"Failed to generate all-notables candidate: {e}")

        return candidates

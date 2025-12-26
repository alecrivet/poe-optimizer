"""
Passive Tree Optimizer - Greedy Algorithm

This module implements a greedy algorithm for optimizing Path of Exile passive trees.
It iteratively tries adding/removing nodes to maximize an objective function.

Algorithm:
1. Start with current build
2. Generate all valid neighboring modifications (add/remove single nodes)
3. Evaluate each modification using RelativeCalculator
4. Pick the best improvement
5. Apply it and repeat
6. Stop when no improvements found or iteration limit reached

Features:
- Node removal: Try removing allocated nodes
- Node addition: Try adding adjacent unallocated nodes
- Mastery optimization: Select optimal mastery effects for each tree
- Budget constraints: Stay within point limits
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..pob.codec import encode_pob_code, decode_pob_code
from ..pob.modifier import modify_passive_tree_nodes, get_passive_tree_summary
from ..pob.relative_calculator import RelativeCalculator, RelativeEvaluation
from ..pob.mastery_optimizer import (
    get_mastery_database,
    MasteryOptimizer,
    MasteryDatabase,
)
from ..pob.tree_parser import load_passive_tree, PassiveTreeGraph

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result from a tree optimization run."""

    original_xml: str
    optimized_xml: str
    original_stats: RelativeEvaluation
    optimized_stats: RelativeEvaluation
    iterations: int
    modifications_applied: List[Dict]
    improvement_history: List[float]

    def get_improvement(self, objective: str = 'dps') -> float:
        """Get total improvement percentage for an objective."""
        if objective == 'dps':
            return self.optimized_stats.dps_change_percent
        elif objective == 'life':
            return self.optimized_stats.life_change_percent
        elif objective == 'ehp':
            return self.optimized_stats.ehp_change_percent
        else:
            raise ValueError(f"Unknown objective: {objective}")


class GreedyTreeOptimizer:
    """
    Greedy algorithm for passive tree optimization.

    Iteratively tries adding/removing individual nodes and keeps improvements.
    Simple but effective for local optimization.

    Example:
        >>> optimizer = GreedyTreeOptimizer(max_iterations=50)
        >>> result = optimizer.optimize(build_xml, objective='dps')
        >>> print(f"Improved DPS by {result.get_improvement('dps'):.1f}%")
    """

    def __init__(
        self,
        max_iterations: int = 100,
        min_improvement: float = 0.1,  # Stop if improvement < 0.1%
        max_points_change: int = 5,  # Maximum points to add/remove
        optimize_masteries: bool = True,  # Enable mastery optimization
        enable_node_addition: bool = True,  # Enable adding nodes to tree
        optimize_jewel_sockets: bool = False,  # Enable jewel socket swapping
    ):
        """
        Initialize the optimizer.

        Args:
            max_iterations: Maximum optimization iterations
            min_improvement: Minimum improvement percentage to continue
            max_points_change: Maximum point budget change (positive or negative)
            optimize_masteries: If True, optimize mastery effect selections
            enable_node_addition: If True, try adding nodes (requires tree graph)
            optimize_jewel_sockets: If True, try swapping jewels between sockets
        """
        self.max_iterations = max_iterations
        self.min_improvement = min_improvement
        self.max_points_change = max_points_change
        self.optimize_masteries = optimize_masteries
        self.enable_node_addition = enable_node_addition
        self.optimize_jewel_sockets = optimize_jewel_sockets
        self.calculator = RelativeCalculator()

        # Load mastery database if optimization enabled
        if self.optimize_masteries:
            logger.info("Loading mastery database...")
            self.mastery_db = get_mastery_database()
            self.mastery_optimizer = MasteryOptimizer(self.mastery_db)
            logger.info(f"Loaded {len(self.mastery_db.masteries)} mastery nodes")
        else:
            self.mastery_db = None
            self.mastery_optimizer = None

        # Load passive tree graph for node addition
        if self.enable_node_addition:
            logger.info("Loading passive tree graph...")
            self.tree_graph = load_passive_tree()
            logger.info(f"Loaded {self.tree_graph.count_nodes()} nodes from passive tree")
        else:
            self.tree_graph = None

        # Initialize jewel socket optimizer components
        if self.optimize_jewel_sockets:
            if not self.tree_graph:
                logger.info("Loading passive tree graph for jewel socket optimization...")
                self.tree_graph = load_passive_tree()

            from ..pob.jewel.socket_optimizer import SocketDiscovery, JewelConstraintValidator
            logger.info("Initializing jewel socket optimizer...")
            self.socket_discovery = SocketDiscovery(self.tree_graph)
            self.socket_validator = JewelConstraintValidator(self.tree_graph, self.socket_discovery)
        else:
            self.socket_discovery = None
            self.socket_validator = None

        logger.info(
            f"Initialized GreedyTreeOptimizer (max_iterations={max_iterations}, "
            f"min_improvement={min_improvement}%, max_points_change={max_points_change}, "
            f"optimize_masteries={optimize_masteries}, enable_node_addition={enable_node_addition}, "
            f"optimize_jewel_sockets={optimize_jewel_sockets})"
        )

    def optimize(
        self,
        build_xml: str,
        objective: str = 'dps',
        allow_point_increase: bool = True,
    ) -> OptimizationResult:
        """
        Optimize a build's passive tree.

        Args:
            build_xml: Original build XML
            objective: Optimization objective ('dps', 'life', 'ehp', 'balanced')
            allow_point_increase: If False, can only reallocate existing points

        Returns:
            OptimizationResult with optimization details
        """
        logger.info(f"Starting optimization with objective: {objective}")

        # Get baseline stats
        tree_summary = get_passive_tree_summary(build_xml)
        original_points = tree_summary['total_nodes']
        allocated_nodes = set(tree_summary['allocated_nodes'])

        logger.info(f"Original build: {original_points} points allocated")

        # Track optimization progress
        current_xml = build_xml
        modifications_applied = []
        improvement_history = []

        # Baseline evaluation (current build vs itself = no change)
        baseline_eval = self.calculator.evaluate_modification(build_xml, build_xml)

        for iteration in range(self.max_iterations):
            logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")

            # Generate candidate modifications
            candidates = self._generate_candidates(
                current_xml,
                allocated_nodes,
                original_points,
                allow_point_increase,
                objective
            )

            if not candidates:
                logger.info("No more candidates to try - stopping")
                break

            logger.info(f"Evaluating {len(candidates)} candidates...")

            # Evaluate all candidates
            evaluations = {}
            for name, modified_xml in candidates.items():
                eval_result = self.calculator.evaluate_modification(build_xml, modified_xml)
                evaluations[name] = (modified_xml, eval_result)

            # Find best improvement
            best_name, (best_xml, best_eval) = self._select_best(
                evaluations,
                objective
            )

            improvement = self._get_improvement_value(best_eval, objective)

            # Log all evaluations for debugging
            logger.info(f"Evaluation results:")
            for name, (_, eval_result) in sorted(
                evaluations.items(),
                key=lambda x: self._get_improvement_value(x[1][1], objective),
                reverse=True
            )[:5]:  # Top 5
                imp = self._get_improvement_value(eval_result, objective)
                logger.info(f"  {name}: {imp:+.2f}% {objective}")

            logger.info(
                f"Best candidate: {best_name} "
                f"({improvement:+.2f}% {objective})"
            )

            # Check if improvement is significant enough
            if improvement < self.min_improvement:
                logger.info(
                    f"Improvement below threshold ({improvement:.2f}% < {self.min_improvement}%) - stopping"
                )
                break

            # Apply the improvement
            current_xml = best_xml
            allocated_nodes = set(get_passive_tree_summary(current_xml)['allocated_nodes'])

            modifications_applied.append({
                'iteration': iteration + 1,
                'modification': best_name,
                'improvement_pct': improvement,
            })
            improvement_history.append(improvement)

            logger.info(f"Applied: {best_name} (+{improvement:.2f}% {objective})")

        # Final evaluation
        final_eval = self.calculator.evaluate_modification(build_xml, current_xml)

        logger.info(
            f"Optimization complete after {len(modifications_applied)} improvements "
            f"(total: {final_eval.dps_change_percent:+.1f}% DPS, "
            f"{final_eval.life_change_percent:+.1f}% Life)"
        )

        return OptimizationResult(
            original_xml=build_xml,
            optimized_xml=current_xml,
            original_stats=baseline_eval,
            optimized_stats=final_eval,
            iterations=len(modifications_applied),
            modifications_applied=modifications_applied,
            improvement_history=improvement_history,
        )

    def _optimize_masteries_for_tree(
        self,
        xml: str,
        objective: str
    ) -> str:
        """
        Optimize mastery effect selections for a given tree.

        Args:
            xml: Build XML with tree modifications
            objective: Optimization objective

        Returns:
            XML with optimized mastery selections
        """
        if not self.optimize_masteries or not self.mastery_optimizer:
            return xml

        # Get current tree state
        summary = get_passive_tree_summary(xml)
        allocated_nodes = summary['allocated_nodes']
        current_masteries = summary['mastery_effects']

        # Select optimal mastery effects
        optimal_masteries = self.mastery_optimizer.select_best_mastery_effects(
            allocated_nodes=allocated_nodes,
            current_mastery_effects=current_masteries,
            objective=objective,
            calculator=None  # Could pass self.calculator for evaluation
        )

        # If masteries changed, apply them
        if optimal_masteries != current_masteries:
            changed_count = sum(
                1 for node_id in optimal_masteries
                if optimal_masteries.get(node_id) != current_masteries.get(node_id)
            )

            if changed_count > 0:
                logger.debug(f"Optimized {changed_count} mastery selections")

                # Apply mastery changes
                xml = modify_passive_tree_nodes(
                    xml,
                    nodes_to_add=[],
                    nodes_to_remove=[],
                    mastery_effects_to_add=optimal_masteries
                )

        return xml

    def _generate_candidates(
        self,
        current_xml: str,
        allocated_nodes: set,
        original_points: int,
        allow_point_increase: bool,
        objective: str,
    ) -> Dict[str, str]:
        """
        Generate candidate modifications (add/remove single nodes).

        Tries:
        1. Optimizing mastery selections (no node changes)
        2. Removing each allocated node (up to 20)
        3. Adding each adjacent unallocated node (up to 20)

        Each candidate has its masteries optimized for the objective.

        Args:
            current_xml: Current build XML
            allocated_nodes: Set of currently allocated node IDs
            original_points: Original point count
            allow_point_increase: If False, can only reallocate existing points
            objective: Optimization objective

        Returns:
            Dict mapping candidate name to modified XML
        """
        candidates = {}

        current_points = len(allocated_nodes)
        points_below_max = original_points + self.max_points_change - current_points
        points_above_min = current_points - (original_points - self.max_points_change)

        # Try mastery-only optimization (no node changes)
        if self.optimize_masteries:
            try:
                mastery_optimized = self._optimize_masteries_for_tree(
                    current_xml,
                    objective
                )
                # Only add if it's different from current
                if mastery_optimized != current_xml:
                    candidates["Optimize mastery selections"] = mastery_optimized
            except Exception as e:
                logger.debug(f"Failed to optimize masteries: {e}")

        # Try jewel socket swaps (if enabled)
        if self.optimize_jewel_sockets and self.socket_discovery:
            try:
                jewel_swap_candidates = self._generate_jewel_swap_candidates(
                    current_xml,
                    allocated_nodes,
                    objective
                )
                candidates.update(jewel_swap_candidates)
            except Exception as e:
                logger.debug(f"Failed to generate jewel swap candidates: {e}")

        # Try removing each allocated node (one at a time)
        for node_id in list(allocated_nodes)[:20]:  # Limit to first 20 for speed
            candidate_name = f"Remove node {node_id}"

            # Check if we can remove (stay within budget)
            if points_above_min > 0:
                try:
                    modified_xml = modify_passive_tree_nodes(
                        current_xml,
                        nodes_to_remove=[node_id]
                    )

                    # Optimize mastery selections for this candidate
                    modified_xml = self._optimize_masteries_for_tree(
                        modified_xml,
                        objective
                    )

                    candidates[candidate_name] = modified_xml
                except Exception as e:
                    logger.debug(f"Failed to remove node {node_id}: {e}")

        # Try adding nodes (if enabled and tree graph loaded)
        if self.enable_node_addition and self.tree_graph:
            # Find unallocated nodes adjacent to current tree
            unallocated_neighbors = self.tree_graph.find_unallocated_neighbors(
                allocated_nodes
            )

            # Limit to first 20 neighbors for speed
            neighbors_to_try = list(unallocated_neighbors)[:20]

            logger.debug(
                f"Found {len(unallocated_neighbors)} unallocated neighbors, "
                f"trying {len(neighbors_to_try)}"
            )

            for node_id in neighbors_to_try:
                # Check if we can add (stay within budget)
                if not allow_point_increase and points_below_max <= 0:
                    break  # Can't add more points

                node = self.tree_graph.get_node(node_id)
                if not node:
                    continue

                # Skip mastery nodes (they're allocated automatically with their parent)
                if node.is_mastery:
                    continue

                candidate_name = f"Add node {node_id} ({node.name})"

                try:
                    modified_xml = modify_passive_tree_nodes(
                        current_xml,
                        nodes_to_add=[node_id]
                    )

                    # Optimize mastery selections for this candidate
                    modified_xml = self._optimize_masteries_for_tree(
                        modified_xml,
                        objective
                    )

                    candidates[candidate_name] = modified_xml
                except Exception as e:
                    logger.debug(f"Failed to add node {node_id}: {e}")

        return candidates

    def _select_best(
        self,
        evaluations: Dict[str, Tuple[str, RelativeEvaluation]],
        objective: str,
    ) -> Tuple[str, Tuple[str, RelativeEvaluation]]:
        """Select the best candidate based on objective."""

        def score_func(item):
            name, (xml, eval_result) = item
            return self._get_improvement_value(eval_result, objective)

        return max(evaluations.items(), key=score_func)

    def _generate_jewel_swap_candidates(
        self,
        current_xml: str,
        allocated_nodes: set,
        objective: str,
    ) -> Dict[str, str]:
        """
        Generate candidate jewel socket swaps.

        Tries swapping movable jewels (unique, cluster) between compatible sockets.
        Timeless jewels are never moved.

        Args:
            current_xml: Current build XML
            allocated_nodes: Set of currently allocated node IDs
            objective: Optimization objective

        Returns:
            Dict mapping candidate name to modified XML
        """
        from ..pob.jewel.registry import JewelRegistry
        from ..pob.jewel.socket_optimizer import JewelAssignment
        from ..pob.jewel.base import JewelCategory
        import xml.etree.ElementTree as ET

        candidates = {}

        try:
            # Load jewel registry
            registry = JewelRegistry.from_build_xml(current_xml)

            # Find movable jewels (not timeless)
            movable_jewels = [
                jewel for jewel in registry.all_jewels
                if jewel.category != JewelCategory.TIMELESS and jewel.socket_node_id
            ]

            if len(movable_jewels) < 2:
                return candidates  # Need at least 2 jewels to swap

            # Generate swap pairs (limit to first 10 for performance)
            swap_count = 0
            max_swaps = 10

            for i, jewel1 in enumerate(movable_jewels):
                if swap_count >= max_swaps:
                    break

                for jewel2 in movable_jewels[i + 1:]:
                    if swap_count >= max_swaps:
                        break

                    # Check if swap is valid
                    sockets = self.socket_discovery.discover_all_sockets()
                    socket1 = sockets.get(jewel1.socket_node_id)
                    socket2 = sockets.get(jewel2.socket_node_id)

                    if not socket1 or not socket2:
                        continue

                    # Check if each jewel can go in the other's socket
                    if not (socket1.can_hold_jewel(jewel2) and socket2.can_hold_jewel(jewel1)):
                        continue

                    # Swap is valid - apply it to XML
                    try:
                        root = ET.fromstring(current_xml)

                        # Update socket assignments
                        for sockets_elem in root.findall(".//Sockets"):
                            for socket in sockets_elem.findall("Socket"):
                                item_id_str = socket.get("itemId")

                                if item_id_str and item_id_str != "0":
                                    try:
                                        item_id = int(item_id_str)

                                        if item_id == jewel1.item_id:
                                            socket.set("nodeId", str(jewel2.socket_node_id))
                                        elif item_id == jewel2.item_id:
                                            socket.set("nodeId", str(jewel1.socket_node_id))
                                    except ValueError:
                                        continue

                        modified_xml = ET.tostring(root, encoding='unicode')

                        # Optimize masteries for this candidate
                        if self.optimize_masteries:
                            modified_xml = self._optimize_masteries_for_tree(
                                modified_xml,
                                objective
                            )

                        candidate_name = (
                            f"Swap jewels: {jewel1.item_id} (socket {jewel1.socket_node_id}) "
                            f"<-> {jewel2.item_id} (socket {jewel2.socket_node_id})"
                        )
                        candidates[candidate_name] = modified_xml
                        swap_count += 1

                    except Exception as e:
                        logger.debug(f"Failed to apply jewel swap: {e}")
                        continue

        except Exception as e:
            logger.debug(f"Error loading jewel registry for swaps: {e}")

        return candidates

    def _get_improvement_value(
        self,
        eval_result: RelativeEvaluation,
        objective: str,
    ) -> float:
        """Get improvement value for an objective."""
        if objective == 'dps':
            return eval_result.dps_change_percent
        elif objective == 'life':
            return eval_result.life_change_percent
        elif objective == 'ehp':
            return eval_result.ehp_change_percent
        elif objective == 'balanced':
            # Simple balanced score: average of normalized changes
            return (
                eval_result.dps_change_percent +
                eval_result.life_change_percent +
                eval_result.ehp_change_percent
            ) / 3
        else:
            raise ValueError(f"Unknown objective: {objective}")

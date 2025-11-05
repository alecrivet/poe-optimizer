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
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..pob.codec import encode_pob_code, decode_pob_code
from ..pob.modifier import modify_passive_tree_nodes, get_passive_tree_summary
from ..pob.relative_calculator import RelativeCalculator, RelativeEvaluation

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
    ):
        """
        Initialize the optimizer.

        Args:
            max_iterations: Maximum optimization iterations
            min_improvement: Minimum improvement percentage to continue
            max_points_change: Maximum point budget change (positive or negative)
        """
        self.max_iterations = max_iterations
        self.min_improvement = min_improvement
        self.max_points_change = max_points_change
        self.calculator = RelativeCalculator()

        logger.info(
            f"Initialized GreedyTreeOptimizer (max_iterations={max_iterations}, "
            f"min_improvement={min_improvement}%, max_points_change={max_points_change})"
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
                allow_point_increase
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

    def _generate_candidates(
        self,
        current_xml: str,
        allocated_nodes: set,
        original_points: int,
        allow_point_increase: bool,
    ) -> Dict[str, str]:
        """
        Generate candidate modifications (add/remove single nodes).

        For now: Simple approach - try removing each allocated node.
        Future: Try adding nodes, multi-node swaps, etc.
        """
        candidates = {}

        current_points = len(allocated_nodes)
        points_below_max = original_points + self.max_points_change - current_points
        points_above_min = current_points - (original_points - self.max_points_change)

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
                    candidates[candidate_name] = modified_xml
                except Exception as e:
                    logger.debug(f"Failed to remove node {node_id}: {e}")

        # TODO: Try adding nodes (requires knowing which nodes are available)
        # For now, we only support removal-based optimization

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

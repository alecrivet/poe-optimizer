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
- Parallel evaluation: Evaluate multiple candidates simultaneously
"""

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

from ..pob.codec import encode_pob_code, decode_pob_code
from ..pob.modifier import modify_passive_tree_nodes, get_passive_tree_summary
from ..pob.relative_calculator import RelativeCalculator, RelativeEvaluation
from ..pob.batch_calculator import BatchCalculator
from ..pob.mastery_optimizer import (
    get_mastery_database,
    MasteryOptimizer,
    MasteryDatabase,
)
from ..pob.build_context import BuildContext
from ..pob.tree_parser import load_passive_tree, PassiveTreeGraph
from ..pob.tree_positions import TreePositionLoader
from ..pob.jewel.radius_calculator import RadiusCalculator
from ..pob.jewel.thread_of_hope import ThreadOfHopeOptimizer, ThreadOfHopePlacement
from ..pob.jewel.cluster_optimizer import ClusterNotableOptimizer
from ..pob.jewel.cluster_subgraph import ClusterSubgraph, ClusterSubgraphBuilder
from ..pob.jewel.registry import JewelRegistry

logger = logging.getLogger(__name__)


def _evaluate_candidate(args: Tuple[str, str, str]) -> Tuple[str, str, Optional[RelativeEvaluation]]:
    """
    Evaluate a single candidate modification (for parallel execution).

    This is a module-level function to enable pickling for ProcessPoolExecutor.

    Args:
        args: Tuple of (candidate_name, baseline_xml, modified_xml)

    Returns:
        Tuple of (candidate_name, modified_xml, evaluation_result or None on error)
    """
    name, baseline_xml, modified_xml = args
    try:
        # Create a new calculator for this process
        calculator = RelativeCalculator()
        eval_result = calculator.evaluate_modification(baseline_xml, modified_xml)
        return (name, modified_xml, eval_result)
    except Exception as e:
        logger.debug(f"Failed to evaluate candidate {name}: {e}")
        return (name, modified_xml, None)


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
        allow_cluster_optimization: bool = False,  # Enable cluster jewel reallocation
        max_workers: Optional[int] = None,  # Parallel workers (None = CPU count)
        use_batch_evaluation: bool = False,  # EXPERIMENTAL: Use persistent worker pool
        show_progress: bool = True,  # Show progress bars during optimization
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
            allow_cluster_optimization: If True, allow reallocating nodes within
                                        cluster jewel subgraphs
            max_workers: Number of parallel workers for evaluation.
                         None = use CPU count, 1 = sequential (no parallelism)
            use_batch_evaluation: EXPERIMENTAL - If True, use persistent worker pool.
            show_progress: If True, show progress bars during optimization.
        """
        self.max_iterations = max_iterations
        self.min_improvement = min_improvement
        self.max_points_change = max_points_change
        self.optimize_masteries = optimize_masteries
        self.enable_node_addition = enable_node_addition
        self.optimize_jewel_sockets = optimize_jewel_sockets
        self.allow_cluster_optimization = allow_cluster_optimization
        self.max_workers = max_workers if max_workers is not None else os.cpu_count()
        self.use_batch_evaluation = use_batch_evaluation
        self.show_progress = show_progress and TQDM_AVAILABLE

        # Initialize calculator based on evaluation mode
        if use_batch_evaluation:
            logger.info("Using batch evaluation with persistent worker pool")
            self.batch_calculator = BatchCalculator(num_workers=self.max_workers)
            self.calculator = self.batch_calculator  # For compatibility
        else:
            self.batch_calculator = None
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

            # Initialize Thread of Hope optimizer
            try:
                logger.info("Initializing Thread of Hope optimizer...")
                position_loader = TreePositionLoader()
                positions = position_loader.load_positions()
                self.radius_calculator = RadiusCalculator(positions)
                self.thread_of_hope_optimizer = ThreadOfHopeOptimizer(
                    self.radius_calculator, self.tree_graph
                )
                logger.info(f"Thread of Hope optimizer ready ({len(positions)} node positions)")
            except Exception as e:
                logger.warning(f"Failed to initialize Thread of Hope optimizer: {e}")
                self.radius_calculator = None
                self.thread_of_hope_optimizer = None

            # Initialize cluster notable optimizer (if cluster optimization enabled)
            if self.allow_cluster_optimization:
                logger.info("Cluster optimization enabled - cluster notables can be reallocated")
                self.cluster_optimizer = ClusterNotableOptimizer(calculator=None)
            else:
                self.cluster_optimizer = None
        else:
            self.socket_discovery = None
            self.socket_validator = None
            self.radius_calculator = None
            self.thread_of_hope_optimizer = None
            self.cluster_optimizer = None

        # Build context for context-aware mastery scoring (set during optimize())
        self.build_context: Optional[BuildContext] = None
        self._baseline_xml: Optional[str] = None  # Store for mastery evaluation

        logger.info(
            f"Initialized GreedyTreeOptimizer (max_iterations={max_iterations}, "
            f"min_improvement={min_improvement}%, max_points_change={max_points_change}, "
            f"optimize_masteries={optimize_masteries}, enable_node_addition={enable_node_addition}, "
            f"optimize_jewel_sockets={optimize_jewel_sockets}, max_workers={self.max_workers}, "
            f"use_batch_evaluation={use_batch_evaluation})"
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

        # Store baseline XML for mastery evaluation
        self._baseline_xml = build_xml

        # Extract build context for context-aware mastery scoring
        if self.optimize_masteries:
            try:
                self.build_context = BuildContext.from_build_xml(build_xml)
                logger.info(
                    f"Build context: {self.build_context.primary_damage_type} "
                    f"{self.build_context.attack_or_spell}, "
                    f"defense: {self.build_context.defense_style}"
                )
            except Exception as e:
                logger.warning(f"Failed to extract build context: {e}")
                self.build_context = None

        # Start batch calculator if using batch evaluation
        if self.use_batch_evaluation and self.batch_calculator:
            logger.info("Starting worker pool...")
            num_workers = self.batch_calculator.start()
            logger.info(f"Worker pool ready ({num_workers} workers)")

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

        # Track cumulative improvement for progress display
        cumulative_improvement = 0.0

        # Create main iteration progress bar
        iteration_pbar = None
        if self.show_progress:
            iteration_pbar = tqdm(
                total=self.max_iterations,
                desc="Optimizing",
                unit="iter",
                leave=True,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}"
            )
            iteration_pbar.set_postfix_str(f"improvement: +0.00%")

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
                if iteration_pbar:
                    iteration_pbar.set_postfix_str(f"done! +{cumulative_improvement:.2f}%")
                break

            eval_mode = "batch" if self.use_batch_evaluation else f"parallel ({self.max_workers} workers)"
            logger.info(f"Evaluating {len(candidates)} candidates ({eval_mode})...")

            # Update progress bar description
            if iteration_pbar:
                iteration_pbar.set_description(f"Iter {iteration+1}: evaluating {len(candidates)} candidates")

            # Evaluate all candidates
            evaluations = {}

            if self.use_batch_evaluation and self.batch_calculator:
                # Batch evaluation using persistent worker pool (fastest)
                try:
                    # Create candidate progress bar for batch mode
                    if self.show_progress:
                        candidate_pbar = tqdm(
                            total=len(candidates),
                            desc="  Evaluating",
                            unit="build",
                            leave=False,
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                        )

                    batch_results = self.batch_calculator.evaluate_batch(
                        build_xml,
                        candidates
                    )
                    for name, eval_result in batch_results.items():
                        evaluations[name] = (candidates[name], eval_result)
                        if self.show_progress:
                            candidate_pbar.update(1)

                    if self.show_progress:
                        candidate_pbar.close()
                except Exception as e:
                    logger.error(f"Batch evaluation failed: {e}")
                    if self.show_progress and 'candidate_pbar' in locals():
                        candidate_pbar.close()

            elif self.max_workers == 1:
                # Sequential evaluation (for debugging or single-core)
                candidate_iter = candidates.items()
                if self.show_progress:
                    candidate_iter = tqdm(
                        candidate_iter,
                        total=len(candidates),
                        desc="  Evaluating",
                        unit="build",
                        leave=False
                    )
                for name, modified_xml in candidate_iter:
                    try:
                        eval_result = self.calculator.evaluate_modification(build_xml, modified_xml)
                        evaluations[name] = (modified_xml, eval_result)
                    except Exception as e:
                        logger.debug(f"Failed to evaluate {name}: {e}")
            else:
                # Parallel evaluation using ProcessPoolExecutor
                eval_args = [
                    (name, build_xml, modified_xml)
                    for name, modified_xml in candidates.items()
                ]

                # Create candidate progress bar for parallel mode
                candidate_pbar = None
                if self.show_progress:
                    candidate_pbar = tqdm(
                        total=len(candidates),
                        desc="  Evaluating",
                        unit="build",
                        leave=False,
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                    )

                with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(_evaluate_candidate, args): args[0]
                        for args in eval_args
                    }

                    for future in as_completed(futures):
                        name = futures[future]
                        try:
                            result_name, modified_xml, eval_result = future.result()
                            if eval_result is not None:
                                evaluations[result_name] = (modified_xml, eval_result)
                            else:
                                logger.debug(f"Skipping failed candidate: {result_name}")
                        except Exception as e:
                            logger.debug(f"Exception evaluating {name}: {e}")

                        if candidate_pbar:
                            candidate_pbar.update(1)

                if candidate_pbar:
                    candidate_pbar.close()

            if not evaluations:
                logger.warning("All candidates failed to evaluate")
                break

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
                if iteration_pbar:
                    iteration_pbar.set_postfix_str(f"done! +{cumulative_improvement:.2f}%")
                break

            # Apply the improvement
            current_xml = best_xml
            allocated_nodes = set(get_passive_tree_summary(current_xml)['allocated_nodes'])
            cumulative_improvement += improvement

            modifications_applied.append({
                'iteration': iteration + 1,
                'modification': best_name,
                'improvement_pct': improvement,
            })
            improvement_history.append(improvement)

            logger.info(f"Applied: {best_name} (+{improvement:.2f}% {objective})")

            # Update progress bar
            if iteration_pbar:
                iteration_pbar.update(1)
                iteration_pbar.set_postfix_str(f"improvement: +{cumulative_improvement:.2f}%")
                iteration_pbar.set_description(f"Iter {iteration+1}: applied {best_name[:30]}")

        # Close progress bar
        if iteration_pbar:
            iteration_pbar.close()

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

    def shutdown(self):
        """
        Shutdown the optimizer and release resources.

        Call this when done with optimization if using batch evaluation.
        """
        if self.batch_calculator:
            logger.info("Shutting down batch calculator...")
            self.batch_calculator.shutdown()

    def __enter__(self):
        """Context manager support for automatic cleanup."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Shutdown on context manager exit."""
        self.shutdown()
        return False

    def _optimize_masteries_for_tree(
        self,
        xml: str,
        objective: str
    ) -> str:
        """
        Optimize mastery effect selections for a given tree.

        Uses calculator-based evaluation when batch_calculator is available,
        otherwise falls back to heuristic scoring with build context awareness.

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
        allocated_nodes = set(summary['allocated_nodes'])
        current_masteries = summary['mastery_effects']

        # Select optimal mastery effects
        # Priority: batch calculator > regular calculator > heuristics
        if self.use_batch_evaluation and self.batch_calculator and self._baseline_xml:
            # Use batch calculator for faster evaluation
            try:
                optimal_masteries = self.mastery_optimizer.select_best_mastery_effects_batch(
                    base_xml=xml,
                    allocated_nodes=allocated_nodes,
                    current_effects=current_masteries,
                    objective=objective,
                    batch_calculator=self.batch_calculator
                )
                logger.debug("Used batch calculator for mastery evaluation")
            except Exception as e:
                logger.warning(f"Batch mastery evaluation failed, using heuristics: {e}")
                optimal_masteries = self.mastery_optimizer.select_best_mastery_effects(
                    allocated_nodes=allocated_nodes,
                    current_mastery_effects=current_masteries,
                    objective=objective,
                    calculator=None
                )
        else:
            # Fall back to heuristic scoring (context-aware if build_context available)
            optimal_masteries = self.mastery_optimizer.select_best_mastery_effects(
                allocated_nodes=allocated_nodes,
                current_mastery_effects=current_masteries,
                objective=objective,
                calculator=None
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

            # Try Thread of Hope placement candidates
            if self.thread_of_hope_optimizer:
                try:
                    toh_candidates = self._generate_thread_of_hope_candidates(
                        current_xml,
                        allocated_nodes,
                        objective
                    )
                    candidates.update(toh_candidates)
                except Exception as e:
                    logger.debug(f"Failed to generate Thread of Hope candidates: {e}")

            # Try cluster notable reallocation candidates
            if self.cluster_optimizer and self.allow_cluster_optimization:
                try:
                    cluster_candidates = self._generate_cluster_candidates(
                        current_xml,
                        allocated_nodes,
                        objective
                    )
                    candidates.update(cluster_candidates)
                except Exception as e:
                    logger.debug(f"Failed to generate cluster candidates: {e}")

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
        Generate candidate jewel socket moves and swaps.

        Includes:
        - Swaps between occupied sockets
        - Moves to empty sockets (considering pathing cost)

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

            if not movable_jewels:
                return candidates

            # Get occupied sockets
            occupied_sockets = {
                j.socket_node_id for j in registry.all_jewels
                if j.socket_node_id
            }

            # Get socket distances for point-aware evaluation
            socket_distances = self.socket_discovery.calculate_socket_distances(
                allocated_nodes
            )

            candidate_count = 0
            max_candidates = 15

            # --- Part 1: Generate moves to empty sockets ---
            for jewel in movable_jewels:
                if candidate_count >= max_candidates:
                    break

                # Find ALL compatible sockets (including empty)
                compatible = self.socket_discovery.find_compatible_sockets(
                    jewel,
                    occupied_sockets,
                    include_empty=True
                )

                current_socket = jewel.socket_node_id
                current_cost = socket_distances.get(current_socket, 0)

                for target_socket in compatible:
                    if candidate_count >= max_candidates:
                        break

                    if target_socket == current_socket:
                        continue

                    # Skip sockets occupied by other jewels (handled by swaps)
                    if target_socket in occupied_sockets:
                        continue

                    target_cost = socket_distances.get(target_socket)
                    if target_cost is None:
                        continue  # Unreachable socket

                    # Calculate point savings
                    point_savings = current_cost - target_cost

                    # Apply move to XML
                    try:
                        root = ET.fromstring(current_xml)

                        for sockets_elem in root.findall(".//Sockets"):
                            for socket in sockets_elem.findall("Socket"):
                                item_id_str = socket.get("itemId")
                                if item_id_str and item_id_str != "0":
                                    try:
                                        item_id = int(item_id_str)
                                        if item_id == jewel.item_id:
                                            socket.set("nodeId", str(target_socket))
                                    except ValueError:
                                        continue

                        modified_xml = ET.tostring(root, encoding='unicode')

                        # Optimize masteries for this candidate
                        if self.optimize_masteries:
                            modified_xml = self._optimize_masteries_for_tree(
                                modified_xml,
                                objective
                            )

                        if point_savings != 0:
                            candidate_name = (
                                f"Move jewel {jewel.item_id} to socket {target_socket} "
                                f"({point_savings:+d} pts)"
                            )
                        else:
                            candidate_name = (
                                f"Move jewel {jewel.item_id} to socket {target_socket}"
                            )
                        candidates[candidate_name] = modified_xml
                        candidate_count += 1

                    except Exception as e:
                        logger.debug(f"Failed to apply jewel move: {e}")
                        continue

            # --- Part 2: Generate swaps between occupied sockets ---
            if len(movable_jewels) >= 2:
                for i, jewel1 in enumerate(movable_jewels):
                    if candidate_count >= max_candidates:
                        break

                    for jewel2 in movable_jewels[i + 1:]:
                        if candidate_count >= max_candidates:
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
                            candidate_count += 1

                        except Exception as e:
                            logger.debug(f"Failed to apply jewel swap: {e}")
                            continue

        except Exception as e:
            logger.debug(f"Error loading jewel registry for swaps: {e}")

        return candidates

    def _generate_thread_of_hope_candidates(
        self,
        current_xml: str,
        allocated_nodes: set,
        objective: str,
    ) -> Dict[str, str]:
        """
        Generate candidates for Thread of Hope socket placements.

        Analyzes which sockets would benefit most from Thread of Hope
        and generates candidates with notables allocated via the ring.

        Args:
            current_xml: Current build XML
            allocated_nodes: Set of currently allocated node IDs
            objective: Optimization objective

        Returns:
            Dict mapping candidate name to modified XML
        """
        from ..pob.jewel.registry import JewelRegistry

        candidates = {}

        if not self.thread_of_hope_optimizer:
            return candidates

        try:
            # Check if build already has a Thread of Hope
            registry = JewelRegistry.from_build_xml(current_xml)
            has_thread = any(
                j.display_name and "thread of hope" in j.display_name.lower()
                for j in registry.unique_jewels
            )

            if not has_thread:
                # No Thread of Hope in build, skip analysis
                logger.debug("No Thread of Hope found in build, skipping ToH candidates")
                return candidates

            # Analyze potential placements for different ring sizes
            for ring_size in ["Medium", "Large"]:  # Most common sizes
                placements = self.thread_of_hope_optimizer.find_optimal_placement(
                    current_xml,
                    ring_size,
                    objective="value"
                )

                # Generate candidates for top 3 placements
                for placement in placements[:3]:
                    if placement.notable_count == 0:
                        continue

                    # Get unallocated notables in ring that we could benefit from
                    new_notables = placement.ring_notables - allocated_nodes

                    if not new_notables:
                        continue  # All notables already allocated

                    # Create candidate: add the top notable(s) via Thread of Hope
                    for notable_id in list(new_notables)[:2]:  # Max 2 per placement
                        node = self.tree_graph.get_node(notable_id)
                        if not node:
                            continue

                        try:
                            # Add the notable directly (Thread of Hope allows this)
                            modified_xml = modify_passive_tree_nodes(
                                current_xml,
                                nodes_to_add=[notable_id]
                            )

                            # Optimize masteries
                            if self.optimize_masteries:
                                modified_xml = self._optimize_masteries_for_tree(
                                    modified_xml,
                                    objective
                                )

                            candidate_name = (
                                f"ToH ({ring_size}): allocate {node.name} "
                                f"via socket {placement.socket_node_id}"
                            )
                            candidates[candidate_name] = modified_xml

                        except Exception as e:
                            logger.debug(f"Failed to create ToH candidate: {e}")

        except Exception as e:
            logger.debug(f"Error generating Thread of Hope candidates: {e}")

        return candidates

    def _generate_cluster_candidates(
        self,
        current_xml: str,
        allocated_nodes: set,
        objective: str,
    ) -> Dict[str, str]:
        """
        Generate candidates for cluster notable reallocation.

        Analyzes cluster jewel subgraphs and generates candidates that
        add or swap notables within clusters.

        Args:
            current_xml: Current build XML
            allocated_nodes: Set of currently allocated node IDs
            objective: Optimization objective

        Returns:
            Dict mapping candidate name to modified XML
        """
        candidates = {}

        if not self.cluster_optimizer or not self.allow_cluster_optimization:
            return candidates

        try:
            # Get jewel registry and cluster subgraphs
            registry = JewelRegistry.from_build_xml(current_xml)

            if not registry.has_cluster_jewels():
                return candidates

            # Build subgraphs for each cluster jewel
            subgraphs = registry.get_cluster_subgraphs(allocated_nodes)

            for subgraph in subgraphs:
                # Generate candidates using the cluster optimizer
                try:
                    cluster_candidates = self.cluster_optimizer.generate_candidates(
                        subgraph,
                        current_xml,
                        objective
                    )

                    # Optimize masteries for each cluster candidate
                    for name, modified_xml in cluster_candidates.items():
                        if self.optimize_masteries:
                            modified_xml = self._optimize_masteries_for_tree(
                                modified_xml,
                                objective
                            )
                        candidates[name] = modified_xml

                except Exception as e:
                    logger.debug(f"Failed to generate candidates for cluster: {e}")

        except Exception as e:
            logger.debug(f"Error generating cluster candidates: {e}")

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

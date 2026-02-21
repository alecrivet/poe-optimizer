"""
Genetic Algorithm for Passive Tree Optimization

This module implements a genetic algorithm for optimizing Path of Exile passive trees.
Unlike the greedy algorithm which does local optimization, the genetic algorithm explores
the solution space more broadly through evolution.

Algorithm Overview:
1. Initialize population of random tree modifications
2. Evaluate fitness of each individual (DPS, Life, EHP)
3. Select parents based on fitness
4. Create offspring through crossover (combine parent trees)
5. Apply mutations (add/remove nodes, change masteries)
6. Replace old population with new generation
7. Repeat until convergence or max generations

Key Concepts:
- Individual: A passive tree configuration (XML with allocated nodes)
- Population: Collection of individuals
- Fitness: Objective function value (DPS, Life, EHP, or multi-objective)
- Selection: Choosing parents based on fitness (tournament, roulette wheel)
- Crossover: Combining two parent trees to create offspring
- Mutation: Random changes to tree (add/remove nodes, change masteries)
- Elitism: Preserving best individuals across generations

Advantages over Greedy:
- Explores solution space more broadly
- Can escape local optima
- Can optimize multiple objectives simultaneously (Pareto frontier)
- Better for finding novel tree configurations
"""

import logging
import os
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from copy import deepcopy

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
from ..pob.tree_version import get_tree_version_from_xml
from ..pob.jewel.registry import JewelRegistry
from ..pob.jewel.cluster import is_cluster_node_id
from ..pob.jewel.radius_calculator import RadiusCalculator
from ..pob.jewel.thread_of_hope import ThreadOfHopeOptimizer
from ..pob.jewel.cluster_optimizer import ClusterNotableOptimizer
from ..pob.jewel.cluster_subgraph import ClusterSubgraph

logger = logging.getLogger(__name__)


def _evaluate_individual(args: Tuple[int, str, str, str]) -> Tuple[int, Optional[RelativeEvaluation]]:
    """
    Evaluate a single individual (for parallel execution).

    This is a module-level function to enable pickling for ProcessPoolExecutor.

    Args:
        args: Tuple of (individual_id, baseline_xml, individual_xml, objective)

    Returns:
        Tuple of (individual_id, evaluation_result or None if failed)
    """
    individual_id, baseline_xml, individual_xml, objective = args
    try:
        calculator = RelativeCalculator()
        eval_result = calculator.evaluate_modification(baseline_xml, individual_xml)
        return (individual_id, eval_result)
    except Exception as e:
        logger.debug(f"Failed to evaluate individual {individual_id}: {e}")
        return (individual_id, None)


@dataclass
class GeneticOptimizationResult:
    """
    Result from a genetic algorithm optimization run.

    Attributes:
        original_xml: Original build XML
        best_xml: Best optimized build XML found
        best_fitness: Fitness score of best individual
        best_fitness_details: Detailed evaluation of best individual
        generations: Number of generations completed
        best_fitness_history: Best fitness in each generation
        avg_fitness_history: Average fitness in each generation
        final_population: Final population after evolution
    """
    original_xml: str
    best_xml: str
    best_fitness: float
    best_fitness_details: RelativeEvaluation
    generations: int
    best_fitness_history: List[float]
    avg_fitness_history: List[float]
    final_population: 'Population'

    def get_improvement(self, objective: str = 'dps') -> float:
        """Get improvement percentage for an objective."""
        return self.best_fitness


@dataclass
class Individual:
    """
    Represents a single passive tree configuration in the population.

    Attributes:
        xml: Build XML with passive tree allocation
        fitness: Fitness score (higher is better)
        fitness_details: Detailed evaluation (DPS, Life, EHP changes)
        generation: Generation number when created
        parent_ids: IDs of parent individuals (for tracking lineage)
    """
    xml: str
    fitness: float = 0.0
    fitness_details: Optional[RelativeEvaluation] = None
    generation: int = 0
    parent_ids: Tuple[int, ...] = ()
    individual_id: int = 0
    _cached_summary: Optional[Dict] = field(default=None, repr=False)

    def _get_summary(self) -> Dict:
        """Lazily compute and cache the passive tree summary."""
        if self._cached_summary is None:
            self._cached_summary = get_passive_tree_summary(self.xml)
        return self._cached_summary

    def get_allocated_nodes(self) -> Set[int]:
        """Get set of allocated node IDs."""
        summary = self._get_summary()
        return set(summary['allocated_nodes'])

    def get_mastery_effects(self) -> Dict[int, int]:
        """Get mastery effect selections."""
        summary = self._get_summary()
        return summary['mastery_effects']

    def get_point_count(self) -> int:
        """Get total number of allocated points."""
        return len(self.get_allocated_nodes())


class Population:
    """
    Manages a population of passive tree individuals.

    Handles fitness evaluation, selection, and population statistics.
    """

    def __init__(
        self,
        individuals: List[Individual],
        baseline_xml: str,
        calculator: RelativeCalculator,
        batch_calculator: Optional[BatchCalculator] = None,
        max_workers: int = 1,
        use_batch_evaluation: bool = False,
        show_progress: bool = True,
    ):
        """
        Initialize population.

        Args:
            individuals: List of individuals in population
            baseline_xml: Original build XML for fitness comparison
            calculator: Calculator for evaluating fitness
            batch_calculator: Optional batch calculator for faster evaluation
            max_workers: Number of parallel workers for evaluation
            use_batch_evaluation: If True, use batch calculator
            show_progress: If True, show progress bars during evaluation
        """
        self.individuals = individuals
        self.baseline_xml = baseline_xml
        self.calculator = calculator
        self.batch_calculator = batch_calculator
        self.max_workers = max_workers
        self.use_batch_evaluation = use_batch_evaluation
        self.show_progress = show_progress and TQDM_AVAILABLE
        self.generation = 0
        self._next_id = 0

    def evaluate_fitness(self, objective: str = 'dps') -> None:
        """
        Evaluate fitness for all individuals in population.

        Supports three evaluation modes:
        1. Batch evaluation (fastest) - uses persistent worker pool
        2. Parallel evaluation - uses ProcessPoolExecutor
        3. Sequential evaluation - single-threaded

        Args:
            objective: Optimization objective ('dps', 'life', 'ehp', 'balanced')
        """
        num_individuals = len(self.individuals)
        logger.info(f"Evaluating fitness for {num_individuals} individuals...")

        # Create progress bar for evaluation
        eval_pbar = None
        if self.show_progress:
            eval_pbar = tqdm(
                total=num_individuals,
                desc="  Evaluating population",
                unit="ind",
                leave=False,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            )

        if self.use_batch_evaluation and self.batch_calculator:
            # Batch evaluation using persistent worker pool (fastest)
            self._evaluate_batch(objective, eval_pbar)
        elif self.max_workers > 1:
            # Parallel evaluation using ProcessPoolExecutor
            self._evaluate_parallel(objective, eval_pbar)
        else:
            # Sequential evaluation
            self._evaluate_sequential(objective, eval_pbar)

        if eval_pbar:
            eval_pbar.close()

    def _calculate_fitness(self, eval_result: RelativeEvaluation, objective: str) -> float:
        """Calculate fitness score from evaluation result."""
        if objective == 'dps':
            return eval_result.dps_change_percent
        elif objective == 'life':
            return eval_result.life_change_percent
        elif objective == 'ehp':
            return eval_result.ehp_change_percent
        elif objective == 'balanced':
            return (
                eval_result.dps_change_percent +
                eval_result.life_change_percent +
                eval_result.ehp_change_percent
            ) / 3
        else:
            raise ValueError(f"Unknown objective: {objective}")

    def _evaluate_sequential(self, objective: str, pbar=None) -> None:
        """Evaluate all individuals sequentially."""
        for individual in self.individuals:
            eval_result = self.calculator.evaluate_modification(
                self.baseline_xml,
                individual.xml
            )
            individual.fitness = self._calculate_fitness(eval_result, objective)
            individual.fitness_details = eval_result
            if pbar:
                pbar.update(1)

    def _evaluate_parallel(self, objective: str, pbar=None) -> None:
        """Evaluate all individuals in parallel using ProcessPoolExecutor."""
        # Build evaluation args
        eval_args = [
            (i, self.baseline_xml, ind.xml, objective)
            for i, ind in enumerate(self.individuals)
        ]

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(_evaluate_individual, args): args[0]
                for args in eval_args
            }

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result_idx, eval_result = future.result()
                    if eval_result is not None:
                        individual = self.individuals[result_idx]
                        individual.fitness = self._calculate_fitness(eval_result, objective)
                        individual.fitness_details = eval_result
                    else:
                        # Failed evaluation - assign very low fitness
                        self.individuals[idx].fitness = -1000
                except Exception as e:
                    logger.debug(f"Exception evaluating individual {idx}: {e}")
                    self.individuals[idx].fitness = -1000

                if pbar:
                    pbar.update(1)

    def _evaluate_batch(self, objective: str, pbar=None) -> None:
        """Evaluate all individuals using batch calculator."""
        # Build modifications dict
        modifications = {
            f"individual_{i}": ind.xml
            for i, ind in enumerate(self.individuals)
        }

        try:
            batch_results = self.batch_calculator.evaluate_batch(
                self.baseline_xml,
                modifications
            )

            for i, ind in enumerate(self.individuals):
                key = f"individual_{i}"
                if key in batch_results:
                    eval_result = batch_results[key]
                    ind.fitness = self._calculate_fitness(eval_result, objective)
                    ind.fitness_details = eval_result
                else:
                    ind.fitness = -1000  # Failed evaluation

                if pbar:
                    pbar.update(1)

        except Exception as e:
            logger.error(f"Batch evaluation failed: {e}, falling back to sequential")
            self._evaluate_sequential(objective, pbar)

    def get_best(self, n: int = 1) -> List[Individual]:
        """Get the n best individuals by fitness."""
        return sorted(self.individuals, key=lambda x: x.fitness, reverse=True)[:n]

    def get_worst(self, n: int = 1) -> List[Individual]:
        """Get the n worst individuals by fitness."""
        return sorted(self.individuals, key=lambda x: x.fitness)[:n]

    def get_stats(self) -> Dict:
        """Get population statistics."""
        if not self.individuals:
            return {}

        fitnesses = [ind.fitness for ind in self.individuals]
        return {
            'size': len(self.individuals),
            'generation': self.generation,
            'best_fitness': max(fitnesses),
            'worst_fitness': min(fitnesses),
            'avg_fitness': sum(fitnesses) / len(fitnesses),
            'median_fitness': sorted(fitnesses)[len(fitnesses) // 2],
        }

    def assign_id(self, individual: Individual) -> None:
        """Assign unique ID to individual."""
        individual.individual_id = self._next_id
        self._next_id += 1


class GeneticTreeOptimizer:
    """
    Genetic algorithm for passive tree optimization.

    Uses evolution-inspired operators to explore the solution space:
    - Selection: Choose fit individuals to reproduce
    - Crossover: Combine parent trees to create offspring
    - Mutation: Random modifications to trees
    - Elitism: Preserve best solutions

    Example:
        >>> optimizer = GeneticTreeOptimizer(
        ...     population_size=30,
        ...     generations=50,
        ...     mutation_rate=0.2
        ... )
        >>> result = optimizer.optimize(build_xml, objective='dps')
        >>> print(f"Best improvement: {result.best_fitness:.1f}%")
    """

    def __init__(
        self,
        population_size: int = 30,
        generations: int = 50,
        mutation_rate: float = 0.2,
        crossover_rate: float = 0.8,
        elitism_count: int = 5,
        tournament_size: int = 3,
        max_points_change: int = 10,
        optimize_masteries: bool = True,
        optimize_jewel_sockets: bool = False,
        allow_cluster_optimization: bool = False,
        max_workers: Optional[int] = None,
        use_batch_evaluation: bool = False,
        show_progress: bool = True,
        tree_version: Optional[str] = None,
    ):
        """
        Initialize genetic algorithm optimizer.

        Args:
            population_size: Number of individuals in population
            generations: Maximum number of generations
            mutation_rate: Probability of mutation (0.0 to 1.0)
            crossover_rate: Probability of crossover (0.0 to 1.0)
            elitism_count: Number of best individuals to preserve
            tournament_size: Size of tournament for selection
            max_points_change: Maximum point budget change from original
            optimize_masteries: If True, optimize mastery selections
            optimize_jewel_sockets: If True, include jewel socket swaps in mutations
            allow_cluster_optimization: If True, allow reallocating nodes within
                                        cluster jewel subgraphs
            max_workers: Number of parallel workers (None = CPU count)
            use_batch_evaluation: If True, use persistent worker pool
            show_progress: If True, show progress bars during evolution
        """
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = elitism_count
        self.tournament_size = tournament_size
        self.max_points_change = max_points_change
        self.optimize_masteries = optimize_masteries
        self.optimize_jewel_sockets = optimize_jewel_sockets
        self.allow_cluster_optimization = allow_cluster_optimization
        self.max_workers = max_workers if max_workers is not None else os.cpu_count()
        self.use_batch_evaluation = use_batch_evaluation
        self.show_progress = show_progress and TQDM_AVAILABLE
        self.tree_version = tree_version

        # Initialize components
        self.calculator = RelativeCalculator()
        self.tree_graph = load_passive_tree(self.tree_version)

        # Initialize batch calculator if using batch evaluation
        if use_batch_evaluation:
            logger.info("Using batch evaluation with persistent worker pool")
            self.batch_calculator = BatchCalculator(num_workers=self.max_workers)
        else:
            self.batch_calculator = None

        if self.optimize_masteries:
            self.mastery_db = get_mastery_database(tree_version=self.tree_version)
            self.mastery_optimizer = MasteryOptimizer(self.mastery_db)
        else:
            self.mastery_db = None
            self.mastery_optimizer = None

        # Initialize jewel socket optimizer components
        if self.optimize_jewel_sockets:
            from ..pob.jewel.socket_optimizer import SocketDiscovery, JewelConstraintValidator
            logger.info("Initializing jewel socket optimizer...")
            self.socket_discovery = SocketDiscovery(self.tree_graph)
            self.socket_validator = JewelConstraintValidator(self.tree_graph, self.socket_discovery)

            # Initialize Thread of Hope optimizer
            try:
                logger.info("Initializing Thread of Hope optimizer...")
                position_loader = TreePositionLoader(self.tree_version)
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

        # Protected nodes (jewel sockets, cluster nodes) - set during optimize()
        self.protected_nodes: Set[int] = set()

        # Build context for context-aware mastery scoring (set during optimize())
        self.build_context: Optional[BuildContext] = None
        self._baseline_xml: Optional[str] = None  # Store for mastery evaluation

        eval_mode = "batch" if use_batch_evaluation else f"parallel ({self.max_workers} workers)"
        logger.info(
            f"Initialized GeneticTreeOptimizer "
            f"(pop_size={population_size}, generations={generations}, "
            f"mutation_rate={mutation_rate}, crossover_rate={crossover_rate}, "
            f"optimize_jewel_sockets={optimize_jewel_sockets}, eval_mode={eval_mode})"
        )

    def optimize(
        self,
        build_xml: str,
        objective: str = 'dps',
    ):
        """
        Optimize a build's passive tree using genetic algorithm.

        The genetic algorithm evolution cycle:
        1. Initialize population with random variations
        2. FOR each generation:
           a. Evaluate fitness for all individuals
           b. Select elite individuals (best ones)
           c. WHILE population not full:
              - Select 2 parents (tournament selection)
              - Crossover parents to create offspring
              - Mutate offspring
              - Add to new population
           d. Replace population
        3. Return best individual found

        Args:
            build_xml: Original build XML
            objective: Optimization objective ('dps', 'life', 'ehp', 'balanced')

        Returns:
            GeneticOptimizationResult with best individual and history
        """
        logger.info(f"Starting genetic algorithm with objective: {objective}")
        logger.info(
            f"Population: {self.population_size}, "
            f"Generations: {self.generations}, "
            f"Mutation rate: {self.mutation_rate:.0%}"
        )

        # Resolve tree version from build XML if not explicitly set
        if self.tree_version is None:
            self.tree_version = get_tree_version_from_xml(build_xml)
            if self.tree_version:
                logger.info(f"Detected tree version from build: {self.tree_version}")

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

        # Get original tree info
        original_summary = get_passive_tree_summary(build_xml)
        original_nodes = set(original_summary['allocated_nodes'])

        # Initialize protected nodes from jewel registry
        # Protected nodes include: jewel sockets, cluster jewel nodes
        # We set protect_empty_sockets=False since we now support jewel removal
        jewel_registry = JewelRegistry.from_build_xml(build_xml)
        self.protected_nodes = jewel_registry.get_protected_nodes(
            original_nodes,
            protect_empty_sockets=False  # Only protect sockets with jewels
        )
        if self.protected_nodes:
            logger.info(
                f"Protected nodes (jewel sockets + cluster nodes): "
                f"{len(self.protected_nodes)}"
            )

        # Initialize population
        population = self._initialize_population(
            build_xml,
            original_nodes,
            objective
        )

        # Track evolution history
        best_fitness_history = []
        avg_fitness_history = []
        best_individual_overall = None

        # Create main progress bar for generations
        gen_pbar = None
        if self.show_progress:
            gen_pbar = tqdm(
                total=self.generations,
                desc="Evolving",
                unit="gen",
                leave=True,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}"
            )
            gen_pbar.set_postfix_str("best: +0.00%")

        # Evolution loop
        for generation in range(self.generations):
            logger.info(f"\n{'='*60}")
            logger.info(f"Generation {generation + 1}/{self.generations}")
            logger.info(f"{'='*60}")

            # Update progress bar description
            if gen_pbar:
                gen_pbar.set_description(f"Gen {generation+1}: evaluating {len(population.individuals)} individuals")

            # Evaluate fitness
            population.evaluate_fitness(objective)

            # Get statistics
            stats = population.get_stats()
            best_fitness_history.append(stats['best_fitness'])
            avg_fitness_history.append(stats['avg_fitness'])

            logger.info(
                f"Fitness - Best: {stats['best_fitness']:+.2f}%, "
                f"Avg: {stats['avg_fitness']:+.2f}%, "
                f"Worst: {stats['worst_fitness']:+.2f}%"
            )

            # Track best individual ever
            generation_best = population.get_best(1)[0]
            if (best_individual_overall is None or
                generation_best.fitness > best_individual_overall.fitness):
                best_individual_overall = generation_best
                logger.info(
                    f"New best found! Fitness: {generation_best.fitness:+.2f}%"
                )

            # Update progress bar
            if gen_pbar:
                gen_pbar.update(1)
                gen_pbar.set_postfix_str(f"best: {best_individual_overall.fitness:+.2f}%")

            # Check for convergence (optional early stopping)
            if generation > 10:
                recent_improvement = (
                    best_fitness_history[-1] - best_fitness_history[-10]
                )
                if abs(recent_improvement) < 0.1:
                    logger.info(
                        f"Converged: No significant improvement in 10 generations"
                    )
                    if gen_pbar:
                        gen_pbar.set_postfix_str(f"converged! best: {best_individual_overall.fitness:+.2f}%")
                    break

            # Create next generation
            new_individuals = []

            # Elitism: Keep best individuals
            elite = population.get_best(self.elitism_count)
            new_individuals.extend(elite)
            logger.info(
                f"Elitism: Preserved {self.elitism_count} best individuals"
            )

            # Fill rest of population with offspring
            offspring_needed = self.population_size - len(new_individuals)

            for _ in range(offspring_needed):
                # Select parents via tournament
                parent1 = self._tournament_selection(
                    population,
                    self.tournament_size
                )
                parent2 = self._tournament_selection(
                    population,
                    self.tournament_size
                )

                # Crossover
                if random.random() < self.crossover_rate:
                    offspring = self._crossover(parent1, parent2, generation + 1)
                else:
                    # No crossover, just copy parent
                    offspring = Individual(
                        xml=parent1.xml,
                        generation=generation + 1,
                        parent_ids=(parent1.individual_id,)
                    )

                # Mutation
                offspring = self._mutate(offspring, objective)

                new_individuals.append(offspring)

            # Replace population
            population.individuals = new_individuals
            population.generation = generation + 1

            # Assign IDs to new individuals
            for ind in new_individuals:
                if ind.individual_id == 0:
                    population.assign_id(ind)

        # Close progress bar
        if gen_pbar:
            gen_pbar.close()

        # Final evaluation
        population.evaluate_fitness(objective)
        final_best = population.get_best(1)[0]

        if (best_individual_overall is None or
            final_best.fitness > best_individual_overall.fitness):
            best_individual_overall = final_best

        logger.info(f"\n{'='*60}")
        logger.info(f"Genetic Algorithm Complete!")
        logger.info(f"{'='*60}")
        logger.info(
            f"Best fitness: {best_individual_overall.fitness:+.2f}% {objective}"
        )
        logger.info(f"Generations: {population.generation}")

        # Return result
        return GeneticOptimizationResult(
            original_xml=build_xml,
            best_xml=best_individual_overall.xml,
            best_fitness=best_individual_overall.fitness,
            best_fitness_details=best_individual_overall.fitness_details,
            generations=population.generation,
            best_fitness_history=best_fitness_history,
            avg_fitness_history=avg_fitness_history,
            final_population=population,
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

    def _initialize_population(
        self,
        baseline_xml: str,
        original_nodes: Set[int],
        objective: str,
    ) -> Population:
        """
        Create initial population.

        Strategy: Start with original tree, then create variations by:
        - Removing random nodes
        - Adding random adjacent nodes
        - Changing mastery selections

        Args:
            baseline_xml: Original build XML
            original_nodes: Original allocated nodes
            objective: Optimization objective

        Returns:
            Initialized population
        """
        logger.info(f"Initializing population of {self.population_size} individuals...")

        individuals = []

        # First individual is the original tree
        original_ind = Individual(
            xml=baseline_xml,
            generation=0,
            parent_ids=()
        )
        individuals.append(original_ind)

        # Create variations
        for i in range(1, self.population_size):
            # Create random variation
            varied_xml = self._create_random_variation(
                baseline_xml,
                original_nodes,
                objective
            )

            ind = Individual(
                xml=varied_xml,
                generation=0,
                parent_ids=()
            )
            individuals.append(ind)

        population = Population(
            individuals,
            baseline_xml,
            self.calculator,
            batch_calculator=self.batch_calculator,
            max_workers=self.max_workers,
            use_batch_evaluation=self.use_batch_evaluation,
            show_progress=self.show_progress,
        )

        # Assign IDs and evaluate
        for ind in individuals:
            population.assign_id(ind)
        population.evaluate_fitness(objective)

        logger.info(f"Initial population created: {population.get_stats()}")

        return population

    def _create_random_variation(
        self,
        xml: str,
        original_nodes: Set[int],
        objective: str,
    ) -> str:
        """
        Create a random variation of the tree.

        Randomly adds/removes nodes and changes masteries.
        This creates diversity in the initial population.
        """
        current_nodes = original_nodes.copy()
        num_changes = random.randint(1, 5)  # 1-5 random changes

        for _ in range(num_changes):
            action = random.choice(['add', 'remove', 'mastery'])

            if action == 'add':
                # Add random adjacent node
                neighbors = self.tree_graph.find_unallocated_neighbors(current_nodes)
                if neighbors:
                    node_to_add = random.choice(list(neighbors))
                    node = self.tree_graph.get_node(node_to_add)

                    # Skip mastery nodes
                    if node and not node.is_mastery:
                        try:
                            xml = modify_passive_tree_nodes(
                                xml,
                                nodes_to_add=[node_to_add]
                            )
                            current_nodes.add(node_to_add)
                        except Exception as e:
                            logger.debug(f"Failed to add node {node_to_add}: {e}")

            elif action == 'remove':
                # Remove random node (excluding protected nodes like jewel sockets and cluster nodes)
                removable_nodes = current_nodes - self.protected_nodes
                if len(removable_nodes) > 50:  # Keep tree reasonably sized
                    node_to_remove = random.choice(list(removable_nodes))
                    try:
                        xml = modify_passive_tree_nodes(
                            xml,
                            nodes_to_remove=[node_to_remove]
                        )
                        current_nodes.discard(node_to_remove)
                    except Exception as e:
                        logger.debug(f"Failed to remove node {node_to_remove}: {e}")

            elif action == 'mastery' and self.optimize_masteries:
                # Change random mastery selection
                xml = self._randomize_one_mastery(xml, objective)

        return xml

    def _optimize_masteries_for_tree(
        self,
        xml: str,
        objective: str
    ) -> str:
        """
        Optimize mastery effect selections for a given tree.

        Uses calculator-based evaluation when batch_calculator is available,
        otherwise falls back to heuristic scoring.

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
        # Priority: batch calculator > heuristics
        if self.use_batch_evaluation and self.batch_calculator and self._baseline_xml:
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
                xml = modify_passive_tree_nodes(
                    xml,
                    nodes_to_add=[],
                    nodes_to_remove=[],
                    mastery_effects_to_add=optimal_masteries
                )

        return xml

    def _randomize_one_mastery(self, xml: str, objective: str) -> str:
        """Randomly change one mastery selection."""
        summary = get_passive_tree_summary(xml)
        mastery_effects = summary['mastery_effects']

        if not mastery_effects:
            return xml

        # Pick random mastery node
        mastery_node_id = random.choice(list(mastery_effects.keys()))

        # Get available effects for this mastery
        if mastery_node_id in self.mastery_db.masteries:
            mastery_node = self.mastery_db.masteries[mastery_node_id]
            if mastery_node.available_effects:
                # Pick random effect
                random_effect = random.choice(mastery_node.available_effects)

                # Apply it
                new_masteries = mastery_effects.copy()
                new_masteries[mastery_node_id] = random_effect.effect_id

                xml = modify_passive_tree_nodes(
                    xml,
                    nodes_to_add=[],
                    nodes_to_remove=[],
                    mastery_effects_to_add=new_masteries
                )

        return xml

    def _tournament_selection(
        self,
        population: Population,
        tournament_size: int,
    ) -> Individual:
        """
        Select individual using tournament selection.

        Randomly sample tournament_size individuals and return the best.
        """
        tournament = random.sample(population.individuals, tournament_size)
        return max(tournament, key=lambda x: x.fitness)

    def _crossover(
        self,
        parent1: Individual,
        parent2: Individual,
        generation: int,
    ) -> Individual:
        """
        Create offspring by combining two parent trees.

        Strategy (Union Crossover):
        1. Take intersection of nodes (nodes both parents have)
        2. For each unique node, 50% chance to include from either parent
        3. Combine mastery selections from both parents

        This maintains tree connectivity since we start with common nodes.

        Example:
        Parent 1: [A, B, C, D, E] with masteries {M1: 5, M2: 3}
        Parent 2: [A, B, C, F, G] with masteries {M1: 7, M2: 3}

        Intersection: [A, B, C] (always included)
        Unique to P1: [D, E] (50% chance each)
        Unique to P2: [F, G] (50% chance each)
        Offspring: [A, B, C, D, G] with masteries from P1/P2 mix
        """
        nodes1 = parent1.get_allocated_nodes()
        nodes2 = parent2.get_allocated_nodes()
        masteries1 = parent1.get_mastery_effects()
        masteries2 = parent2.get_mastery_effects()

        # Start with intersection (common nodes)
        offspring_nodes = nodes1 & nodes2

        # Add unique nodes probabilistically
        unique_to_p1 = nodes1 - nodes2
        unique_to_p2 = nodes2 - nodes1

        for node_id in unique_to_p1:
            if random.random() < 0.5:  # 50% chance
                offspring_nodes.add(node_id)

        for node_id in unique_to_p2:
            if random.random() < 0.5:  # 50% chance
                offspring_nodes.add(node_id)

        # Combine mastery selections (prefer fitter parent)
        offspring_masteries = {}
        all_mastery_nodes = set(masteries1.keys()) | set(masteries2.keys())

        for mastery_node in all_mastery_nodes:
            # Only include if node is in offspring
            if mastery_node in offspring_nodes:
                # Prefer parent1 if fitter, else parent2
                if parent1.fitness >= parent2.fitness:
                    if mastery_node in masteries1:
                        offspring_masteries[mastery_node] = masteries1[mastery_node]
                    elif mastery_node in masteries2:
                        offspring_masteries[mastery_node] = masteries2[mastery_node]
                else:
                    if mastery_node in masteries2:
                        offspring_masteries[mastery_node] = masteries2[mastery_node]
                    elif mastery_node in masteries1:
                        offspring_masteries[mastery_node] = masteries1[mastery_node]

        # Build offspring XML
        # Start from parent1's XML and modify to match offspring
        offspring_xml = parent1.xml

        # Calculate nodes to add/remove (excluding protected nodes from removal)
        nodes_to_add = list(offspring_nodes - nodes1)
        nodes_to_remove = list((nodes1 - offspring_nodes) - self.protected_nodes)

        try:
            # Apply node changes
            if nodes_to_add or nodes_to_remove:
                offspring_xml = modify_passive_tree_nodes(
                    offspring_xml,
                    nodes_to_add=nodes_to_add,
                    nodes_to_remove=nodes_to_remove,
                    mastery_effects_to_add=offspring_masteries
                )
            elif offspring_masteries != masteries1:
                # Only mastery changes
                offspring_xml = modify_passive_tree_nodes(
                    offspring_xml,
                    nodes_to_add=[],
                    nodes_to_remove=[],
                    mastery_effects_to_add=offspring_masteries
                )
        except Exception as e:
            logger.debug(f"Crossover failed, using parent1: {e}")
            offspring_xml = parent1.xml

        # Create offspring individual
        offspring = Individual(
            xml=offspring_xml,
            generation=generation,
            parent_ids=(parent1.individual_id, parent2.individual_id)
        )

        return offspring

    def _mutate_jewel_swap(self, xml: str) -> str:
        """
        Randomly swap two jewels between compatible sockets.

        Args:
            xml: Build XML

        Returns:
            Modified XML with swapped jewels (or original if no valid swap)
        """
        from ..pob.jewel.base import JewelCategory
        import xml.etree.ElementTree as ET

        try:
            # Load jewel registry
            registry = JewelRegistry.from_build_xml(xml)

            # Find movable jewels (not timeless)
            movable_jewels = [
                jewel for jewel in registry.all_jewels
                if jewel.category != JewelCategory.TIMELESS and jewel.socket_node_id
            ]

            if len(movable_jewels) < 2:
                return xml  # Need at least 2 jewels to swap

            # Try random swaps until we find a valid one
            attempts = 0
            max_attempts = 10

            while attempts < max_attempts:
                # Pick two random jewels
                jewel1, jewel2 = random.sample(movable_jewels, 2)

                # Check if swap is valid
                sockets = self.socket_discovery.discover_all_sockets()
                socket1 = sockets.get(jewel1.socket_node_id)
                socket2 = sockets.get(jewel2.socket_node_id)

                if not socket1 or not socket2:
                    attempts += 1
                    continue

                # Check if each jewel can go in the other's socket
                if not (socket1.can_hold_jewel(jewel2) and socket2.can_hold_jewel(jewel1)):
                    attempts += 1
                    continue

                # Valid swap found - apply it
                root = ET.fromstring(xml)

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

                return ET.tostring(root, encoding='unicode')

        except Exception as e:
            logger.debug(f"Jewel swap mutation failed: {e}")

        return xml  # Return original if swap failed

    def _mutate_jewel_move(self, xml: str, allocated_nodes: Set[int]) -> str:
        """
        Move a random jewel to a random compatible empty socket.

        This allows jewels to explore positions outside the currently occupied
        sockets, potentially finding better placements with lower pathing costs.

        Args:
            xml: Build XML
            allocated_nodes: Currently allocated nodes (for distance calculation)

        Returns:
            Modified XML with moved jewel (or original if no valid move)
        """
        from ..pob.jewel.base import JewelCategory
        import xml.etree.ElementTree as ET

        try:
            # Load jewel registry
            registry = JewelRegistry.from_build_xml(xml)

            # Find movable jewels (not timeless)
            movable_jewels = [
                jewel for jewel in registry.all_jewels
                if jewel.category != JewelCategory.TIMELESS and jewel.socket_node_id
            ]

            if not movable_jewels:
                return xml

            # Get occupied sockets
            occupied_sockets = {
                j.socket_node_id for j in registry.all_jewels
                if j.socket_node_id
            }

            # Pick a random jewel to move
            jewel = random.choice(movable_jewels)

            # Find ALL compatible sockets (including empty)
            compatible = self.socket_discovery.find_compatible_sockets(
                jewel,
                occupied_sockets,
                include_empty=True
            )

            # Filter to only empty sockets (not current, not occupied by others)
            empty_compatible = [
                s for s in compatible
                if s != jewel.socket_node_id and s not in occupied_sockets
            ]

            if not empty_compatible:
                return xml  # No empty compatible sockets

            # Pick a random target socket
            target_socket = random.choice(empty_compatible)

            # Apply move to XML
            root = ET.fromstring(xml)

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

            logger.debug(
                f"Jewel move mutation: {jewel.item_id} from "
                f"{jewel.socket_node_id} to {target_socket}"
            )
            return ET.tostring(root, encoding='unicode')

        except Exception as e:
            logger.debug(f"Jewel move mutation failed: {e}")

        return xml

    def _mutate_jewel_removal(self, xml: str) -> str:
        """
        Remove a random jewel from the build entirely.

        This allows the optimizer to evaluate whether a jewel provides
        enough value to justify its pathing cost. Removing a mediocre
        jewel can free up points for better passive nodes.

        Args:
            xml: Build XML

        Returns:
            Modified XML with jewel removed (or original if removal failed)
        """
        from ..pob.jewel.base import JewelCategory
        import xml.etree.ElementTree as ET

        try:
            registry = JewelRegistry.from_build_xml(xml)

            # Only consider removing non-essential jewels
            # Don't remove timeless (build-defining) or clusters (complex dependencies)
            removable_jewels = [
                j for j in registry.all_jewels
                if j.category not in [JewelCategory.TIMELESS, JewelCategory.CLUSTER]
                and j.socket_node_id
            ]

            if not removable_jewels:
                return xml

            # Pick a random jewel to remove
            jewel = random.choice(removable_jewels)

            root = ET.fromstring(xml)

            # Remove jewel from Items section
            for items_elem in root.findall(".//Items"):
                for item in items_elem.findall("Item"):
                    if item.get("id") == str(jewel.item_id):
                        items_elem.remove(item)
                        break

            # Clear socket assignment
            for sockets_elem in root.findall(".//Sockets"):
                for socket in sockets_elem.findall("Socket"):
                    if socket.get("itemId") == str(jewel.item_id):
                        socket.set("itemId", "0")
                        break

            logger.debug(f"Jewel removal mutation: removed jewel {jewel.item_id}")
            return ET.tostring(root, encoding='unicode')

        except Exception as e:
            logger.debug(f"Jewel removal mutation failed: {e}")

        return xml

    def _mutate_thread_of_hope(self, xml: str, allocated_nodes: Set[int]) -> str:
        """
        Mutate by allocating a node via Thread of Hope ring.

        This mutation adds a notable that is within a Thread of Hope ring
        but would normally be too expensive to path to.

        Args:
            xml: Current build XML
            allocated_nodes: Currently allocated node IDs

        Returns:
            Modified build XML
        """
        if not self.thread_of_hope_optimizer:
            return xml

        try:
            registry = JewelRegistry.from_build_xml(xml)

            # Check if build has Thread of Hope
            has_thread = any(
                j.display_name and "thread of hope" in j.display_name.lower()
                for j in registry.unique_jewels
            )

            if not has_thread:
                return xml  # No Thread of Hope in build

            # Pick a random ring size
            ring_size = random.choice(["Small", "Medium", "Large", "Very Large"])

            # Get placements for this ring size
            placements = self.thread_of_hope_optimizer.find_optimal_placement(
                xml, ring_size, objective="value"
            )

            if not placements:
                return xml

            # Pick a random placement with unallocated notables
            random.shuffle(placements)

            for placement in placements:
                new_notables = placement.ring_notables - allocated_nodes
                if new_notables:
                    # Pick a random unallocated notable in the ring
                    notable_id = random.choice(list(new_notables))
                    node = self.tree_graph.get_node(notable_id)

                    if node and not node.is_mastery:
                        # Allocate the notable via Thread of Hope
                        return modify_passive_tree_nodes(
                            xml,
                            nodes_to_add=[notable_id]
                        )

        except Exception as e:
            logger.debug(f"Thread of Hope mutation failed: {e}")

        return xml

    def _mutate_cluster_notable(self, xml: str, allocated_nodes: Set[int]) -> str:
        """
        Mutate by adding or swapping a cluster notable.

        This mutation adds an unallocated notable in a cluster jewel's
        subgraph, which can improve the cluster jewel's effectiveness.

        Args:
            xml: Current build XML
            allocated_nodes: Currently allocated node IDs

        Returns:
            Modified build XML
        """
        if not self.cluster_optimizer or not self.allow_cluster_optimization:
            return xml

        try:
            registry = JewelRegistry.from_build_xml(xml)

            if not registry.has_cluster_jewels():
                return xml

            # Get cluster subgraphs
            subgraphs = registry.get_cluster_subgraphs(allocated_nodes)

            if not subgraphs:
                return xml

            # Pick a random cluster subgraph
            subgraph = random.choice(subgraphs)

            # Find unallocated notables in this cluster
            unallocated_notables = set(subgraph.notables) - allocated_nodes

            if not unallocated_notables:
                return xml  # All notables already allocated

            # Pick a random unallocated notable
            notable_id = random.choice(list(unallocated_notables))

            # Get the minimum allocation needed to reach this notable
            needed_nodes = subgraph.get_minimum_allocation({notable_id})
            nodes_to_add = list(needed_nodes - allocated_nodes)

            if nodes_to_add:
                return modify_passive_tree_nodes(
                    xml,
                    nodes_to_add=nodes_to_add
                )

        except Exception as e:
            logger.debug(f"Cluster notable mutation failed: {e}")

        return xml

    def _mutate(
        self,
        individual: Individual,
        objective: str,
    ) -> Individual:
        """
        Apply random mutations to individual.

        Mutation maintains genetic diversity and helps escape local optima.
        Each mutation happens with probability self.mutation_rate.

        Possible mutations:
        1. Add random adjacent node
        2. Remove random node
        3. Change random mastery selection
        4. Swap jewel sockets (if jewel optimization enabled)
        5. Move jewel to empty socket (if jewel optimization enabled)
        6. Remove jewel entirely (if jewel optimization enabled)
        7. Allocate node via Thread of Hope ring (if Thread of Hope present)
        8. Add cluster notable (if cluster optimization enabled)

        Example:
        Original: [A, B, C, D] with mastery {M1: 5}
        Mutation: [A, B, C, D, E] with mastery {M1: 7}
        (Added node E, changed mastery M1 from effect 5 to 7)
        """
        # Check if mutation should occur
        if random.random() > self.mutation_rate:
            return individual

        xml = individual.xml
        current_nodes = individual.get_allocated_nodes()

        # Choose mutation type
        mutation_types = ['add', 'remove', 'mastery']
        if self.optimize_jewel_sockets:
            mutation_types.extend(['jewel_swap', 'jewel_move', 'jewel_removal'])
        if self.thread_of_hope_optimizer:
            mutation_types.append('thread_of_hope')
        if self.cluster_optimizer and self.allow_cluster_optimization:
            mutation_types.append('cluster_notable')

        mutation_type = random.choice(mutation_types)

        if mutation_type == 'add':
            # Add random adjacent node
            neighbors = self.tree_graph.find_unallocated_neighbors(current_nodes)
            if neighbors:
                node_to_add = random.choice(list(neighbors))
                node = self.tree_graph.get_node(node_to_add)

                if node and not node.is_mastery:
                    try:
                        xml = modify_passive_tree_nodes(
                            xml,
                            nodes_to_add=[node_to_add]
                        )
                        logger.debug(
                            f"Mutation: Added node {node_to_add} ({node.name})"
                        )
                    except Exception as e:
                        logger.debug(f"Mutation add failed: {e}")

        elif mutation_type == 'remove':
            # Remove random node (excluding protected nodes like jewel sockets and cluster nodes)
            removable_nodes = current_nodes - self.protected_nodes
            if len(removable_nodes) > 50:  # Keep tree reasonably sized
                node_to_remove = random.choice(list(removable_nodes))
                try:
                    xml = modify_passive_tree_nodes(
                        xml,
                        nodes_to_remove=[node_to_remove]
                    )
                    logger.debug(f"Mutation: Removed node {node_to_remove}")
                except Exception as e:
                    logger.debug(f"Mutation remove failed: {e}")

        elif mutation_type == 'mastery' and self.optimize_masteries:
            # Change random mastery selection
            original_xml = xml
            xml = self._randomize_one_mastery(xml, objective)
            if xml != original_xml:
                logger.debug("Mutation: Changed mastery selection")

        elif mutation_type == 'jewel_swap' and self.optimize_jewel_sockets:
            # Swap two jewel sockets
            original_xml = xml
            xml = self._mutate_jewel_swap(xml)
            if xml != original_xml:
                logger.debug("Mutation: Swapped jewel sockets")

        elif mutation_type == 'jewel_move' and self.optimize_jewel_sockets:
            # Move a jewel to an empty socket
            original_xml = xml
            xml = self._mutate_jewel_move(xml, current_nodes)
            if xml != original_xml:
                logger.debug("Mutation: Moved jewel to empty socket")

        elif mutation_type == 'jewel_removal' and self.optimize_jewel_sockets:
            # Remove a jewel entirely (to free up pathing points)
            original_xml = xml
            xml = self._mutate_jewel_removal(xml)
            if xml != original_xml:
                logger.debug("Mutation: Removed jewel")

        elif mutation_type == 'thread_of_hope' and self.thread_of_hope_optimizer:
            # Allocate a node via Thread of Hope ring
            original_xml = xml
            xml = self._mutate_thread_of_hope(xml, current_nodes)
            if xml != original_xml:
                logger.debug("Mutation: Added node via Thread of Hope")

        elif mutation_type == 'cluster_notable' and self.cluster_optimizer:
            # Add or swap a cluster notable
            original_xml = xml
            xml = self._mutate_cluster_notable(xml, current_nodes)
            if xml != original_xml:
                logger.debug("Mutation: Modified cluster notable allocation")

        # Create mutated individual (keep same generation and parent IDs)
        mutated = Individual(
            xml=xml,
            generation=individual.generation,
            parent_ids=individual.parent_ids
        )

        return mutated

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
import random
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from copy import deepcopy

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

    def get_allocated_nodes(self) -> Set[int]:
        """Get set of allocated node IDs."""
        summary = get_passive_tree_summary(self.xml)
        return set(summary['allocated_nodes'])

    def get_mastery_effects(self) -> Dict[int, int]:
        """Get mastery effect selections."""
        summary = get_passive_tree_summary(self.xml)
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
    ):
        """
        Initialize population.

        Args:
            individuals: List of individuals in population
            baseline_xml: Original build XML for fitness comparison
            calculator: Calculator for evaluating fitness
        """
        self.individuals = individuals
        self.baseline_xml = baseline_xml
        self.calculator = calculator
        self.generation = 0
        self._next_id = 0

    def evaluate_fitness(self, objective: str = 'dps') -> None:
        """
        Evaluate fitness for all individuals in population.

        Args:
            objective: Optimization objective ('dps', 'life', 'ehp', 'balanced')
        """
        logger.info(f"Evaluating fitness for {len(self.individuals)} individuals...")

        for individual in self.individuals:
            # Evaluate against baseline
            eval_result = self.calculator.evaluate_modification(
                self.baseline_xml,
                individual.xml
            )

            # Calculate fitness based on objective
            if objective == 'dps':
                fitness = eval_result.dps_change_percent
            elif objective == 'life':
                fitness = eval_result.life_change_percent
            elif objective == 'ehp':
                fitness = eval_result.ehp_change_percent
            elif objective == 'balanced':
                # Balanced: average of all three
                fitness = (
                    eval_result.dps_change_percent +
                    eval_result.life_change_percent +
                    eval_result.ehp_change_percent
                ) / 3
            else:
                raise ValueError(f"Unknown objective: {objective}")

            individual.fitness = fitness
            individual.fitness_details = eval_result

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
        """
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = elitism_count
        self.tournament_size = tournament_size
        self.max_points_change = max_points_change
        self.optimize_masteries = optimize_masteries

        # Initialize components
        self.calculator = RelativeCalculator()
        self.tree_graph = load_passive_tree()

        if self.optimize_masteries:
            self.mastery_db = get_mastery_database()
            self.mastery_optimizer = MasteryOptimizer(self.mastery_db)
        else:
            self.mastery_db = None
            self.mastery_optimizer = None

        logger.info(
            f"Initialized GeneticTreeOptimizer "
            f"(pop_size={population_size}, generations={generations}, "
            f"mutation_rate={mutation_rate}, crossover_rate={crossover_rate})"
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

        # Get original tree info
        original_summary = get_passive_tree_summary(build_xml)
        original_nodes = set(original_summary['allocated_nodes'])

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

        # Evolution loop
        for generation in range(self.generations):
            logger.info(f"\n{'='*60}")
            logger.info(f"Generation {generation + 1}/{self.generations}")
            logger.info(f"{'='*60}")

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
                    f"🎉 New best found! Fitness: {generation_best.fitness:+.2f}%"
                )

            # Check for convergence (optional early stopping)
            if generation > 10:
                recent_improvement = (
                    best_fitness_history[-1] - best_fitness_history[-10]
                )
                if abs(recent_improvement) < 0.1:
                    logger.info(
                        f"Converged: No significant improvement in 10 generations"
                    )
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

        population = Population(individuals, baseline_xml, self.calculator)

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

            elif action == 'remove' and len(current_nodes) > 50:
                # Remove random node (but keep tree reasonably sized)
                node_to_remove = random.choice(list(current_nodes))
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

        # Calculate nodes to add/remove
        nodes_to_add = list(offspring_nodes - nodes1)
        nodes_to_remove = list(nodes1 - offspring_nodes)

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
        1. Add random adjacent node (33% if triggered)
        2. Remove random node (33% if triggered)
        3. Change random mastery selection (33% if triggered)

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
        mutation_type = random.choice(['add', 'remove', 'mastery'])

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
            # Remove random node
            if len(current_nodes) > 50:  # Keep tree reasonably sized
                node_to_remove = random.choice(list(current_nodes))
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

        # Create mutated individual (keep same generation and parent IDs)
        mutated = Individual(
            xml=xml,
            generation=individual.generation,
            parent_ids=individual.parent_ids
        )

        return mutated

"""
Multi-Objective Optimization for Passive Trees

This module implements multi-objective optimization using Pareto dominance.
Unlike single-objective optimization (maximize DPS only), multi-objective
optimization finds the best trade-offs between competing objectives.

Key Concepts:

1. Multiple Objectives:
   - DPS (damage per second)
   - Life (effective health pool)
   - Defense (EHP - effective hit points)

2. Pareto Dominance:
   - Solution A dominates B if A is better in ALL objectives
   - Example: A = [+5% DPS, +3% Life], B = [+4% DPS, +2% Life]
   - A dominates B (better in both)

3. Pareto Frontier:
   - Set of non-dominated solutions
   - No solution dominates any other
   - Represents best trade-offs

   Example Frontier:
   Solution A: [+10% DPS, +2% Life]  ← High DPS, low Life
   Solution B: [+7% DPS, +5% Life]   ← Balanced
   Solution C: [+3% DPS, +9% Life]   ← Low DPS, high Life

   User picks based on preference!

4. NSGA-II Algorithm:
   - Non-dominated Sorting Genetic Algorithm II
   - Industry standard for multi-objective optimization
   - Maintains diverse Pareto frontier
   - Fast and efficient

Algorithm Overview:
1. Initialize population (like genetic algorithm)
2. FOR each generation:
   a. Evaluate all objectives (DPS, Life, EHP)
   b. Non-dominated sorting (rank by dominance)
   c. Crowding distance (maintain diversity)
   d. Selection based on rank + diversity
   e. Crossover and mutation
3. Return Pareto frontier

Benefits:
- See trade-offs between objectives
- Choose preferred balance
- No need to pick weights upfront
- Discover all good solutions
"""

import logging
from typing import List, Set, Tuple, Dict, Optional
from dataclasses import dataclass
from copy import deepcopy
import random

from ..pob.relative_calculator import RelativeEvaluation

logger = logging.getLogger(__name__)


@dataclass
class MultiObjectiveScore:
    """
    Represents fitness across multiple objectives.

    Attributes:
        dps_percent: DPS improvement percentage
        life_percent: Life improvement percentage
        ehp_percent: EHP improvement percentage
        evaluation: Full evaluation details
    """
    dps_percent: float
    life_percent: float
    ehp_percent: float
    evaluation: RelativeEvaluation

    def dominates(self, other: 'MultiObjectiveScore') -> bool:
        """
        Check if this score dominates another (Pareto dominance).

        A dominates B if:
        - A is >= B in all objectives
        - A is > B in at least one objective

        Args:
            other: Another multi-objective score

        Returns:
            True if this dominates other
        """
        # Check if >= in all objectives
        dps_better_or_equal = self.dps_percent >= other.dps_percent
        life_better_or_equal = self.life_percent >= other.life_percent
        ehp_better_or_equal = self.ehp_percent >= other.ehp_percent

        # Check if > in at least one
        dps_strictly_better = self.dps_percent > other.dps_percent
        life_strictly_better = self.life_percent > other.life_percent
        ehp_strictly_better = self.ehp_percent > other.ehp_percent

        all_better_or_equal = (
            dps_better_or_equal and
            life_better_or_equal and
            ehp_better_or_equal
        )

        at_least_one_strictly_better = (
            dps_strictly_better or
            life_strictly_better or
            ehp_strictly_better
        )

        return all_better_or_equal and at_least_one_strictly_better

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple for easy comparison."""
        return (self.dps_percent, self.life_percent, self.ehp_percent)

    def __repr__(self) -> str:
        return (
            f"MultiObjectiveScore(DPS={self.dps_percent:+.1f}%, "
            f"Life={self.life_percent:+.1f}%, EHP={self.ehp_percent:+.1f}%)"
        )


@dataclass
class ParetoIndividual:
    """
    Individual for multi-objective optimization.

    Extends Individual with:
    - Multi-objective score
    - Pareto rank (dominance level)
    - Crowding distance (diversity measure)
    """
    xml: str
    score: MultiObjectiveScore
    rank: int = 0  # Pareto rank (0 = non-dominated)
    crowding_distance: float = 0.0  # Diversity measure
    individual_id: int = 0

    def __lt__(self, other: 'ParetoIndividual') -> bool:
        """
        Compare individuals for selection.

        Prefer:
        1. Lower rank (better dominance)
        2. Higher crowding distance (more diverse)
        """
        if self.rank != other.rank:
            return self.rank < other.rank
        return self.crowding_distance > other.crowding_distance


class ParetoFrontier:
    """
    Represents a Pareto frontier of non-dominated solutions.

    The frontier is the set of solutions where no solution is dominated
    by any other. This represents the best trade-offs between objectives.
    """

    def __init__(self, individuals: List[ParetoIndividual]):
        """
        Initialize Pareto frontier.

        Args:
            individuals: List of non-dominated individuals
        """
        self.individuals = individuals

    def get_extreme_points(self) -> Dict[str, ParetoIndividual]:
        """
        Get extreme points on the frontier.

        Returns:
            Dict with keys: 'max_dps', 'max_life', 'max_ehp'
        """
        if not self.individuals:
            return {}

        return {
            'max_dps': max(self.individuals, key=lambda x: x.score.dps_percent),
            'max_life': max(self.individuals, key=lambda x: x.score.life_percent),
            'max_ehp': max(self.individuals, key=lambda x: x.score.ehp_percent),
        }

    def get_balanced_solution(self) -> Optional[ParetoIndividual]:
        """
        Get most balanced solution (closest to equal improvement in all objectives).

        Returns:
            Individual with most balanced improvements
        """
        if not self.individuals:
            return None

        def balance_score(ind: ParetoIndividual) -> float:
            """Lower score = more balanced (less variance)."""
            dps = ind.score.dps_percent
            life = ind.score.life_percent
            ehp = ind.score.ehp_percent

            mean = (dps + life + ehp) / 3
            variance = (
                (dps - mean) ** 2 +
                (life - mean) ** 2 +
                (ehp - mean) ** 2
            ) / 3

            return variance

        return min(self.individuals, key=balance_score)

    def size(self) -> int:
        """Get number of solutions on frontier."""
        return len(self.individuals)

    def __repr__(self) -> str:
        return f"ParetoFrontier(size={self.size()})"


def calculate_pareto_ranks(individuals: List[ParetoIndividual]) -> List[List[ParetoIndividual]]:
    """
    Calculate Pareto ranks using non-dominated sorting.

    Assigns each individual a rank:
    - Rank 0: Non-dominated (Pareto frontier)
    - Rank 1: Dominated by rank 0 only
    - Rank 2: Dominated by rank 0 and 1 only
    - etc.

    Args:
        individuals: List of individuals to rank

    Returns:
        List of fronts (each front is a list of individuals with same rank)
    """
    n = len(individuals)

    # For each individual, track:
    # - domination_count: how many individuals dominate this one
    # - dominated_by: set of individuals this one dominates
    domination_count = [0] * n
    dominated_by = [[] for _ in range(n)]

    # Compare all pairs
    for i in range(n):
        for j in range(i + 1, n):
            if individuals[i].score.dominates(individuals[j].score):
                # i dominates j
                domination_count[j] += 1
                dominated_by[i].append(j)
            elif individuals[j].score.dominates(individuals[i].score):
                # j dominates i
                domination_count[i] += 1
                dominated_by[j].append(i)

    # First front: individuals with domination_count = 0
    fronts = []
    current_front = []

    for i in range(n):
        if domination_count[i] == 0:
            individuals[i].rank = 0
            current_front.append(individuals[i])

    fronts.append(current_front)

    # Build subsequent fronts
    rank = 0
    while fronts[rank]:
        next_front = []

        for i in range(n):
            if individuals[i] in fronts[rank]:
                # For each individual this one dominates
                for j in dominated_by[i]:
                    domination_count[j] -= 1

                    if domination_count[j] == 0:
                        individuals[j].rank = rank + 1
                        next_front.append(individuals[j])

        rank += 1
        fronts.append(next_front)

    # Remove empty last front
    fronts = [f for f in fronts if f]

    return fronts


def calculate_crowding_distances(front: List[ParetoIndividual]) -> None:
    """
    Calculate crowding distance for individuals in a front.

    Crowding distance measures how crowded the space around an individual is.
    Higher values = more isolated = better for diversity.

    Boundary individuals (min/max in any objective) get infinite distance
    to ensure they're preserved.

    Args:
        front: List of individuals in the same Pareto rank
    """
    n = len(front)

    if n <= 2:
        # Boundary cases: all get infinite distance
        for ind in front:
            ind.crowding_distance = float('inf')
        return

    # Initialize distances to 0
    for ind in front:
        ind.crowding_distance = 0.0

    # Calculate for each objective
    objectives = ['dps_percent', 'life_percent', 'ehp_percent']

    for obj in objectives:
        # Sort by this objective
        front_sorted = sorted(front, key=lambda x: getattr(x.score, obj))

        # Boundary individuals get infinite distance
        front_sorted[0].crowding_distance = float('inf')
        front_sorted[-1].crowding_distance = float('inf')

        # Get objective range
        obj_min = getattr(front_sorted[0].score, obj)
        obj_max = getattr(front_sorted[-1].score, obj)
        obj_range = obj_max - obj_min

        if obj_range == 0:
            continue

        # Calculate distances for middle individuals
        for i in range(1, n - 1):
            if front_sorted[i].crowding_distance != float('inf'):
                obj_prev = getattr(front_sorted[i - 1].score, obj)
                obj_next = getattr(front_sorted[i + 1].score, obj)

                # Add normalized distance
                front_sorted[i].crowding_distance += (obj_next - obj_prev) / obj_range


def get_pareto_frontier(individuals: List[ParetoIndividual]) -> ParetoFrontier:
    """
    Extract Pareto frontier (rank 0 individuals).

    Args:
        individuals: List of individuals

    Returns:
        ParetoFrontier with non-dominated solutions
    """
    fronts = calculate_pareto_ranks(individuals)

    if fronts and fronts[0]:
        # Calculate crowding distances for the frontier
        calculate_crowding_distances(fronts[0])
        return ParetoFrontier(fronts[0])

    return ParetoFrontier([])


def format_pareto_frontier(frontier: ParetoFrontier) -> str:
    """
    Format Pareto frontier for display.

    Args:
        frontier: Pareto frontier to format

    Returns:
        Formatted string
    """
    if frontier.size() == 0:
        return "Empty frontier"

    lines = []
    lines.append(f"\n{'='*80}")
    lines.append(f"Pareto Frontier: {frontier.size()} Solutions")
    lines.append(f"{'='*80}")

    # Extreme points
    extremes = frontier.get_extreme_points()

    lines.append(f"\n[BEST] Extreme Points:")
    if 'max_dps' in extremes:
        ind = extremes['max_dps']
        lines.append(
            f"   Max DPS:     {ind.score.dps_percent:+6.1f}% DPS, "
            f"{ind.score.life_percent:+6.1f}% Life, "
            f"{ind.score.ehp_percent:+6.1f}% EHP"
        )

    if 'max_life' in extremes:
        ind = extremes['max_life']
        lines.append(
            f"   Max Life:    {ind.score.dps_percent:+6.1f}% DPS, "
            f"{ind.score.life_percent:+6.1f}% Life, "
            f"{ind.score.ehp_percent:+6.1f}% EHP"
        )

    if 'max_ehp' in extremes:
        ind = extremes['max_ehp']
        lines.append(
            f"   Max EHP:     {ind.score.dps_percent:+6.1f}% DPS, "
            f"{ind.score.life_percent:+6.1f}% Life, "
            f"{ind.score.ehp_percent:+6.1f}% EHP"
        )

    # Balanced solution
    balanced = frontier.get_balanced_solution()
    if balanced:
        lines.append(
            f"   Balanced:    {balanced.score.dps_percent:+6.1f}% DPS, "
            f"{balanced.score.life_percent:+6.1f}% Life, "
            f"{balanced.score.ehp_percent:+6.1f}% EHP"
        )

    # All solutions sorted by DPS
    lines.append(f"\nAll Solutions (sorted by DPS):")
    sorted_individuals = sorted(
        frontier.individuals,
        key=lambda x: x.score.dps_percent,
        reverse=True
    )

    for i, ind in enumerate(sorted_individuals[:10], 1):  # Show top 10
        lines.append(
            f"   {i:2d}. DPS={ind.score.dps_percent:+6.1f}%, "
            f"Life={ind.score.life_percent:+6.1f}%, "
            f"EHP={ind.score.ehp_percent:+6.1f}%"
        )

    if len(sorted_individuals) > 10:
        lines.append(f"   ... and {len(sorted_individuals) - 10} more")

    lines.append(f"{'='*80}\n")

    return '\n'.join(lines)

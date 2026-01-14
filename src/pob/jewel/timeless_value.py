"""
Timeless Jewel Value Calculator

Calculates the value of timeless jewel transformations at different sockets.
Used for optimizing jewel placement and seed selection.

Value is computed based on:
- The objective (DPS, Life, EHP)
- The transformations applied by the jewel at that socket
- Which nodes are allocated in the build
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Set, Tuple, TYPE_CHECKING

from .timeless_data import (
    TimelessJewelDataLoader,
    TimelessTransformation,
    TimelessNodeMod,
    get_default_loader,
)
from .base import JewelRadius

if TYPE_CHECKING:
    from .timeless import TimelessJewel
    from ..tree_parser import PassiveTreeGraph

logger = logging.getLogger(__name__)


# Stat weights for different objectives
# Values represent approximate contribution to the objective
DPS_STAT_WEIGHTS = {
    # Damage mods
    "fire_damage_+%": 1.0,
    "cold_damage_+%": 1.0,
    "lightning_damage_+%": 1.0,
    "physical_damage_+%": 1.0,
    "chaos_damage_+%": 1.0,
    "damage_+%": 1.2,
    "attack_damage_+%": 1.0,
    "spell_damage_+%": 1.0,
    "minion_damage_+%": 1.0,
    "area_damage_+%": 0.9,
    "projectile_damage_+%": 0.9,
    "damage_over_time_+%": 0.9,

    # Crit
    "critical_strike_chance_+%": 0.8,
    "base_critical_strike_multiplier_+": 1.2,

    # Speed
    "attack_speed_+%": 1.5,
    "cast_speed_+%": 1.5,

    # Attributes (for attribute-stacking builds)
    "strength": 0.2,
    "dexterity": 0.2,
    "intelligence": 0.2,

    # Other useful stats
    "accuracy_rating_+%": 0.4,
    "base_skill_area_of_effect_+%": 0.3,
    "base_projectile_speed_+%": 0.2,
}

LIFE_STAT_WEIGHTS = {
    # Life
    "maximum_life_+%": 2.0,
    "base_maximum_life": 1.0,
    "life_regeneration_rate_per_minute_%": 0.5,
    "base_life_regeneration_rate_per_minute": 0.3,
    "base_life_leech_from_attack_damage_permyriad": 0.4,

    # Attributes (strength gives life)
    "strength": 0.5,

    # Recovery
    "life_recovery_rate_+%": 0.6,
}

EHP_STAT_WEIGHTS = {
    # Life
    "maximum_life_+%": 1.5,
    "base_maximum_life": 0.8,

    # Energy Shield
    "maximum_energy_shield_+%": 1.5,
    "base_maximum_energy_shield": 0.8,

    # Resistances
    "fire_damage_resistance_%": 1.0,
    "cold_damage_resistance_%": 1.0,
    "lightning_damage_resistance_%": 1.0,
    "chaos_damage_resistance_%": 1.2,
    "base_resist_all_elements_%": 2.0,

    # Armour/Evasion
    "physical_damage_reduction_rating_+%": 0.6,
    "base_evasion_rating_+%": 0.5,
    "evasion_rating_+%": 0.5,
    "base_additional_physical_damage_reduction_%": 2.0,

    # Attributes
    "strength": 0.3,  # Life
    "intelligence": 0.2,  # ES
    "dexterity": 0.1,  # Evasion

    # Block/Dodge
    "block_%": 1.5,
    "spell_block_%": 1.5,

    # Other defenses
    "base_life_regeneration_rate_per_minute": 0.4,
    "life_regeneration_rate_per_minute_%": 0.6,
}


def get_stat_weights(objective: str) -> Dict[str, float]:
    """Get stat weights for an objective."""
    objective_lower = objective.lower()
    if "dps" in objective_lower or "damage" in objective_lower:
        return DPS_STAT_WEIGHTS
    elif "life" in objective_lower:
        return LIFE_STAT_WEIGHTS
    elif "ehp" in objective_lower or "defence" in objective_lower or "defense" in objective_lower:
        return EHP_STAT_WEIGHTS
    else:
        # Default to DPS
        return DPS_STAT_WEIGHTS


class RadiusCalculator(Protocol):
    """Protocol for radius calculation (stub for Stream B dependency)."""

    def get_nodes_in_radius(
        self, socket_id: int, radius: JewelRadius
    ) -> Set[int]:
        """Get nodes within radius of a socket."""
        ...


@dataclass
class TimelessSocketAnalysis:
    """
    Analysis of a timeless jewel at a specific socket.

    Attributes:
        socket_node_id: The jewel socket node ID
        affected_nodes: All nodes within the jewel's radius
        transformations: Dict of node_id -> transformation
        total_value: Aggregate value for the objective
        best_nodes: Top transformed nodes by value
        pathing_cost: Number of unallocated nodes needed to path
    """
    socket_node_id: int
    affected_nodes: Set[int] = field(default_factory=set)
    transformations: Dict[int, TimelessTransformation] = field(default_factory=dict)
    total_value: float = 0.0
    best_nodes: List[Tuple[int, float]] = field(default_factory=list)
    pathing_cost: int = 0

    def __repr__(self) -> str:
        return (
            f"TimelessSocketAnalysis(socket={self.socket_node_id}, "
            f"value={self.total_value:.1f}, nodes={len(self.affected_nodes)})"
        )


class SimpleRadiusCalculator:
    """
    Simple radius calculator using distance-based calculation.

    This is a fallback implementation if RadiusCalculator from Stream B
    is not available.
    """

    def __init__(self, tree: "PassiveTreeGraph"):
        self.tree = tree
        # Cache socket positions
        self._socket_positions: Dict[int, Tuple[float, float]] = {}

    def get_nodes_in_radius(
        self, socket_id: int, radius: JewelRadius
    ) -> Set[int]:
        """Get nodes within radius of a socket using Euclidean distance."""
        socket_node = self.tree.get_node(socket_id)
        if socket_node is None:
            return set()

        socket_x, socket_y = socket_node.x, socket_node.y
        max_dist_sq = radius.node_distance ** 2

        in_radius = set()
        for node_id, node in self.tree.nodes.items():
            dx = node.x - socket_x
            dy = node.y - socket_y
            if dx * dx + dy * dy <= max_dist_sq:
                in_radius.add(node_id)

        return in_radius


class TimelessValueCalculator:
    """
    Calculator for timeless jewel value at different sockets.

    This class evaluates the value of timeless jewel transformations
    to help optimize jewel placement and seed selection.

    Usage:
        from src.pob.jewel.timeless_value import TimelessValueCalculator
        from src.pob.jewel.timeless_data import get_default_loader

        loader = get_default_loader()
        calc = TimelessValueCalculator(loader, tree)

        analysis = calc.analyze_socket(jewel, socket_id, allocated_nodes, "DPS")
        print(f"Total value: {analysis.total_value}")
    """

    def __init__(
        self,
        data_loader: TimelessJewelDataLoader,
        tree: "PassiveTreeGraph",
        radius_calc: Optional[RadiusCalculator] = None,
    ):
        """
        Initialize the calculator.

        Args:
            data_loader: The timeless jewel data loader
            tree: The passive tree graph
            radius_calc: Optional radius calculator (uses SimpleRadiusCalculator if not provided)
        """
        self.data_loader = data_loader
        self.tree = tree

        if radius_calc is not None:
            self.radius_calc = radius_calc
        else:
            self.radius_calc = SimpleRadiusCalculator(tree)

    def analyze_socket(
        self,
        jewel: "TimelessJewel",
        socket_id: int,
        allocated_nodes: Set[int],
        objective: str,
    ) -> TimelessSocketAnalysis:
        """
        Analyze timeless jewel value at a socket.

        Args:
            jewel: The timeless jewel
            socket_id: The socket node ID to analyze
            allocated_nodes: Currently allocated passive nodes
            objective: Optimization objective (DPS, Life, EHP)

        Returns:
            Analysis results including total value and best nodes
        """
        # Get nodes in radius
        affected_nodes = self.radius_calc.get_nodes_in_radius(socket_id, JewelRadius.LARGE)

        # Get transformations for allocated nodes in radius
        allocated_in_radius = affected_nodes & allocated_nodes

        transformations = self.data_loader.get_transformations(
            jewel.jewel_type,
            jewel.seed,
            allocated_in_radius
        )

        # Score each transformation
        stat_weights = get_stat_weights(objective)
        node_values: List[Tuple[int, float]] = []

        for node_id, transform in transformations.items():
            value = self.score_transformation(transform, objective, stat_weights)
            node_values.append((node_id, value))

        # Sort by value descending
        node_values.sort(key=lambda x: x[1], reverse=True)

        # Calculate total value
        total_value = sum(v for _, v in node_values)

        # Calculate pathing cost (simplified - just count unallocated nodes)
        # A more sophisticated approach would use actual path finding
        pathing_cost = self._estimate_pathing_cost(socket_id, allocated_nodes)

        return TimelessSocketAnalysis(
            socket_node_id=socket_id,
            affected_nodes=affected_nodes,
            transformations=transformations,
            total_value=total_value,
            best_nodes=node_values[:10],  # Top 10
            pathing_cost=pathing_cost,
        )

    def compare_sockets(
        self,
        jewel: "TimelessJewel",
        socket_ids: Set[int],
        allocated_nodes: Set[int],
        objective: str,
    ) -> List[TimelessSocketAnalysis]:
        """
        Compare multiple sockets for a timeless jewel.

        Args:
            jewel: The timeless jewel
            socket_ids: Set of socket node IDs to compare
            allocated_nodes: Currently allocated passive nodes
            objective: Optimization objective

        Returns:
            List of analyses sorted by total value (best first)
        """
        analyses = []

        for socket_id in socket_ids:
            analysis = self.analyze_socket(
                jewel, socket_id, allocated_nodes, objective
            )
            analyses.append(analysis)

        # Sort by value descending
        analyses.sort(key=lambda a: a.total_value, reverse=True)

        return analyses

    def score_transformation(
        self,
        transform: TimelessTransformation,
        objective: str,
        stat_weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Score a single transformation for an objective.

        Args:
            transform: The transformation to score
            objective: The optimization objective
            stat_weights: Optional pre-computed stat weights

        Returns:
            Numeric score for the transformation
        """
        if stat_weights is None:
            stat_weights = get_stat_weights(objective)

        total_score = 0.0

        for mod in transform.mods:
            weight = stat_weights.get(mod.stat_id, 0.0)

            # Use stat value if available
            if mod.stat_value > 0:
                total_score += weight * mod.stat_value
            else:
                # Default contribution if no value
                total_score += weight * 10.0

        return total_score

    def _estimate_pathing_cost(
        self,
        socket_id: int,
        allocated_nodes: Set[int]
    ) -> int:
        """
        Estimate the pathing cost to reach a socket.

        This is a simplified calculation - a more accurate version
        would use actual shortest path finding.

        Args:
            socket_id: The socket node ID
            allocated_nodes: Currently allocated nodes

        Returns:
            Estimated number of additional nodes needed
        """
        if socket_id in allocated_nodes:
            return 0

        # Check if socket is adjacent to allocated nodes
        neighbors = self.tree.get_neighbors(socket_id)
        if any(n in allocated_nodes for n in neighbors):
            return 1

        # Simple BFS to find shortest path
        visited = {socket_id}
        queue = [(socket_id, 0)]

        while queue:
            current, depth = queue.pop(0)

            if depth > 10:  # Max search depth
                break

            for neighbor in self.tree.get_neighbors(current):
                if neighbor in allocated_nodes:
                    return depth + 1

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return 10  # Max if not found

    def find_best_seed(
        self,
        jewel_type: str,
        socket_id: int,
        allocated_nodes: Set[int],
        objective: str,
        seed_range: Optional[Tuple[int, int]] = None,
        sample_count: int = 100,
    ) -> List[Tuple[int, float]]:
        """
        Find the best seeds for a jewel type at a socket.

        This samples seeds within the valid range and returns the
        top performers. For a more thorough search, increase sample_count.

        Args:
            jewel_type: The jewel type (e.g., "Lethal Pride")
            socket_id: The socket to analyze
            allocated_nodes: Currently allocated nodes
            objective: Optimization objective
            seed_range: Optional (min, max) seed range to search
            sample_count: Number of seeds to sample

        Returns:
            List of (seed, value) tuples sorted by value
        """
        from .timeless_data import JEWEL_TYPE_IDS, SEED_RANGES

        # Get seed range for jewel type
        type_id = JEWEL_TYPE_IDS.get(jewel_type.replace(" ", ""))
        if type_id is None:
            return []

        min_seed, max_seed = SEED_RANGES[type_id]

        # For Elegant Hubris, seeds are multiples of 20
        seed_step = 20 if type_id == 5 else 1
        min_seed *= seed_step
        max_seed *= seed_step

        if seed_range:
            min_seed = max(min_seed, seed_range[0])
            max_seed = min(max_seed, seed_range[1])

        # Sample seeds
        import random
        total_seeds = (max_seed - min_seed) // seed_step + 1
        if total_seeds <= sample_count:
            seeds = list(range(min_seed, max_seed + 1, seed_step))
        else:
            seeds = random.sample(range(min_seed, max_seed + 1, seed_step), sample_count)

        # Get nodes in radius
        affected_nodes = self.radius_calc.get_nodes_in_radius(socket_id, JewelRadius.LARGE)
        allocated_in_radius = affected_nodes & allocated_nodes

        # Evaluate each seed
        seed_values: List[Tuple[int, float]] = []
        stat_weights = get_stat_weights(objective)

        for seed in seeds:
            transformations = self.data_loader.get_transformations(
                jewel_type, seed, allocated_in_radius
            )

            total_value = sum(
                self.score_transformation(t, objective, stat_weights)
                for t in transformations.values()
            )

            seed_values.append((seed, total_value))

        # Sort by value
        seed_values.sort(key=lambda x: x[1], reverse=True)

        return seed_values


def create_value_calculator(
    tree: "PassiveTreeGraph",
    data_dir: Optional[str] = None,
) -> TimelessValueCalculator:
    """
    Create a value calculator with default settings.

    Args:
        tree: The passive tree graph
        data_dir: Optional path to TimelessJewelData directory

    Returns:
        Configured TimelessValueCalculator
    """
    if data_dir:
        loader = TimelessJewelDataLoader(data_dir)
    else:
        loader = get_default_loader()

    return TimelessValueCalculator(loader, tree)

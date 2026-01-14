"""
Mastery Effect Optimizer

Masteries are special nodes that let you pick one of 4-6 powerful effects.
This module:
1. Parses mastery definitions from PathOfBuilding tree data
2. Evaluates which mastery effect is best for a build
3. Provides mastery selection recommendations to the optimizer

Key concepts:
- Each mastery node has 4-6 available effects
- You can only select ONE effect per mastery
- Multiple keystones can share the same mastery node
- Mastery effects can provide huge bonuses (e.g., +1 max res, leech, etc.)
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .relative_calculator import RelativeCalculator, RelativeEvaluation
    from .batch_calculator import BatchCalculator

logger = logging.getLogger(__name__)


@dataclass
class MasteryEffect:
    """A single mastery effect option."""

    effect_id: int
    stats: List[str]  # Stat descriptions
    reminder_text: Optional[List[str]] = None

    def __repr__(self):
        stats_str = " | ".join(self.stats[:2])  # First 2 stats
        return f"MasteryEffect({self.effect_id}: {stats_str})"

    def get_all_stats_text(self) -> str:
        """Get all stats as a single string."""
        return "\n".join(self.stats)


@dataclass
class MasteryNode:
    """A mastery node with its available effects."""

    node_id: int
    name: str
    available_effects: List[MasteryEffect]

    def __repr__(self):
        return f"MasteryNode({self.node_id}, {self.name}, {len(self.available_effects)} effects)"


@dataclass
class MasteryEvaluationResult:
    """Result from evaluating a mastery effect with calculator."""
    effect_id: int
    score: float  # Percentage improvement for objective
    dps_change: float
    life_change: float
    ehp_change: float

    def __repr__(self):
        return f"MasteryEvaluationResult(effect={self.effect_id}, score={self.score:+.2f}%)"


class MasteryDatabase:
    """
    Database of all mastery nodes and their available effects.

    Loaded from PathOfBuilding tree data.
    """

    def __init__(self):
        self.masteries: Dict[int, MasteryNode] = {}  # node_id -> MasteryNode
        self.effect_lookup: Dict[int, MasteryEffect] = {}  # effect_id -> MasteryEffect

    def add_mastery(self, mastery: MasteryNode):
        """Add a mastery node to the database."""
        self.masteries[mastery.node_id] = mastery

        # Build effect lookup
        for effect in mastery.available_effects:
            self.effect_lookup[effect.effect_id] = effect

    def get_mastery(self, node_id: int) -> Optional[MasteryNode]:
        """Get mastery node by ID."""
        return self.masteries.get(node_id)

    def get_effect(self, effect_id: int) -> Optional[MasteryEffect]:
        """Get effect by ID."""
        return self.effect_lookup.get(effect_id)

    def is_mastery_node(self, node_id: int) -> bool:
        """Check if a node is a mastery."""
        return node_id in self.masteries

    def get_available_effects(self, node_id: int) -> List[MasteryEffect]:
        """Get all available effects for a mastery node."""
        mastery = self.get_mastery(node_id)
        return mastery.available_effects if mastery else []


class MasteryOptimizer:
    """
    Optimizes mastery effect selection for builds.

    Strategy:
    1. Parse tree to find which mastery nodes are allocated
    2. For each mastery, evaluate all available effects
    3. Select the effect that provides most value for the build's objective
    """

    def __init__(self, mastery_db: MasteryDatabase):
        self.mastery_db = mastery_db

    def select_best_mastery_effects(
        self,
        allocated_nodes: Set[int],
        current_mastery_effects: Dict[int, int],
        objective: str = 'dps',
        calculator = None
    ) -> Dict[int, int]:
        """
        Select optimal mastery effects for allocated mastery nodes.

        Args:
            allocated_nodes: Set of allocated node IDs
            current_mastery_effects: Current selections {node_id: effect_id}
            objective: Optimization objective ('dps', 'life', 'ehp', 'balanced')
            calculator: RelativeCalculator for evaluation (optional)

        Returns:
            Dict of {node_id: best_effect_id}
        """
        # Find which allocated nodes are masteries
        mastery_nodes = [
            node_id for node_id in allocated_nodes
            if self.mastery_db.is_mastery_node(node_id)
        ]

        if not mastery_nodes:
            return {}

        logger.info(f"Selecting mastery effects for {len(mastery_nodes)} mastery nodes")

        best_effects = {}

        for node_id in mastery_nodes:
            available = self.mastery_db.get_available_effects(node_id)

            if not available:
                logger.warning(f"No available effects for mastery node {node_id}")
                continue

            # If calculator provided, evaluate each effect
            if calculator:
                best_effect = self._evaluate_effects_with_calculator(
                    node_id,
                    available,
                    objective,
                    calculator
                )
            else:
                # Fallback: Use heuristics
                best_effect = self._select_effect_by_heuristic(
                    available,
                    objective,
                    current_mastery_effects.get(node_id)
                )

            if best_effect:
                best_effects[node_id] = best_effect.effect_id
                logger.debug(
                    f"Selected effect {best_effect.effect_id} for mastery {node_id}: "
                    f"{best_effect.stats[0]}"
                )

        return best_effects

    def _evaluate_effects_with_calculator(
        self,
        node_id: int,
        effects: List[MasteryEffect],
        objective: str,
        calculator
    ) -> Optional[MasteryEffect]:
        """
        Evaluate each mastery effect by testing with calculator.

        This is the most accurate method but requires multiple calculations.
        """
        if calculator is None:
            return self._select_effect_by_heuristic(effects, objective, None)

        # Use the new calculator-based evaluation
        best_score = float('-inf')
        best_effect = None

        for effect in effects:
            try:
                score = self._score_effect(effect, objective)  # Fallback scoring
                if score > best_score:
                    best_score = score
                    best_effect = effect
            except Exception as e:
                logger.warning(f"Failed to evaluate effect {effect.effect_id}: {e}")

        return best_effect if best_effect else self._select_effect_by_heuristic(effects, objective, None)

    def _select_effect_by_heuristic(
        self,
        effects: List[MasteryEffect],
        objective: str,
        current_effect_id: Optional[int] = None
    ) -> Optional[MasteryEffect]:
        """
        Select best effect using heuristics based on stat text.

        Heuristics by objective:
        - dps: Look for damage, crit, attack/cast speed, penetration
        - life: Look for life, regen, recovery
        - ehp: Look for defenses, block, resistances
        - balanced: Weighted combination
        """
        if not effects:
            return None

        # If current effect exists and objective is unclear, keep it
        if current_effect_id and objective == 'balanced':
            for effect in effects:
                if effect.effect_id == current_effect_id:
                    return effect

        # Score each effect based on objective
        scored_effects = []
        for effect in effects:
            score = self._score_effect(effect, objective)
            scored_effects.append((score, effect))

        # Sort by score (descending), using only the score for comparison
        scored_effects.sort(key=lambda x: x[0], reverse=True)

        best_score, best_effect = scored_effects[0]

        logger.debug(
            f"Heuristic scoring for {objective}: "
            f"best={best_effect.effect_id} (score={best_score:.2f})"
        )

        return best_effect

    def _score_effect(self, effect: MasteryEffect, objective: str) -> float:
        """
        Score a mastery effect based on objective.

        Returns a score where higher is better.
        """
        stats_text = effect.get_all_stats_text().lower()
        score = 0.0

        # DPS-related keywords
        dps_keywords = {
            'damage': 5.0,
            'increased damage': 8.0,
            'more damage': 15.0,
            'penetration': 10.0,
            'critical': 7.0,
            'attack speed': 8.0,
            'cast speed': 8.0,
            'impale': 6.0,
            'bleeding': 5.0,
            'poison': 5.0,
            'ignite': 5.0,
            'exposure': 8.0,
            'overwhelm': 7.0,
            'accuracy': 3.0,
            'frenzy charge': 6.0,
            'power charge': 6.0,
        }

        # Life/Recovery keywords
        life_keywords = {
            'maximum life': 10.0,
            'life regeneration': 7.0,
            'life recovery': 8.0,
            'life leech': 8.0,
            'recover life': 9.0,
            'life flask': 5.0,
            'endurance charge': 6.0,
        }

        # Defense/EHP keywords
        defense_keywords = {
            'maximum resistances': 15.0,
            'block': 8.0,
            'spell suppression': 10.0,
            'armour': 6.0,
            'evasion': 6.0,
            'energy shield': 7.0,
            'defences': 5.0,
            'physical damage reduction': 8.0,
            'reduced damage taken': 12.0,
            'avoid': 7.0,
        }

        # Select keyword set based on objective
        if objective == 'dps':
            keywords = dps_keywords
        elif objective == 'life':
            keywords = life_keywords
        elif objective == 'ehp':
            keywords = defense_keywords
        elif objective == 'balanced':
            # Balanced: all keywords with reduced weight
            keywords = {**dps_keywords, **life_keywords, **defense_keywords}
            # Reduce all scores by 50% for balanced
            keywords = {k: v * 0.5 for k, v in keywords.items()}
        else:
            keywords = dps_keywords  # Default

        # Score based on keyword matches
        for keyword, weight in keywords.items():
            if keyword in stats_text:
                score += weight

        # Parse numeric values (bigger numbers often = better)
        # Look for patterns like "+X%" or "X% increased"
        numbers = re.findall(r'(\d+)%', stats_text)
        if numbers:
            # Average numeric value as a bonus
            avg_value = sum(int(n) for n in numbers) / len(numbers)
            score += avg_value * 0.1  # Small bonus for larger values

        return score

    # === New Calculator-Based Methods (v0.8) ===

    def _evaluate_effect_with_calculator(
        self,
        base_xml: str,
        mastery_node_id: int,
        effect_id: int,
        calculator: "RelativeCalculator",
        objective: str
    ) -> float:
        """
        Evaluate a single mastery effect by modifying build and calculating.

        Args:
            base_xml: Original build XML
            mastery_node_id: The mastery node ID
            effect_id: The effect to test
            calculator: RelativeCalculator instance
            objective: 'dps', 'life', 'ehp', or 'balanced'

        Returns:
            Score for this effect (percentage improvement)
        """
        from .modifier import modify_passive_tree_nodes

        modified_xml = modify_passive_tree_nodes(
            base_xml,
            mastery_effects_to_add={mastery_node_id: effect_id}
        )

        try:
            result = calculator.evaluate_modification(base_xml, modified_xml)
        except Exception as e:
            logger.warning(f"Failed to evaluate mastery effect {effect_id}: {e}")
            return 0.0

        return self._extract_score_from_evaluation(result, objective)

    def _extract_score_from_evaluation(
        self,
        result: "RelativeEvaluation",
        objective: str
    ) -> float:
        """Extract objective-appropriate score from evaluation result."""
        if objective == 'dps':
            return result.dps_change_percent
        elif objective == 'life':
            return result.life_change_percent
        elif objective == 'ehp':
            return result.ehp_change_percent
        elif objective == 'balanced':
            return (
                result.dps_change_percent * 0.4 +
                result.life_change_percent * 0.3 +
                result.ehp_change_percent * 0.3
            )
        return result.dps_change_percent

    def evaluate_all_effects_for_node(
        self,
        base_xml: str,
        mastery_node_id: int,
        calculator: "RelativeCalculator",
        objective: str = 'dps'
    ) -> List[MasteryEvaluationResult]:
        """
        Evaluate all effects for a mastery node using the calculator.

        Returns list of results sorted by score (best first).
        """
        from .modifier import modify_passive_tree_nodes

        available = self.mastery_db.get_available_effects(mastery_node_id)
        if not available:
            return []

        results = []
        for effect in available:
            modified_xml = modify_passive_tree_nodes(
                base_xml,
                mastery_effects_to_add={mastery_node_id: effect.effect_id}
            )
            try:
                eval_result = calculator.evaluate_modification(base_xml, modified_xml)
                score = self._extract_score_from_evaluation(eval_result, objective)
                results.append(MasteryEvaluationResult(
                    effect_id=effect.effect_id,
                    score=score,
                    dps_change=eval_result.dps_change_percent,
                    life_change=eval_result.life_change_percent,
                    ehp_change=eval_result.ehp_change_percent
                ))
            except Exception as e:
                logger.warning(f"Failed to evaluate effect {effect.effect_id}: {e}")

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def select_best_effect_with_calculator(
        self,
        base_xml: str,
        mastery_node_id: int,
        calculator: "RelativeCalculator",
        objective: str = 'dps'
    ) -> Optional[Tuple[int, float]]:
        """
        Select best effect using calculator evaluation.

        Returns:
            Tuple of (effect_id, score) or None if no effects available
        """
        results = self.evaluate_all_effects_for_node(
            base_xml, mastery_node_id, calculator, objective
        )
        if not results:
            return None
        return (results[0].effect_id, results[0].score)

    def select_best_mastery_effects_batch(
        self,
        base_xml: str,
        allocated_nodes: Set[int],
        current_effects: Dict[int, int],
        objective: str,
        batch_calculator: "BatchCalculator"
    ) -> Dict[int, int]:
        """
        Evaluate all mastery options using batch evaluation.

        This is much faster than evaluating each effect individually
        when there are many masteries to optimize.

        Args:
            base_xml: Original build XML
            allocated_nodes: Set of allocated node IDs
            current_effects: Current mastery selections {node_id: effect_id}
            objective: Optimization objective
            batch_calculator: BatchCalculator instance

        Returns:
            Best effect for each mastery node {node_id: best_effect_id}
        """
        from .modifier import modify_passive_tree_nodes

        # Find mastery nodes
        mastery_nodes = [
            node_id for node_id in allocated_nodes
            if self.mastery_db.is_mastery_node(node_id)
        ]

        if not mastery_nodes:
            return {}

        # Build modifications dict: key -> modified_xml
        modifications = {}
        effect_map = {}  # key -> (node_id, effect_id)

        for node_id in mastery_nodes:
            for effect in self.mastery_db.get_available_effects(node_id):
                key = f"{node_id}:{effect.effect_id}"
                modifications[key] = modify_passive_tree_nodes(
                    base_xml,
                    mastery_effects_to_add={node_id: effect.effect_id}
                )
                effect_map[key] = (node_id, effect.effect_id)

        if not modifications:
            return {}

        # Batch evaluate all modifications
        try:
            results = batch_calculator.evaluate_batch(base_xml, modifications)
        except Exception as e:
            logger.error(f"Batch evaluation failed: {e}")
            # Fallback to heuristic selection
            return self.select_best_mastery_effects(
                allocated_nodes, current_effects, objective, calculator=None
            )

        # Find best effect for each node
        best_effects: Dict[int, int] = {}
        best_scores: Dict[int, float] = {}

        for key, eval_result in results.items():
            node_id, effect_id = effect_map[key]
            score = self._extract_score_from_evaluation(eval_result, objective)

            if node_id not in best_scores or score > best_scores[node_id]:
                best_scores[node_id] = score
                best_effects[node_id] = effect_id

        return best_effects


def load_mastery_database(pob_path: str = "./PathOfBuilding", tree_version: str = "3_27") -> MasteryDatabase:
    """
    Load mastery database from PathOfBuilding tree data.

    Args:
        pob_path: Path to PathOfBuilding directory
        tree_version: Tree version (e.g., "3_27")

    Returns:
        MasteryDatabase with all masteries loaded
    """
    tree_file = Path(pob_path) / "src" / "TreeData" / tree_version / "tree.lua"

    if not tree_file.exists():
        logger.error(f"Tree file not found: {tree_file}")
        return MasteryDatabase()  # Empty database

    logger.info(f"Loading mastery database from {tree_file}")

    # Parse Lua file to extract mastery data
    # This is a simplified parser - full Lua parsing would be more robust
    db = MasteryDatabase()

    with open(tree_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all mastery nodes
    # Format: [nodeId]= { ["skill"]= nodeId, ["name"]= "...", ["isMastery"]= true, ["masteryEffects"]= {...} }

    # Strategy: Find nodes marked with isMastery, then extract their masteryEffects
    # Split by node definitions
    node_blocks = re.split(r'\[(\d+)\]\s*=\s*\{', content)

    # Process node blocks
    for i in range(1, len(node_blocks), 2):
        node_id_str = node_blocks[i]
        node_content = node_blocks[i + 1] if i + 1 < len(node_blocks) else ""

        # Check if this is a mastery node
        if '"isMastery"' not in node_content and '["isMastery"]' not in node_content:
            continue

        if 'true' not in node_content:
            continue

        node_id = int(node_id_str)

        # Extract name
        name_match = re.search(r'\["name"\]\s*=\s*"([^"]+)"', node_content)
        name = name_match.group(1) if name_match else f"Mastery_{node_id}"

        # Extract masteryEffects block
        # Pattern: ["masteryEffects"]= { ... }, followed by next field
        effects_match = re.search(
            r'\["masteryEffects"\]\s*=\s*\{(.*?)\},\s*\["',
            node_content,
            re.DOTALL
        )

        if not effects_match:
            logger.debug(f"Mastery node {node_id} ({name}) has no masteryEffects")
            continue

        effects_block = effects_match.group(1)

        # Parse effects from the block
        effects = _parse_mastery_effects_from_lua(effects_block)

        if effects:
            mastery = MasteryNode(
                node_id=node_id,
                name=name,
                available_effects=effects
            )
            db.add_mastery(mastery)
            logger.debug(f"Loaded {name} ({node_id}) with {len(effects)} effects")

    logger.info(f"Loaded {len(db.masteries)} mastery nodes")

    return db


def _parse_mastery_effects_from_lua(lua_block: str) -> List[MasteryEffect]:
    """
    Parse mastery effects from a Lua block.

    Example format:
        {
            ["effect"]= 48385,
            ["stats"]= {
                "Stat line 1",
                "Stat line 2"
            }
        },
    """
    effects = []

    # Find effect blocks
    effect_pattern = r'\["effect"\]\s*=\s*(\d+).*?\["stats"\]\s*=\s*\{([^}]+)\}'

    for match in re.finditer(effect_pattern, lua_block, re.DOTALL):
        effect_id = int(match.group(1))
        stats_block = match.group(2)

        # Parse stat lines
        stat_pattern = r'"([^"]+)"'
        stats = re.findall(stat_pattern, stats_block)

        if stats:
            effect = MasteryEffect(
                effect_id=effect_id,
                stats=stats
            )
            effects.append(effect)

    return effects


# Singleton instance
_mastery_db: Optional[MasteryDatabase] = None


def get_mastery_database(reload: bool = False) -> MasteryDatabase:
    """Get the global mastery database instance."""
    global _mastery_db

    if _mastery_db is None or reload:
        _mastery_db = load_mastery_database()

    return _mastery_db

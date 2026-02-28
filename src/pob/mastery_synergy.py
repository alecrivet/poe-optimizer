"""
Mastery Synergy Detection

Detects synergies between mastery effects where combined value
exceeds the sum of individual values.

Synergy types:
- additive: Effects add together linearly
- multiplicative: Effects multiply together
- enabling: One effect enables/enhances another
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple, TYPE_CHECKING
from itertools import combinations

if TYPE_CHECKING:
    from .relative_calculator import RelativeCalculator

from .mastery_optimizer import BALANCED_OBJECTIVE_WEIGHTS

logger = logging.getLogger(__name__)


@dataclass
class MasterySynergy:
    """Represents a synergy between two mastery effects."""
    effect_ids: Tuple[int, int]
    synergy_type: str  # 'additive', 'multiplicative', 'enabling'
    combined_value: float
    individual_sum: float
    synergy_bonus: float  # combined - individual_sum

    def __repr__(self):
        return (
            f"MasterySynergy({self.effect_ids}, type={self.synergy_type}, "
            f"bonus={self.synergy_bonus:+.2f}%)"
        )


class MasterySynergyDetector:
    """
    Detects synergies between allocated mastery effects.

    A synergy exists when the combined effect of two masteries
    exceeds the sum of their individual contributions.
    """

    def __init__(self):
        self._cache = {}

    def detect_synergies(
        self,
        build_xml: str,
        mastery_effects: Dict[int, int],
        calculator: "RelativeCalculator",
        threshold: float = 0.5,
        objective: str = 'dps'
    ) -> List[MasterySynergy]:
        """
        Detect synergies between allocated mastery effects.

        Args:
            build_xml: Original build XML
            mastery_effects: Current mastery selections {node_id: effect_id}
            calculator: RelativeCalculator instance
            threshold: Minimum synergy bonus % to report
            objective: 'dps', 'life', 'ehp', or 'balanced'

        Returns:
            List of detected synergies above threshold
        """
        from .modifier import modify_passive_tree_nodes

        if len(mastery_effects) < 2:
            return []

        synergies = []
        effect_ids = list(mastery_effects.values())

        # Create mapping from effect_id to node_id
        effect_to_node = {v: k for k, v in mastery_effects.items()}

        # Evaluate each effect individually
        individual_scores = {}
        for node_id, effect_id in mastery_effects.items():
            modified_xml = modify_passive_tree_nodes(
                build_xml,
                mastery_effects_to_add={node_id: effect_id}
            )
            try:
                result = calculator.evaluate_modification(build_xml, modified_xml)
                individual_scores[effect_id] = self._get_score(result, objective)
            except Exception as e:
                logger.warning(f"Failed to evaluate effect {effect_id}: {e}")
                individual_scores[effect_id] = 0.0

        # Test pairs for synergies
        for (eff1, eff2) in combinations(effect_ids, 2):
            node1 = effect_to_node[eff1]
            node2 = effect_to_node[eff2]

            # Evaluate combined effect
            combined_xml = modify_passive_tree_nodes(
                build_xml,
                mastery_effects_to_add={node1: eff1, node2: eff2}
            )

            try:
                combined_result = calculator.evaluate_modification(
                    build_xml, combined_xml
                )
                combined_score = self._get_score(combined_result, objective)
            except Exception:
                continue

            individual_sum = individual_scores.get(eff1, 0) + individual_scores.get(eff2, 0)
            synergy_bonus = combined_score - individual_sum

            if synergy_bonus >= threshold:
                synergy_type = self._classify_synergy(
                    individual_scores.get(eff1, 0),
                    individual_scores.get(eff2, 0),
                    combined_score
                )

                synergies.append(MasterySynergy(
                    effect_ids=(eff1, eff2),
                    synergy_type=synergy_type,
                    combined_value=combined_score,
                    individual_sum=individual_sum,
                    synergy_bonus=synergy_bonus
                ))

        # Sort by synergy bonus
        synergies.sort(key=lambda x: x.synergy_bonus, reverse=True)
        return synergies

    def _get_score(self, result, objective: str) -> float:
        """Extract score from evaluation result."""
        if objective == 'dps':
            return result.dps_change_percent
        elif objective == 'life':
            return result.life_change_percent
        elif objective == 'ehp':
            return result.ehp_change_percent
        elif objective == 'balanced':
            return (
                result.dps_change_percent * BALANCED_OBJECTIVE_WEIGHTS['dps'] +
                result.life_change_percent * BALANCED_OBJECTIVE_WEIGHTS['life'] +
                result.ehp_change_percent * BALANCED_OBJECTIVE_WEIGHTS['ehp']
            )
        return result.dps_change_percent

    def _classify_synergy(
        self,
        score1: float,
        score2: float,
        combined: float
    ) -> str:
        """Classify synergy type based on value relationships."""
        individual_sum = score1 + score2

        if individual_sum == 0:
            return 'enabling'

        ratio = combined / individual_sum if individual_sum != 0 else 1.0

        if ratio > 1.5:
            return 'multiplicative'
        elif score1 == 0 or score2 == 0:
            return 'enabling'
        else:
            return 'additive'

"""
Extended Objectives for Multi-Objective Optimization

Adds support for additional objectives beyond DPS/Life/EHP:
- Mana efficiency (unreserved mana, regen)
- Energy shield (total ES, recharge rate)
- Block chance (attack/spell block)
- Clear speed (movement speed, attack speed, AoE)
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from ..pob.relative_calculator import RelativeEvaluation
from ..pob.xml_parser import parse_pob_stats

logger = logging.getLogger(__name__)


@dataclass
class ExtendedObjectiveScore:
    """
    Extended multi-objective score with additional objectives.

    Attributes:
        dps_percent: DPS improvement %
        life_percent: Life improvement %
        ehp_percent: EHP improvement %
        mana_percent: Mana efficiency improvement %
        es_percent: Energy shield improvement %
        block_percent: Block chance improvement %
        clear_speed_percent: Clear speed improvement %
        evaluation: Full evaluation details
    """
    dps_percent: float
    life_percent: float
    ehp_percent: float
    mana_percent: Optional[float] = None
    es_percent: Optional[float] = None
    block_percent: Optional[float] = None
    clear_speed_percent: Optional[float] = None
    evaluation: Optional[RelativeEvaluation] = None

    def dominates(self, other: 'ExtendedObjectiveScore', objectives: List[str]) -> bool:
        """
        Check Pareto dominance for selected objectives.

        Args:
            other: Another score
            objectives: List of objective names to consider

        Returns:
            True if this dominates other
        """
        better_or_equal_count = 0
        strictly_better_count = 0

        for obj in objectives:
            self_value = getattr(self, f'{obj}_percent', 0) or 0
            other_value = getattr(other, f'{obj}_percent', 0) or 0

            if self_value >= other_value:
                better_or_equal_count += 1
            if self_value > other_value:
                strictly_better_count += 1

        # Dominates if >= in all AND > in at least one
        return (better_or_equal_count == len(objectives) and
                strictly_better_count > 0)

    def get_objective_value(self, objective: str) -> float:
        """Get value for a specific objective."""
        return getattr(self, f'{objective}_percent', 0) or 0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'dps': self.dps_percent,
            'life': self.life_percent,
            'ehp': self.ehp_percent,
            'mana': self.mana_percent,
            'es': self.es_percent,
            'block': self.block_percent,
            'clear_speed': self.clear_speed_percent,
        }

    def __repr__(self) -> str:
        parts = [
            f"DPS={self.dps_percent:+.1f}%",
            f"Life={self.life_percent:+.1f}%",
            f"EHP={self.ehp_percent:+.1f}%",
        ]

        if self.mana_percent is not None:
            parts.append(f"Mana={self.mana_percent:+.1f}%")
        if self.es_percent is not None:
            parts.append(f"ES={self.es_percent:+.1f}%")
        if self.block_percent is not None:
            parts.append(f"Block={self.block_percent:+.1f}%")
        if self.clear_speed_percent is not None:
            parts.append(f"Speed={self.clear_speed_percent:+.1f}%")

        return f"ExtendedScore({', '.join(parts)})"


def calculate_mana_metrics(xml: str) -> Dict[str, float]:
    """
    Calculate mana-related metrics from build XML.

    Returns:
        Dict with keys: total_mana, unreserved_mana, mana_regen, mana_reserved_percent
    """
    try:
        stats = parse_pob_stats(xml)

        # Extract mana stats
        total_mana = stats.get('Mana', 0)
        mana_reserved = stats.get('ManaReserved', 0)
        mana_regen = stats.get('ManaRegen', 0)

        unreserved_mana = total_mana - mana_reserved
        reserved_percent = (mana_reserved / total_mana * 100) if total_mana > 0 else 0

        return {
            'total_mana': total_mana,
            'unreserved_mana': unreserved_mana,
            'mana_regen': mana_regen,
            'mana_reserved_percent': reserved_percent,
        }
    except Exception as e:
        logger.debug(f"Could not calculate mana metrics: {e}")
        return {}


def calculate_es_metrics(xml: str) -> Dict[str, float]:
    """
    Calculate energy shield metrics from build XML.

    Returns:
        Dict with keys: total_es, es_percent_of_life, es_recharge_rate
    """
    try:
        stats = parse_pob_stats(xml)

        # Extract ES stats
        total_es = stats.get('EnergyShield', 0)
        total_life = stats.get('Life', 0)
        es_recharge = stats.get('EnergyShieldRecharge', 0)

        es_percent = (total_es / total_life * 100) if total_life > 0 else 0

        return {
            'total_es': total_es,
            'es_percent_of_life': es_percent,
            'es_recharge_rate': es_recharge,
        }
    except Exception as e:
        logger.debug(f"Could not calculate ES metrics: {e}")
        return {}


def calculate_block_metrics(xml: str) -> Dict[str, float]:
    """
    Calculate block chance metrics from build XML.

    Returns:
        Dict with keys: attack_block, spell_block, block_recovery
    """
    try:
        stats = parse_pob_stats(xml)

        # Extract block stats
        attack_block = stats.get('BlockChance', 0)
        spell_block = stats.get('SpellBlockChance', 0)
        block_recovery = stats.get('BlockRecovery', 0)

        return {
            'attack_block': attack_block,
            'spell_block': spell_block,
            'block_recovery': block_recovery,
        }
    except Exception as e:
        logger.debug(f"Could not calculate block metrics: {e}")
        return {}


def calculate_clear_speed_metrics(xml: str) -> Dict[str, float]:
    """
    Calculate clear speed metrics from build XML.

    Returns:
        Dict with keys: movement_speed, attack_speed, cast_speed, aoe_radius
    """
    try:
        stats = parse_pob_stats(xml)

        # Extract speed stats
        movement_speed = stats.get('MovementSpeed', 0)
        attack_speed = stats.get('AttackRate', 0)
        cast_speed = stats.get('CastRate', 0)
        aoe_radius = stats.get('AreaOfEffectRadius', 0)

        return {
            'movement_speed': movement_speed,
            'attack_speed': attack_speed,
            'cast_speed': cast_speed,
            'aoe_radius': aoe_radius,
        }
    except Exception as e:
        logger.debug(f"Could not calculate clear speed metrics: {e}")
        return {}


def evaluate_extended_objectives(
    original_xml: str,
    modified_xml: str,
    base_evaluation: RelativeEvaluation,
) -> ExtendedObjectiveScore:
    """
    Evaluate all objectives including extended ones.

    Args:
        original_xml: Original build XML
        modified_xml: Modified build XML
        base_evaluation: Base DPS/Life/EHP evaluation

    Returns:
        ExtendedObjectiveScore with all objectives
    """
    # Start with base objectives
    score = ExtendedObjectiveScore(
        dps_percent=base_evaluation.dps_change_percent,
        life_percent=base_evaluation.life_change_percent,
        ehp_percent=base_evaluation.ehp_change_percent,
        evaluation=base_evaluation,
    )

    # Calculate mana improvement
    try:
        original_mana = calculate_mana_metrics(original_xml)
        modified_mana = calculate_mana_metrics(modified_xml)

        if original_mana and modified_mana:
            # Use unreserved mana as primary metric
            orig_unreserved = original_mana.get('unreserved_mana', 0)
            mod_unreserved = modified_mana.get('unreserved_mana', 0)

            if orig_unreserved > 0:
                mana_improvement = (mod_unreserved - orig_unreserved) / orig_unreserved * 100
                score.mana_percent = mana_improvement
    except Exception as e:
        logger.debug(f"Could not calculate mana objective: {e}")

    # Calculate ES improvement
    try:
        original_es = calculate_es_metrics(original_xml)
        modified_es = calculate_es_metrics(modified_xml)

        if original_es and modified_es:
            orig_total = original_es.get('total_es', 0)
            mod_total = modified_es.get('total_es', 0)

            if orig_total > 0:
                es_improvement = (mod_total - orig_total) / orig_total * 100
                score.es_percent = es_improvement
    except Exception as e:
        logger.debug(f"Could not calculate ES objective: {e}")

    # Calculate block improvement
    try:
        original_block = calculate_block_metrics(original_xml)
        modified_block = calculate_block_metrics(modified_xml)

        if original_block and modified_block:
            # Average of attack and spell block
            orig_avg = (original_block.get('attack_block', 0) +
                       original_block.get('spell_block', 0)) / 2
            mod_avg = (modified_block.get('attack_block', 0) +
                      modified_block.get('spell_block', 0)) / 2

            if orig_avg > 0:
                block_improvement = (mod_avg - orig_avg) / orig_avg * 100
                score.block_percent = block_improvement
    except Exception as e:
        logger.debug(f"Could not calculate block objective: {e}")

    # Calculate clear speed improvement
    try:
        original_speed = calculate_clear_speed_metrics(original_xml)
        modified_speed = calculate_clear_speed_metrics(modified_xml)

        if original_speed and modified_speed:
            # Composite score: movement + attack/cast speed + aoe
            orig_composite = (
                original_speed.get('movement_speed', 0) +
                max(original_speed.get('attack_speed', 0),
                    original_speed.get('cast_speed', 0)) +
                original_speed.get('aoe_radius', 0)
            )
            mod_composite = (
                modified_speed.get('movement_speed', 0) +
                max(modified_speed.get('attack_speed', 0),
                    modified_speed.get('cast_speed', 0)) +
                modified_speed.get('aoe_radius', 0)
            )

            if orig_composite > 0:
                speed_improvement = (mod_composite - orig_composite) / orig_composite * 100
                score.clear_speed_percent = speed_improvement
    except Exception as e:
        logger.debug(f"Could not calculate clear speed objective: {e}")

    return score


# Objective definitions for easy reference
CORE_OBJECTIVES = ['dps', 'life', 'ehp']
EXTENDED_OBJECTIVES = ['mana', 'es', 'block', 'clear_speed']
ALL_OBJECTIVES = CORE_OBJECTIVES + EXTENDED_OBJECTIVES

OBJECTIVE_DESCRIPTIONS = {
    'dps': 'Damage Per Second (offense)',
    'life': 'Total Life (survivability)',
    'ehp': 'Effective Hit Points (tankiness)',
    'mana': 'Unreserved Mana (utility)',
    'es': 'Energy Shield (CI/LL builds)',
    'block': 'Block Chance (mitigation)',
    'clear_speed': 'Clear Speed (mapping efficiency)',
}

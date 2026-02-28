"""
Relative Build Calculator - Estimate build modifications using ratio extrapolation

This module provides a way to estimate the impact of build modifications without
requiring perfectly accurate calculations. It works by:

1. Getting accurate baseline stats from XML (pre-calculated by PoB)
2. Calculating RATIO of change using HeadlessWrapper (Lua)
3. Extrapolating estimated real stats using the ratio

Why this works:
- HeadlessWrapper may calculate wrong absolute values (e.g., 42K instead of 3.16M DPS)
- BUT the RATIO of changes is consistent (e.g., +7% DPS is still +7%)
- We use the ratio to extrapolate from the accurate baseline

Limitations:
- Assumes changes scale linearly (mostly true for passive tree, less so for mechanics)
- Not suitable for final validation (use PoB desktop app for that)
- Best for comparing many modifications quickly (optimization)

Future improvements:
- Contribute to PoB to fix HeadlessWrapper for complex mechanics
- Build/use a web API for accurate recalculation
- ML model to predict calculation errors and correct them
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

from .caller import PoBCalculator
from .xml_parser import get_build_summary
from .calculator_utils import (
    extract_build_stats,
    build_evaluation_from_accurate_stats,
    build_evaluation_from_lua,
)

logger = logging.getLogger(__name__)


@dataclass
class RelativeEvaluation:
    """Results from a relative build evaluation."""

    # Baseline (accurate from XML)
    baseline_dps: float
    baseline_life: float
    baseline_ehp: float

    # Estimated (extrapolated)
    estimated_dps: float
    estimated_life: float
    estimated_ehp: float

    # Ratios (from Lua)
    dps_ratio: float
    life_ratio: float
    ehp_ratio: float

    # Changes
    dps_change_percent: float
    life_change_percent: float
    ehp_change_percent: float

    # Raw Lua values (for debugging)
    baseline_lua_dps: float
    modified_lua_dps: float

    def __repr__(self):
        return (
            f"RelativeEvaluation(\n"
            f"  DPS: {self.baseline_dps:,.0f} → {self.estimated_dps:,.0f} "
            f"({self.dps_change_percent:+.1f}%)\n"
            f"  Life: {self.baseline_life:,.0f} → {self.estimated_life:,.0f} "
            f"({self.life_change_percent:+.1f}%)\n"
            f"  EHP: {self.baseline_ehp:,.0f} → {self.estimated_ehp:,.0f} "
            f"({self.ehp_change_percent:+.1f}%)\n"
            f")"
        )


class RelativeCalculator:
    """
    Calculate relative build improvements using ratio extrapolation.

    This calculator uses HeadlessWrapper for relative comparisons while maintaining
    accuracy by extrapolating from XML-based baseline stats.

    Example:
        >>> calc = RelativeCalculator()
        >>> # Get baseline
        >>> original_xml = decode_pob_code(build_code)
        >>> # Modify build
        >>> modified_xml = modify_passive_tree_nodes(
        ...     original_xml,
        ...     nodes_to_add=[12345, 23456]  # Add some DPS nodes
        ... )
        >>> # Evaluate
        >>> result = calc.evaluate_modification(original_xml, modified_xml)
        >>> print(f"DPS change: {result.dps_change_percent:+.1f}%")
        >>> print(f"Estimated DPS: {result.estimated_dps:,.0f}")
    """

    def __init__(self, calibration_factor: float = 1.0, dps_mode: str = "combined"):
        """
        Initialize the relative calculator.

        Args:
            calibration_factor: Adjustment factor for ratio extrapolation.
                               Can be tuned based on empirical testing.
            dps_mode: Which DPS metric to use. "combined" for main skill only,
                      "full" for sum of all skills (useful when supports deal
                      their own damage, e.g. Shockwave).
        """
        self.pob_calc = PoBCalculator()
        self.calibration_factor = calibration_factor
        self.dps_mode = dps_mode
        logger.info("Initialized RelativeCalculator (calibration: %.2f, dps_mode: %s)",
                     calibration_factor, dps_mode)

    def evaluate_modification(
        self,
        original_xml: str,
        modified_xml: str,
        use_lua_fallback: bool = True
    ) -> RelativeEvaluation:
        """
        Evaluate a build modification relative to the original.

        This method:
        1. Gets accurate baseline from original XML
        2. Calculates both builds with Lua
        3. Computes ratio of change
        4. Extrapolates estimated real stats

        Args:
            original_xml: Original build XML
            modified_xml: Modified build XML
            use_lua_fallback: If False, skip Lua and just parse XML stats
                             (useful when modified build also has pre-calculated stats)

        Returns:
            RelativeEvaluation with all stats and ratios

        Example:
            >>> result = calc.evaluate_modification(original, modified)
            >>> if result.dps_change_percent > 5:
            >>>     print("Significant DPS improvement!")
        """
        # Get accurate baseline from original XML
        logger.debug("Parsing accurate baseline from original XML...")
        baseline_accurate = extract_build_stats(get_build_summary(original_xml), self.dps_mode)

        if baseline_accurate.dps == 0 and baseline_accurate.life == 0:
            logger.warning("Baseline XML has no pre-calculated stats! "
                          "Results will be inaccurate.")

        # Try to get stats from modified XML first (if it has pre-calculated stats)
        modified_accurate = extract_build_stats(get_build_summary(modified_xml), self.dps_mode)
        if modified_accurate.dps > 0 and not use_lua_fallback:
            # Modified XML has accurate stats, use them directly
            logger.debug("Using pre-calculated stats from modified XML (no extrapolation needed)")
            return build_evaluation_from_accurate_stats(baseline_accurate, modified_accurate)

        # Calculate both with Lua (use_xml_stats=False to force Lua calculation)
        logger.debug("Calculating baseline with Lua...")
        baseline_lua = extract_build_stats(
            self.pob_calc.evaluate_build(original_xml, use_xml_stats=False),
            self.dps_mode,
        )

        logger.debug("Calculating modified with Lua...")
        modified_lua = extract_build_stats(
            self.pob_calc.evaluate_build(modified_xml, use_xml_stats=False),
            self.dps_mode,
        )

        result = build_evaluation_from_lua(
            baseline_accurate, baseline_lua, modified_lua, self.calibration_factor
        )

        logger.info(
            "Evaluation complete: DPS %+.1f%%, Life %+.1f%%, EHP %+.1f%%",
            result.dps_change_percent, result.life_change_percent, result.ehp_change_percent
        )

        return result

    def compare_modifications(
        self,
        original_xml: str,
        modifications: Dict[str, str]
    ) -> Dict[str, RelativeEvaluation]:
        """
        Compare multiple modifications against the original.

        Useful for quickly ranking different optimization strategies.

        Args:
            original_xml: Original build XML
            modifications: Dict mapping names to modified XMLs

        Returns:
            Dict mapping names to RelativeEvaluation results

        Example:
            >>> mods = {
            ...     "Add 10 life nodes": modified_xml_1,
            ...     "Add 10 DPS nodes": modified_xml_2,
            ...     "Add 5 of each": modified_xml_3,
            ... }
            >>> results = calc.compare_modifications(original, mods)
            >>> best = max(results.items(), key=lambda x: x[1].estimated_dps)
            >>> print(f"Best modification: {best[0]}")
        """
        results = {}

        logger.info(f"Comparing {len(modifications)} modifications...")

        for name, modified_xml in modifications.items():
            logger.debug(f"Evaluating: {name}")
            results[name] = self.evaluate_modification(original_xml, modified_xml)

        logger.info("Comparison complete")
        return results

    def rank_by_objective(
        self,
        comparisons: Dict[str, RelativeEvaluation],
        objective: str = 'dps'
    ) -> list:
        """
        Rank modifications by a specific objective.

        Args:
            comparisons: Results from compare_modifications()
            objective: One of 'dps', 'life', 'ehp', 'balanced'

        Returns:
            List of (name, evaluation) tuples sorted by objective

        Example:
            >>> comparisons = calc.compare_modifications(original, mods)
            >>> ranked = calc.rank_by_objective(comparisons, 'dps')
            >>> print(f"Best DPS build: {ranked[0][0]}")
        """
        if objective == 'dps':
            key_func = lambda x: x[1].estimated_dps
        elif objective == 'life':
            key_func = lambda x: x[1].estimated_life
        elif objective == 'ehp':
            key_func = lambda x: x[1].estimated_ehp
        elif objective == 'balanced':
            # Simple balanced score: normalize and sum
            # This is a placeholder - could be more sophisticated
            key_func = lambda x: (
                x[1].dps_change_percent / 100 +
                x[1].life_change_percent / 100 +
                x[1].ehp_change_percent / 100
            )
        else:
            raise ValueError(f"Unknown objective: {objective}")

        return sorted(comparisons.items(), key=key_func, reverse=True)

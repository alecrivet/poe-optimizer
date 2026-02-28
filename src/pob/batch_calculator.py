"""
Batch Calculator - Fast build evaluation using persistent worker pool.

This module provides BatchCalculator, a drop-in replacement for RelativeCalculator
that uses a pool of persistent PoB workers for much faster evaluation.

Performance improvement:
- RelativeCalculator: ~600ms per evaluation (subprocess startup overhead)
- BatchCalculator: ~100ms per evaluation (reuses initialized workers)
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .worker_pool import PoBWorkerPool, EvaluationResult
from .xml_parser import get_build_summary
from .relative_calculator import RelativeEvaluation
from .calculator_utils import (
    extract_build_stats,
    calculate_ratios,
    build_evaluation_from_accurate_stats,
    build_evaluation_from_lua,
)

logger = logging.getLogger(__name__)


class BatchCalculator:
    """
    Fast build calculator using persistent worker pool.

    Drop-in replacement for RelativeCalculator with the same interface
    but using a pool of pre-initialized PoB workers for faster evaluation.

    Example:
        >>> with BatchCalculator(num_workers=4) as calc:
        >>>     result = calc.evaluate_modification(original_xml, modified_xml)
        >>>     print(f"DPS change: {result.dps_change_percent:+.1f}%")

    Or manage lifecycle manually:
        >>> calc = BatchCalculator(num_workers=4)
        >>> calc.start()
        >>> # ... do evaluations ...
        >>> calc.shutdown()
    """

    def __init__(
        self,
        num_workers: Optional[int] = None,
        calibration_factor: float = 1.0,
        dps_mode: str = "combined",
    ):
        """
        Initialize the batch calculator.

        Args:
            num_workers: Number of worker processes (defaults to CPU count)
            calibration_factor: Adjustment factor for ratio extrapolation
            dps_mode: Which DPS metric to use. "combined" for main skill only,
                      "full" for sum of all skills (useful when supports deal
                      their own damage, e.g. Shockwave).
        """
        self.pool = PoBWorkerPool(num_workers=num_workers)
        self.calibration_factor = calibration_factor
        self.dps_mode = dps_mode
        self._started = False
        logger.info(f"Initialized BatchCalculator (workers: {self.pool.num_workers}, dps_mode: {dps_mode})")

    def start(self) -> int:
        """
        Start the worker pool.

        Returns:
            Number of workers successfully started
        """
        if self._started:
            return self.pool.get_stats()["alive_workers"]

        count = self.pool.start()
        self._started = True
        return count

    def shutdown(self):
        """Shutdown the worker pool."""
        self.pool.shutdown()
        self._started = False

    def evaluate_modification(
        self,
        original_xml: str,
        modified_xml: str,
        use_lua_fallback: bool = True,
    ) -> RelativeEvaluation:
        """
        Evaluate a build modification relative to the original.

        Same interface as RelativeCalculator.evaluate_modification().

        Args:
            original_xml: Original build XML
            modified_xml: Modified build XML
            use_lua_fallback: If False, skip Lua and just parse XML stats

        Returns:
            RelativeEvaluation with all stats and ratios
        """
        if not self._started:
            self.start()

        # Get accurate baseline from original XML
        baseline_accurate = extract_build_stats(get_build_summary(original_xml), self.dps_mode)

        # Try to get stats from modified XML first
        modified_accurate = extract_build_stats(get_build_summary(modified_xml), self.dps_mode)
        if modified_accurate.dps > 0 and not use_lua_fallback:
            # Modified XML has accurate stats, use them directly
            return build_evaluation_from_accurate_stats(baseline_accurate, modified_accurate)

        # Evaluate both builds using worker pool
        baseline_result = self.pool.evaluate(original_xml)
        modified_result = self.pool.evaluate(modified_xml)

        if not baseline_result.success:
            raise RuntimeError(f"Failed to evaluate baseline: {baseline_result.error}")
        if not modified_result.success:
            raise RuntimeError(f"Failed to evaluate modified: {modified_result.error}")

        baseline_lua = extract_build_stats(baseline_result.stats, self.dps_mode)
        modified_lua = extract_build_stats(modified_result.stats, self.dps_mode)

        return build_evaluation_from_lua(
            baseline_accurate, baseline_lua, modified_lua, self.calibration_factor
        )

    def evaluate_batch(
        self,
        original_xml: str,
        modifications: Dict[str, str],
    ) -> Dict[str, RelativeEvaluation]:
        """
        Evaluate multiple modifications in parallel.

        More efficient than calling evaluate_modification() repeatedly
        because it batches the Lua evaluations.

        Args:
            original_xml: Original build XML
            modifications: Dict mapping names to modified XMLs

        Returns:
            Dict mapping names to RelativeEvaluation results
        """
        if not self._started:
            self.start()

        # Get accurate baseline from original XML
        baseline_accurate = extract_build_stats(get_build_summary(original_xml), self.dps_mode)

        # First, evaluate baseline
        baseline_result = self.pool.evaluate(original_xml)
        if not baseline_result.success:
            raise RuntimeError(f"Failed to evaluate baseline: {baseline_result.error}")

        baseline_lua = extract_build_stats(baseline_result.stats, self.dps_mode)

        # Evaluate all modifications in parallel
        names = list(modifications.keys())
        xmls = list(modifications.values())
        results = self.pool.evaluate_batch(xmls)

        # Build result dict
        evaluations = {}
        for name, result, modified_xml in zip(names, results, xmls):
            if not result.success:
                logger.warning(f"Failed to evaluate {name}: {result.error}")
                continue

            modified_lua = extract_build_stats(result.stats, self.dps_mode)
            ratios = calculate_ratios(baseline_lua, modified_lua, self.calibration_factor)

            evaluations[name] = RelativeEvaluation(
                baseline_dps=baseline_accurate.dps,
                baseline_life=baseline_accurate.life,
                baseline_ehp=baseline_accurate.ehp,
                estimated_dps=baseline_accurate.dps * ratios.dps,
                estimated_life=baseline_accurate.life * ratios.life,
                estimated_ehp=baseline_accurate.ehp * ratios.ehp,
                dps_ratio=ratios.dps,
                life_ratio=ratios.life,
                ehp_ratio=ratios.ehp,
                dps_change_percent=(ratios.dps - 1) * 100,
                life_change_percent=(ratios.life - 1) * 100,
                ehp_change_percent=(ratios.ehp - 1) * 100,
                baseline_lua_dps=baseline_lua.dps,
                modified_lua_dps=modified_lua.dps,
            )

        return evaluations

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False

    def __del__(self):
        if self._started:
            self.shutdown()

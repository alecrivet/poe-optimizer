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
    ):
        """
        Initialize the batch calculator.

        Args:
            num_workers: Number of worker processes (defaults to CPU count)
            calibration_factor: Adjustment factor for ratio extrapolation
        """
        self.pool = PoBWorkerPool(num_workers=num_workers)
        self.calibration_factor = calibration_factor
        self._started = False
        logger.info(f"Initialized BatchCalculator (workers: {self.pool.num_workers})")

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
        baseline_accurate = get_build_summary(original_xml)
        baseline_dps = baseline_accurate.get('combinedDPS', 0)
        baseline_life = baseline_accurate.get('life', 0)
        baseline_ehp = baseline_accurate.get('totalEHP', 0)

        # Try to get stats from modified XML first
        modified_accurate = get_build_summary(modified_xml)
        if modified_accurate.get('combinedDPS', 0) > 0 and not use_lua_fallback:
            # Modified XML has accurate stats, use them directly
            return RelativeEvaluation(
                baseline_dps=baseline_dps,
                baseline_life=baseline_life,
                baseline_ehp=baseline_ehp,
                estimated_dps=modified_accurate.get('combinedDPS', 0),
                estimated_life=modified_accurate.get('life', 0),
                estimated_ehp=modified_accurate.get('totalEHP', 0),
                dps_ratio=modified_accurate.get('combinedDPS', 0) / baseline_dps if baseline_dps else 1.0,
                life_ratio=modified_accurate.get('life', 0) / baseline_life if baseline_life else 1.0,
                ehp_ratio=modified_accurate.get('totalEHP', 0) / baseline_ehp if baseline_ehp else 1.0,
                dps_change_percent=(modified_accurate.get('combinedDPS', 0) / baseline_dps - 1) * 100 if baseline_dps else 0,
                life_change_percent=(modified_accurate.get('life', 0) / baseline_life - 1) * 100 if baseline_life else 0,
                ehp_change_percent=(modified_accurate.get('totalEHP', 0) / baseline_ehp - 1) * 100 if baseline_ehp else 0,
                baseline_lua_dps=baseline_dps,
                modified_lua_dps=modified_accurate.get('combinedDPS', 0),
            )

        # Evaluate both builds using worker pool
        baseline_result = self.pool.evaluate(original_xml)
        modified_result = self.pool.evaluate(modified_xml)

        if not baseline_result.success:
            raise RuntimeError(f"Failed to evaluate baseline: {baseline_result.error}")
        if not modified_result.success:
            raise RuntimeError(f"Failed to evaluate modified: {modified_result.error}")

        baseline_lua = baseline_result.stats
        modified_lua = modified_result.stats

        baseline_lua_dps = baseline_lua.get('combinedDPS', 0)
        baseline_lua_life = baseline_lua.get('life', 0)
        baseline_lua_ehp = baseline_lua.get('totalEHP', 0)

        modified_lua_dps = modified_lua.get('combinedDPS', 0)
        modified_lua_life = modified_lua.get('life', 0)
        modified_lua_ehp = modified_lua.get('totalEHP', 0)

        # Calculate ratios
        dps_ratio = (modified_lua_dps / baseline_lua_dps * self.calibration_factor
                     if baseline_lua_dps > 0 else 1.0)
        life_ratio = (modified_lua_life / baseline_lua_life
                      if baseline_lua_life > 0 else 1.0)
        ehp_ratio = (modified_lua_ehp / baseline_lua_ehp
                     if baseline_lua_ehp > 0 else 1.0)

        # Extrapolate estimated real stats
        estimated_dps = baseline_dps * dps_ratio
        estimated_life = baseline_life * life_ratio
        estimated_ehp = baseline_ehp * ehp_ratio

        # Calculate percent changes
        dps_change = (dps_ratio - 1) * 100
        life_change = (life_ratio - 1) * 100
        ehp_change = (ehp_ratio - 1) * 100

        return RelativeEvaluation(
            baseline_dps=baseline_dps,
            baseline_life=baseline_life,
            baseline_ehp=baseline_ehp,
            estimated_dps=estimated_dps,
            estimated_life=estimated_life,
            estimated_ehp=estimated_ehp,
            dps_ratio=dps_ratio,
            life_ratio=life_ratio,
            ehp_ratio=ehp_ratio,
            dps_change_percent=dps_change,
            life_change_percent=life_change,
            ehp_change_percent=ehp_change,
            baseline_lua_dps=baseline_lua_dps,
            modified_lua_dps=modified_lua_dps,
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
        baseline_accurate = get_build_summary(original_xml)
        baseline_dps = baseline_accurate.get('combinedDPS', 0)
        baseline_life = baseline_accurate.get('life', 0)
        baseline_ehp = baseline_accurate.get('totalEHP', 0)

        # First, evaluate baseline
        baseline_result = self.pool.evaluate(original_xml)
        if not baseline_result.success:
            raise RuntimeError(f"Failed to evaluate baseline: {baseline_result.error}")

        baseline_lua = baseline_result.stats
        baseline_lua_dps = baseline_lua.get('combinedDPS', 0)
        baseline_lua_life = baseline_lua.get('life', 0)
        baseline_lua_ehp = baseline_lua.get('totalEHP', 0)

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

            modified_lua = result.stats
            modified_lua_dps = modified_lua.get('combinedDPS', 0)
            modified_lua_life = modified_lua.get('life', 0)
            modified_lua_ehp = modified_lua.get('totalEHP', 0)

            # Calculate ratios
            dps_ratio = (modified_lua_dps / baseline_lua_dps * self.calibration_factor
                         if baseline_lua_dps > 0 else 1.0)
            life_ratio = (modified_lua_life / baseline_lua_life
                          if baseline_lua_life > 0 else 1.0)
            ehp_ratio = (modified_lua_ehp / baseline_lua_ehp
                         if baseline_lua_ehp > 0 else 1.0)

            evaluations[name] = RelativeEvaluation(
                baseline_dps=baseline_dps,
                baseline_life=baseline_life,
                baseline_ehp=baseline_ehp,
                estimated_dps=baseline_dps * dps_ratio,
                estimated_life=baseline_life * life_ratio,
                estimated_ehp=baseline_ehp * ehp_ratio,
                dps_ratio=dps_ratio,
                life_ratio=life_ratio,
                ehp_ratio=ehp_ratio,
                dps_change_percent=(dps_ratio - 1) * 100,
                life_change_percent=(life_ratio - 1) * 100,
                ehp_change_percent=(ehp_ratio - 1) * 100,
                baseline_lua_dps=baseline_lua_dps,
                modified_lua_dps=modified_lua_dps,
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

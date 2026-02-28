"""
Greedy Gem Optimizer - Support Gem Optimization

Optimizes support gem selections for the main skill by evaluating all
candidate support gems via PoB's calculator. Uses a greedy approach:
iterate over each support slot, try all candidates, keep the best.

Algorithm:
1. Get baseline DPS from current build XML
2. Identify main skill group(s) (auto-detect + Righteous Fire)
3. For each support slot in each target group:
   a. For each candidate support gem (~214):
      - Generate modified XML via replace_support_gem()
      - Evaluate via batch calculator
   b. Pick the best support for this slot
   c. If best > current, keep the swap
4. Repeat until no slot improves (convergence)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

from ..pob.gem_database import GemDatabase, GemClassification, GemInfo
from ..pob.modifier import get_main_skill_info, replace_support_gem
from ..pob.batch_calculator import BatchCalculator
from ..pob.relative_calculator import RelativeCalculator, RelativeEvaluation

logger = logging.getLogger(__name__)


@dataclass
class GemSwap:
    """Record of a single gem swap."""
    socket_group_idx: int
    gem_idx: int
    old_name: str
    new_name: str
    dps_change_percent: float


@dataclass
class GemOptimizationResult:
    """Result from gem optimization."""
    original_xml: str
    optimized_xml: str
    original_dps: float
    optimized_dps: float
    swaps: List[GemSwap]
    iterations: int

    @property
    def dps_improvement_percent(self) -> float:
        if self.original_dps == 0:
            return 0.0
        return ((self.optimized_dps - self.original_dps) / self.original_dps) * 100


class GreedyGemOptimizer:
    """
    Greedy optimizer for support gem selection.

    Iterates over each support slot, evaluates all candidate support gems,
    and keeps the best for each slot. Repeats until convergence.

    Example:
        >>> gem_db = GemDatabase.from_pob_data()
        >>> optimizer = GreedyGemOptimizer(gem_db)
        >>> with BatchCalculator(num_workers=4) as calc:
        ...     result = optimizer.optimize(build_xml, calc)
        ...     for swap in result.swaps:
        ...         print(f"  {swap.old_name} → {swap.new_name} ({swap.dps_change_percent:+.1f}%)")
    """

    def __init__(
        self,
        gem_db: GemDatabase,
        max_iterations: int = 5,
        show_progress: bool = True,
        pin_damage_dealing: bool = True,
        pinned_gems: Optional[Set[str]] = None,
        dps_mode: str = "auto",
    ):
        """
        Initialize the gem optimizer.

        Args:
            gem_db: Parsed gem database from Gems.lua
            max_iterations: Maximum sweeps over all support slots
            show_progress: Show progress bars during optimization
            pin_damage_dealing: Auto-pin damage-dealing supports (e.g. Shockwave)
                                so they are never swapped out.
            pinned_gems: Explicit set of gem names to never swap out.
            dps_mode: DPS metric mode. "auto" uses "full" when damage-dealing
                      supports are present, "combined" otherwise. Can also be
                      set to "combined" or "full" explicitly.
        """
        self.gem_db = gem_db
        self.max_iterations = max_iterations
        self.show_progress = show_progress and TQDM_AVAILABLE
        self.pin_damage_dealing = pin_damage_dealing
        self.pinned_gems = pinned_gems or set()
        self.dps_mode = dps_mode
        self.all_supports = gem_db.get_all_supports()
        logger.info(
            f"Initialized GreedyGemOptimizer "
            f"({len(self.all_supports)} candidate supports, "
            f"max_iterations={max_iterations}, dps_mode={dps_mode})"
        )

    def optimize(
        self,
        build_xml: str,
        calculator: BatchCalculator,
        objective: str = "dps",
        main_skill_override: Optional[str] = None,
    ) -> GemOptimizationResult:
        """
        Optimize support gems for the main skill.

        Args:
            build_xml: PoB build XML string
            calculator: BatchCalculator instance (must be started)
            objective: Optimization objective ('dps', 'life', 'ehp', 'balanced')
            main_skill_override: Override main skill detection with gem name

        Returns:
            GemOptimizationResult with optimized XML and swap history
        """
        # Identify main skill groups
        groups = get_main_skill_info(build_xml, main_skill_override)
        if not groups:
            logger.warning("No main skill groups found, nothing to optimize")
            return GemOptimizationResult(
                original_xml=build_xml,
                optimized_xml=build_xml,
                original_dps=0,
                optimized_dps=0,
                swaps=[],
                iterations=0,
            )

        logger.info(f"Optimizing {len(groups)} socket group(s)")

        # Detect damage-dealing supports across all target groups
        damage_dealing_in_groups: Set[str] = set()
        for group in groups:
            for gem in group['gems']:
                if self.gem_db.is_damage_dealing(gem['name']):
                    damage_dealing_in_groups.add(gem['name'])

        # Resolve effective DPS mode
        effective_dps_mode = self.dps_mode
        if self.dps_mode == "auto":
            effective_dps_mode = "full" if damage_dealing_in_groups else "combined"
        logger.info(f"DPS mode: {self.dps_mode} -> effective: {effective_dps_mode}")

        # Update calculator's dps_mode to match
        calculator.dps_mode = effective_dps_mode

        # Build set of pinned gems (auto + explicit)
        pinned: Set[str] = set(self.pinned_gems)
        if self.pin_damage_dealing:
            pinned |= damage_dealing_in_groups

        for group in groups:
            gem_names = [g['name'] for g in group['gems']]
            logger.info(f"  Group {group['index']}: {gem_names}")
            logger.info(f"  Support slots: {group['support_indices']}")
        if pinned:
            logger.info(f"  Pinned gems (will not be swapped): {pinned}")

        # Get baseline evaluation
        baseline_eval = calculator.evaluate_modification(build_xml, build_xml)
        baseline_dps = self._get_objective_value(baseline_eval, objective)
        logger.info(f"Baseline {objective}: {baseline_dps:.2f}%")

        current_xml = build_xml
        all_swaps: List[GemSwap] = []

        for iteration in range(self.max_iterations):
            improved = False
            logger.info(f"--- Iteration {iteration + 1}/{self.max_iterations} ---")

            for group in groups:
                for support_gem_idx in group['support_indices']:
                    current_gem = group['gems'][support_gem_idx]
                    current_name = current_gem['name']

                    # Skip pinned gems
                    if current_name in pinned:
                        logger.info(
                            f"  Skipping slot {support_gem_idx} ({current_name}): pinned"
                        )
                        continue

                    # Build set of gems already in this group (to prevent duplicates)
                    current_group_info = get_main_skill_info(current_xml, main_skill_override)
                    used_names = set()
                    for g in current_group_info:
                        if g['index'] == group['index']:
                            for gem in g['gems']:
                                used_names.add(gem['name'])
                            break

                    # Generate candidates: all supports not already in the group
                    candidates: Dict[str, str] = {}
                    candidate_gems: Dict[str, GemInfo] = {}
                    for support in self.all_supports:
                        if support.name in used_names and support.name != current_name:
                            continue
                        if support.name == current_name:
                            continue  # Skip the current gem

                        modified_xml = replace_support_gem(
                            current_xml,
                            socket_group_idx=group['index'],
                            gem_idx=support_gem_idx,
                            new_gem_name=support.name,
                            new_game_id=support.game_id,
                            new_variant_id=support.variant_id,
                            new_skill_id=support.granted_effect_id,
                            level=support.max_level,
                            quality=20,
                        )
                        candidates[support.name] = modified_xml
                        candidate_gems[support.name] = support

                    if not candidates:
                        continue

                    logger.info(
                        f"Evaluating {len(candidates)} candidates for "
                        f"slot {support_gem_idx} (currently: {current_name})"
                    )

                    # Batch evaluate all candidates
                    if self.show_progress:
                        pbar = tqdm(
                            total=len(candidates),
                            desc=f"  Slot {support_gem_idx} ({current_name})",
                            unit="gem",
                            leave=False,
                        )

                    batch_results = calculator.evaluate_batch(
                        build_xml,  # Always compare against original build
                        candidates,
                    )

                    if self.show_progress:
                        pbar.update(len(candidates))
                        pbar.close()

                    # Find best candidate
                    best_name = None
                    best_score = self._get_objective_value(
                        calculator.evaluate_modification(build_xml, current_xml),
                        objective,
                    )

                    for name, eval_result in batch_results.items():
                        score = self._get_objective_value(eval_result, objective)
                        if score > best_score:
                            best_score = score
                            best_name = name

                    if best_name and best_name != current_name:
                        # Apply the swap
                        best_gem = candidate_gems[best_name]
                        current_xml = replace_support_gem(
                            current_xml,
                            socket_group_idx=group['index'],
                            gem_idx=support_gem_idx,
                            new_gem_name=best_gem.name,
                            new_game_id=best_gem.game_id,
                            new_variant_id=best_gem.variant_id,
                            new_skill_id=best_gem.granted_effect_id,
                            level=best_gem.max_level,
                            quality=20,
                        )

                        swap = GemSwap(
                            socket_group_idx=group['index'],
                            gem_idx=support_gem_idx,
                            old_name=current_name,
                            new_name=best_name,
                            dps_change_percent=best_score,
                        )
                        all_swaps.append(swap)
                        improved = True

                        # Update group gem info for subsequent slots
                        group['gems'][support_gem_idx]['name'] = best_name

                        logger.info(
                            f"  Swap: {current_name} → {best_name} "
                            f"({best_score:+.2f}% {objective})"
                        )
                    else:
                        logger.info(f"  Keeping: {current_name} (no improvement)")

            if not improved:
                logger.info("No improvements found, stopping")
                break

        # Final evaluation
        final_eval = calculator.evaluate_modification(build_xml, current_xml)
        final_score = self._get_objective_value(final_eval, objective)

        logger.info(
            f"Gem optimization complete: {len(all_swaps)} swaps, "
            f"{final_score:+.2f}% {objective} total"
        )

        return GemOptimizationResult(
            original_xml=build_xml,
            optimized_xml=current_xml,
            original_dps=baseline_dps,
            optimized_dps=final_score,
            swaps=all_swaps,
            iterations=iteration + 1 if groups else 0,
        )

    def _get_objective_value(
        self,
        eval_result: RelativeEvaluation,
        objective: str,
    ) -> float:
        """Get the objective value from an evaluation result."""
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

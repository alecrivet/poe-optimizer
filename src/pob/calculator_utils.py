"""
Shared utility functions for build calculators.

Extracts common logic used by both RelativeCalculator and BatchCalculator
to avoid code duplication. These functions handle:
- Stat extraction from build summary dicts
- Ratio calculations with zero-division safety
- Percent change calculations
- Construction of RelativeEvaluation from raw stats
"""

from typing import Dict, NamedTuple


class BuildStats(NamedTuple):
    """Extracted DPS, life, and EHP from a build summary dict."""
    dps: float
    life: float
    ehp: float


def extract_build_stats(stats: Dict, dps_mode: str = "combined") -> BuildStats:
    """
    Extract the three core stats (DPS, life, totalEHP) from a build
    summary dictionary.

    Args:
        stats: Dictionary from get_build_summary() or Lua evaluation results.
        dps_mode: Which DPS metric to use. "combined" uses combinedDPS
                  (main skill only), "full" uses fullDPS (sum of all skills).

    Returns:
        BuildStats named tuple with dps, life, ehp fields.
    """
    dps_key = "fullDPS" if dps_mode == "full" else "combinedDPS"
    return BuildStats(
        dps=stats.get(dps_key, 0),
        life=stats.get('life', 0),
        ehp=stats.get('totalEHP', 0),
    )


def calculate_percent_change(old_value: float, new_value: float) -> float:
    """
    Calculate the percent change from old_value to new_value.

    Returns 0 if old_value is zero (avoids division by zero).

    Args:
        old_value: The baseline value.
        new_value: The new/modified value.

    Returns:
        Percent change as a float (e.g. 7.5 means +7.5%).
    """
    if old_value == 0:
        return 0.0
    return (new_value / old_value - 1) * 100


def calculate_ratios(
    baseline: BuildStats,
    modified: BuildStats,
    calibration_factor: float = 1.0,
) -> BuildStats:
    """
    Calculate the ratio of modified stats to baseline stats.

    DPS ratio is adjusted by calibration_factor; life and EHP ratios are not.
    Returns 1.0 for any stat where the baseline is zero.

    Args:
        baseline: Baseline build stats.
        modified: Modified build stats.
        calibration_factor: Adjustment factor applied to the DPS ratio only.

    Returns:
        BuildStats where each field is the ratio (modified / baseline).
    """
    dps_ratio = (modified.dps / baseline.dps * calibration_factor
                 if baseline.dps > 0 else 1.0)
    life_ratio = (modified.life / baseline.life
                  if baseline.life > 0 else 1.0)
    ehp_ratio = (modified.ehp / baseline.ehp
                 if baseline.ehp > 0 else 1.0)
    return BuildStats(dps=dps_ratio, life=life_ratio, ehp=ehp_ratio)


def build_evaluation_from_accurate_stats(
    baseline: BuildStats,
    modified: BuildStats,
):
    """
    Build a RelativeEvaluation when both baseline and modified have accurate
    pre-calculated stats (no Lua / no extrapolation needed).

    This is the common early-return path used when use_lua_fallback=False and
    the modified XML already contains pre-calculated stats.

    Args:
        baseline: Accurate baseline stats from XML.
        modified: Accurate modified stats from XML.

    Returns:
        A RelativeEvaluation instance.
    """
    from .relative_calculator import RelativeEvaluation

    ratios = BuildStats(
        dps=modified.dps / baseline.dps if baseline.dps else 1.0,
        life=modified.life / baseline.life if baseline.life else 1.0,
        ehp=modified.ehp / baseline.ehp if baseline.ehp else 1.0,
    )
    return RelativeEvaluation(
        baseline_dps=baseline.dps,
        baseline_life=baseline.life,
        baseline_ehp=baseline.ehp,
        estimated_dps=modified.dps,
        estimated_life=modified.life,
        estimated_ehp=modified.ehp,
        dps_ratio=ratios.dps,
        life_ratio=ratios.life,
        ehp_ratio=ratios.ehp,
        dps_change_percent=(ratios.dps - 1) * 100,
        life_change_percent=(ratios.life - 1) * 100,
        ehp_change_percent=(ratios.ehp - 1) * 100,
        baseline_lua_dps=baseline.dps,
        modified_lua_dps=modified.dps,
    )


def build_evaluation_from_lua(
    baseline_accurate: BuildStats,
    baseline_lua: BuildStats,
    modified_lua: BuildStats,
    calibration_factor: float = 1.0,
):
    """
    Build a RelativeEvaluation using Lua-computed stats and ratio extrapolation.

    This is the common main path: use Lua stats to compute ratios, then
    extrapolate from accurate baseline stats.

    Args:
        baseline_accurate: Accurate baseline stats (from XML parsing).
        baseline_lua: Baseline stats from Lua evaluation.
        modified_lua: Modified stats from Lua evaluation.
        calibration_factor: Adjustment factor for DPS ratio.

    Returns:
        A RelativeEvaluation instance.
    """
    from .relative_calculator import RelativeEvaluation

    ratios = calculate_ratios(baseline_lua, modified_lua, calibration_factor)

    estimated_dps = baseline_accurate.dps * ratios.dps
    estimated_life = baseline_accurate.life * ratios.life
    estimated_ehp = baseline_accurate.ehp * ratios.ehp

    return RelativeEvaluation(
        baseline_dps=baseline_accurate.dps,
        baseline_life=baseline_accurate.life,
        baseline_ehp=baseline_accurate.ehp,
        estimated_dps=estimated_dps,
        estimated_life=estimated_life,
        estimated_ehp=estimated_ehp,
        dps_ratio=ratios.dps,
        life_ratio=ratios.life,
        ehp_ratio=ratios.ehp,
        dps_change_percent=(ratios.dps - 1) * 100,
        life_change_percent=(ratios.life - 1) * 100,
        ehp_change_percent=(ratios.ehp - 1) * 100,
        baseline_lua_dps=baseline_lua.dps,
        modified_lua_dps=modified_lua.dps,
    )

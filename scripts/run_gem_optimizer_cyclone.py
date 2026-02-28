"""
Run the greedy gem optimizer against a Cyclone of Tumult + Shockwave build.

Key challenge: Shockwave is a support gem that deals its own damage.
Optimizing purely for "Cyclone DPS" might miss the Shockwave contribution.

This script uses dps_mode="full" (via auto-detection) so that FullDPS
is measured, and Shockwave is auto-pinned so it's never swapped out.
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pob.codec import decode_pob_code
from src.pob.gem_database import GemDatabase, GemClassification
from src.pob.modifier import get_main_skill_info, get_skill_groups_summary, replace_support_gem
from src.pob.xml_parser import get_build_summary
from src.pob.relative_calculator import RelativeCalculator
from src.pob.calculator_utils import enable_full_dps

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    print("=" * 70)
    print("Gem Optimizer: Cyclone of Tumult + Shockwave Build")
    print("=" * 70)
    print()

    # Load build from file
    build_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "shockwavecyclonegencry.txt"
    )
    with open(build_path, "r") as f:
        code = f.read().strip()

    print("Decoding build...")
    build_xml = decode_pob_code(code)

    # Get XML summary
    summary = get_build_summary(build_xml)
    print(f"  Class: {summary.get('className', '?')} / {summary.get('ascendClassName', '?')}")
    print(f"  Level: {summary.get('level', '?')}")
    print(f"  Combined DPS: {summary.get('combinedDPS', 0):,.0f}")
    print(f"  Full DPS:     {summary.get('fullDPS', 0):,.0f}")
    print(f"  Total EHP: {summary.get('totalEHP', 0):,.0f}")
    print(f"  Life: {summary.get('life', 0):,.0f}")

    # Show ALL skill groups
    print(f"\n{'='*70}")
    print("All Skill Groups:")
    print(f"{'='*70}")
    all_groups = get_skill_groups_summary(build_xml)
    for g in all_groups:
        enabled = "ON" if g.get('enabled', True) else "OFF"
        slot = g.get('slot', 'unslotted')
        print(f"\n  Group {g['index']} [{enabled}] slot={slot}:")
        for gem in g.get('gems', []):
            is_support = "Support" in gem.get('gemId', '') or "Support" in gem.get('variantId', '')
            role = "SUPPORT" if is_support else "ACTIVE"
            en = "" if gem.get('enabled', True) else " [DISABLED]"
            print(f"    [{role:7s}] {gem['name']:35s} L{gem.get('level', '?'):>2} Q{gem.get('quality', '?'):>2}{en}")

    # Identify main skill groups
    print(f"\n{'='*70}")
    print("Main Skill Detection:")
    print(f"{'='*70}")
    groups = get_main_skill_info(build_xml)

    gem_db = GemDatabase.from_pob_data()

    for group in groups:
        print(f"\n  Target Group {group['index']}:")
        for gem in group['gems']:
            role = "SUPPORT" if gem['gem_idx'] in group['support_indices'] else "ACTIVE"
            # Show classification for supports
            classification = ""
            if role == "SUPPORT":
                gem_info = gem_db.get_support_by_name(gem['name'])
                if gem_info:
                    classification = f" [{gem_info.classification.value}]"
            print(f"    [{role:7s}] {gem['name']:35s} (idx={gem['gem_idx']}){classification}")
        print(f"  Support slots to optimize: {group['support_indices']}")

    # Detect damage-dealing supports
    print(f"\n{'='*70}")
    print("Damage-Dealing Support Detection:")
    print(f"{'='*70}")
    damage_dealing = []
    for group in groups:
        for gem in group['gems']:
            if gem_db.is_damage_dealing(gem['name']):
                damage_dealing.append(gem['name'])
    if damage_dealing:
        print(f"  Found damage-dealing supports: {damage_dealing}")
        print(f"  -> Using dps_mode='full' (FullDPS) for accurate measurement")
        print(f"  -> These gems will be PINNED (not swapped out)")
    else:
        print(f"  No damage-dealing supports found, using dps_mode='combined'")

    # Enable includeInFullDPS on the main skill group so PoB computes FullDPS
    if damage_dealing:
        group_indices = [g['index'] for g in groups]  # 1-based from get_main_skill_info
        build_xml = enable_full_dps(build_xml, group_indices)
        print(f"  Enabled includeInFullDPS on XML groups: {group_indices}")

    # Run gem swap evaluation with fullDPS mode
    print(f"\n{'='*70}")
    print("Running Gem Swap Evaluation (dps_mode=full)")
    print(f"{'='*70}")

    # Use fullDPS since Shockwave contributes its own damage
    rel_calc = RelativeCalculator(dps_mode="full")

    group = groups[0]
    used_names = {g['name'] for g in group['gems']}

    # Build pinned set
    pinned = {gem['name'] for gem in group['gems'] if gem_db.is_damage_dealing(gem['name'])}
    if pinned:
        print(f"\n  Pinned gems: {pinned}")

    # Test well-known melee/phys supports
    test_supports = [
        "Brutality", "Melee Physical Damage", "Pulverise",
        "Concentrated Effect", "Increased Critical Damage",
        "Increased Critical Strikes", "Awakened Melee Physical Damage",
        "Close Combat", "Fortify", "Ruthless",
        "Damage on Full Life", "Elemental Damage with Attacks",
        "Added Fire Damage", "Impale", "Maim",
    ]

    for support_idx in group['support_indices']:
        current = group['gems'][support_idx]

        # Skip pinned gems
        if current['name'] in pinned:
            print(f"\n  --- Slot {support_idx}: {current['name']} --- PINNED (skipping)")
            continue

        print(f"\n  --- Slot {support_idx}: {current['name']} ---")

        results = []
        for gem_name in test_supports:
            gem_info = gem_db.get_support_by_name(gem_name)
            if gem_info is None:
                continue
            if gem_name in used_names and gem_name != current['name']:
                continue
            if gem_name == current['name']:
                continue

            modified_xml = replace_support_gem(
                build_xml,
                socket_group_idx=group['index'],
                gem_idx=support_idx,
                new_gem_name=gem_info.name,
                new_game_id=gem_info.game_id,
                new_variant_id=gem_info.variant_id,
                new_skill_id=gem_info.granted_effect_id,
                level=gem_info.max_level,
                quality=20,
            )

            t0 = time.time()
            try:
                result = rel_calc.evaluate_modification(build_xml, modified_xml)
                elapsed = time.time() - t0
                results.append((gem_name, result.dps_change_percent, result.life_change_percent))
                sign = "+" if result.dps_change_percent >= 0 else ""
                print(f"    {gem_name:40s} {sign}{result.dps_change_percent:.2f}% FullDPS  ({elapsed:.1f}s)")
            except Exception as e:
                print(f"    {gem_name:40s} ERROR: {e}")

        if results:
            results.sort(key=lambda x: x[1], reverse=True)
            best = results[0]
            print(f"  Best for this slot: {current['name']} -> {best[0]} ({best[1]:+.2f}% FullDPS)")


if __name__ == "__main__":
    main()

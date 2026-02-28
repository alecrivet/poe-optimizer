"""
End-to-end test: Run the gem optimizer against build1 (Icicle Mine).

This does a real optimization loop using PoB's Lua evaluator.
Uses a small candidate set for speed (just 10 supports per slot).
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pob.codec import decode_pob_code
from src.pob.gem_database import GemDatabase
from src.pob.modifier import get_main_skill_info, replace_support_gem
from src.pob.caller import PoBCalculator
from src.pob.relative_calculator import RelativeCalculator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_build1_xml() -> str:
    build_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "build1"
    )
    with open(build_path, "r") as f:
        code = f.read().strip()
    return decode_pob_code(code)


def main():
    print("=" * 70)
    print("Gem Optimizer End-to-End Test")
    print("=" * 70)
    print()

    # Load build
    print("Loading build1 (Icicle Mine of Fanning)...")
    build_xml = load_build1_xml()

    # Load gem database
    print("Loading gem database...")
    gem_db = GemDatabase.from_pob_data()
    all_supports = gem_db.get_all_supports()
    print(f"  {len(gem_db)} total gems, {len(all_supports)} supports")

    # Identify main skill
    groups = get_main_skill_info(build_xml)
    print(f"\nMain skill group(s): {len(groups)}")
    for group in groups:
        print(f"  Group {group['index']}:")
        for gem in group['gems']:
            role = "SUPPORT" if gem['gem_idx'] in group['support_indices'] else "ACTIVE"
            print(f"    [{role}] {gem['name']} (L{gem['level']} Q{gem['quality']})")

    # Initialize calculator
    print("\nInitializing calculator...")
    rel_calc = RelativeCalculator()

    # Get baseline
    print("Evaluating baseline...")
    baseline = rel_calc.evaluate_modification(build_xml, build_xml)
    print(f"  Baseline DPS: {baseline.baseline_dps:,.0f}")
    print(f"  Baseline Life: {baseline.baseline_life:,.0f}")

    # Test: Try a handful of support gem swaps on the first support slot
    group = groups[0]
    target_slot = group['support_indices'][0]
    current_gem = group['gems'][target_slot]
    print(f"\nTesting gem swaps for slot {target_slot}: {current_gem['name']}")

    # Pick 10 well-known supports to test
    test_gems = [
        "Brutality", "Concentrated Effect", "Increased Critical Damage",
        "Added Fire Damage", "Elemental Focus", "Hypothermia",
        "Cold Penetration", "Faster Casting", "Spell Echo", "Empower",
    ]

    used_names = {g['name'] for g in group['gems']}
    results = []

    for gem_name in test_gems:
        gem_info = gem_db.get_support_by_name(gem_name)
        if gem_info is None:
            print(f"  {gem_name}: not found in database, skipping")
            continue
        if gem_name in used_names:
            print(f"  {gem_name}: already in group, skipping")
            continue

        # Generate modified XML
        modified_xml = replace_support_gem(
            build_xml,
            socket_group_idx=group['index'],
            gem_idx=target_slot,
            new_gem_name=gem_info.name,
            new_game_id=gem_info.game_id,
            new_variant_id=gem_info.variant_id,
            new_skill_id=gem_info.granted_effect_id,
            level=gem_info.max_level,
            quality=20,
        )

        # Evaluate
        t0 = time.time()
        try:
            result = rel_calc.evaluate_modification(build_xml, modified_xml)
            elapsed = time.time() - t0
            results.append((gem_name, result.dps_change_percent))
            print(f"  {gem_name}: {result.dps_change_percent:+.2f}% DPS  ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  {gem_name}: ERROR - {e}  ({elapsed:.1f}s)")

    # Summary
    print("\n" + "=" * 70)
    print(f"RESULTS: Replacing '{current_gem['name']}' in slot {target_slot}")
    print("=" * 70)
    results.sort(key=lambda x: x[1], reverse=True)
    for name, pct in results:
        marker = "BETTER" if pct > 0 else ("WORSE" if pct < 0 else "SAME")
        print(f"  {name:30s}  {pct:+8.2f}%  [{marker}]")

    any_improvement = any(pct > 0.01 for _, pct in results)
    any_difference = any(abs(pct) > 0.01 for _, pct in results)

    print()
    if any_difference:
        print("VERDICT: Gem swaps produce different DPS values.")
        if any_improvement:
            best_name, best_pct = results[0]
            print(f"  Best swap: {current_gem['name']} -> {best_name} ({best_pct:+.2f}%)")
        print("  The gem optimizer pipeline is WORKING.")
    else:
        print("VERDICT: No DPS differences detected. Something is wrong.")


if __name__ == "__main__":
    main()

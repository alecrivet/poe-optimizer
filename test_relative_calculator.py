#!/usr/bin/env python3
"""
Test the RelativeCalculator approach with real build modifications.

This validates that ratio extrapolation works for estimating build changes.
"""

from src.pob.codec import decode_pob_code, encode_pob_code
from src.pob.modifier import modify_passive_tree_nodes, modify_character_level, get_passive_tree_summary
from src.pob.relative_calculator import RelativeCalculator
from src.pob.xml_parser import get_build_summary

def main():
    print("=" * 70)
    print("Testing Relative Calculator Approach")
    print("=" * 70)

    # Load build1 (build2 has Timeless Jewels which don't work with HeadlessWrapper)
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    original_xml = decode_pob_code(code)

    # Get baseline stats
    print("\n1. Baseline (from XML pre-calculated stats):")
    baseline = get_build_summary(original_xml)
    print(f"   Combined DPS: {baseline['combinedDPS']:,.0f}")
    print(f"   Life: {baseline['life']:,.0f}")
    print(f"   Total EHP: {baseline['totalEHP']:,.0f}")

    # Get passive tree info
    tree_summary = get_passive_tree_summary(original_xml)
    print(f"\n2. Current passive tree:")
    print(f"   Total nodes: {tree_summary['total_nodes']}")
    print(f"   Class: {tree_summary['class_name']}")
    print(f"   Ascendancy: {tree_summary['ascendancy_name']}")

    # Make some test modifications
    print("\n3. Creating test modifications...")

    # Get some nodes to work with
    allocated_nodes = list(tree_summary['allocated_nodes'])

    # Modification 1: Remove 5 nodes (should decrease stats)
    nodes_to_remove = allocated_nodes[:5]
    mod1_xml = modify_passive_tree_nodes(
        original_xml,
        nodes_to_remove=nodes_to_remove
    )
    print(f"   Mod 1: Remove 5 nodes")

    # Modification 2: Remove 10 nodes (should decrease more)
    nodes_to_remove_2 = allocated_nodes[:10]
    mod2_xml = modify_passive_tree_nodes(
        original_xml,
        nodes_to_remove=nodes_to_remove_2
    )
    print(f"   Mod 2: Remove 10 nodes")

    # Modification 3: Change level from 94 to 90 (should decrease)
    mod3_xml = modify_character_level(original_xml, 90)
    print(f"   Mod 3: Change level 94 → 90")

    # Modification 4: Change level from 94 to 95 (should increase slightly)
    mod4_xml = modify_character_level(original_xml, 95)
    print(f"   Mod 4: Change level 94 → 95")

    # Test the relative calculator
    print("\n4. Testing RelativeCalculator...")
    calc = RelativeCalculator()

    modifications = {
        "Remove 5 nodes": mod1_xml,
        "Remove 10 nodes": mod2_xml,
        "Level 90": mod3_xml,
        "Level 95": mod4_xml,
    }

    results = calc.compare_modifications(original_xml, modifications)

    print("\n5. Results:")
    print("-" * 70)
    for name, result in results.items():
        print(f"\n{name}:")
        print(f"  DPS: {result.baseline_dps:,.0f} → {result.estimated_dps:,.0f} ({result.dps_change_percent:+.1f}%)")
        print(f"  Life: {result.baseline_life:,.0f} → {result.estimated_life:,.0f} ({result.life_change_percent:+.1f}%)")
        print(f"  EHP: {result.baseline_ehp:,.0f} → {result.estimated_ehp:,.0f} ({result.ehp_change_percent:+.1f}%)")
        print(f"  Ratio: {result.dps_ratio:.4f} (Lua: {result.baseline_lua_dps:.0f} → {result.modified_lua_dps:.0f})")

    # Validate expectations
    print("\n6. Validation:")
    print("-" * 70)

    # Removing more nodes should decrease stats more
    r1 = results["Remove 5 nodes"]
    r2 = results["Remove 10 nodes"]

    if r2.estimated_dps < r1.estimated_dps < baseline['combinedDPS']:
        print("   ✓ Removing more nodes decreases DPS (as expected)")
    else:
        print("   ✗ Node removal doesn't behave as expected")

    # Lower level should decrease stats
    r3 = results["Level 90"]
    if r3.estimated_life < baseline['life']:
        print("   ✓ Lower level decreases life (as expected)")
    else:
        print("   ✗ Level change doesn't behave as expected")

    # Rank by DPS
    print("\n7. Ranking modifications by DPS:")
    ranked = calc.rank_by_objective(results, 'dps')
    for i, (name, result) in enumerate(ranked, 1):
        print(f"   {i}. {name}: {result.estimated_dps:,.0f} DPS ({result.dps_change_percent:+.1f}%)")

    # Rank by Life
    print("\n8. Ranking modifications by Life:")
    ranked = calc.rank_by_objective(results, 'life')
    for i, (name, result) in enumerate(ranked, 1):
        print(f"   {i}. {name}: {result.estimated_life:,.0f} Life ({result.life_change_percent:+.1f}%)")

    print("\n" + "=" * 70)
    print("Conclusion:")
    print("=" * 70)
    print("If ratios are reasonable (changes in expected direction),")
    print("then relative calculation approach is viable for optimization!")
    print("=" * 70)

if __name__ == "__main__":
    main()

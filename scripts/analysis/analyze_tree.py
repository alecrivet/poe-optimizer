#!/usr/bin/env python3
"""
Analyze which passive tree nodes can be removed without hurting the objective.

This helps identify inefficient nodes for reallocation.
"""

import logging

from src.pob.codec import decode_pob_code
from src.pob.modifier import modify_passive_tree_nodes, get_passive_tree_summary
from src.pob.relative_calculator import RelativeCalculator

# Enable logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings/errors
    format='%(levelname)s: %(message)s'
)


def main():
    print("=" * 70)
    print("Passive Tree Node Analysis")
    print("=" * 70)

    # Load build1
    print("\n1. Loading build...")
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    original_xml = decode_pob_code(code)
    tree = get_passive_tree_summary(original_xml)
    print(f"   ✓ Build loaded: {tree['total_nodes']} nodes allocated")

    # Create calculator
    print("\n2. Analyzing nodes (this will take a few minutes)...")
    calculator = RelativeCalculator()

    allocated_nodes = list(tree['allocated_nodes'])[:30]  # Analyze first 30 for speed

    results = []

    for i, node_id in enumerate(allocated_nodes, 1):
        print(f"   Analyzing node {i}/{len(allocated_nodes)}: {node_id}...", end='\r')

        try:
            # Try removing this node
            modified_xml = modify_passive_tree_nodes(
                original_xml,
                nodes_to_remove=[node_id]
            )

            # Evaluate impact
            eval_result = calculator.evaluate_modification(original_xml, modified_xml)

            results.append({
                'node_id': node_id,
                'dps_change': eval_result.dps_change_percent,
                'life_change': eval_result.life_change_percent,
                'ehp_change': eval_result.ehp_change_percent,
            })

        except Exception as e:
            print(f"   Error analyzing node {node_id}: {e}")

    print()  # Clear the progress line

    # Sort by DPS impact (least impact first)
    results.sort(key=lambda x: abs(x['dps_change']))

    # Display results
    print("\n" + "=" * 70)
    print("NODE ANALYSIS RESULTS")
    print("=" * 70)

    print("\n🎯 Nodes with MINIMAL DPS impact (candidates for reallocation):")
    print("-" * 70)
    for result in results[:10]:
        if abs(result['dps_change']) < 1.0:  # Less than 1% DPS impact
            print(f"  Node {result['node_id']}: "
                  f"DPS {result['dps_change']:+.2f}%, "
                  f"Life {result['life_change']:+.2f}%, "
                  f"EHP {result['ehp_change']:+.2f}%")

    print("\n⚠️  Nodes with MODERATE DPS impact:")
    print("-" * 70)
    for result in results[:10]:
        if 1.0 <= abs(result['dps_change']) < 5.0:
            print(f"  Node {result['node_id']}: "
                  f"DPS {result['dps_change']:+.2f}%, "
                  f"Life {result['life_change']:+.2f}%, "
                  f"EHP {result['ehp_change']:+.2f}%")

    print("\n🔴 Nodes with HIGH DPS impact (important nodes):")
    print("-" * 70)
    for result in sorted(results, key=lambda x: abs(x['dps_change']), reverse=True)[:10]:
        if abs(result['dps_change']) >= 5.0:
            print(f"  Node {result['node_id']}: "
                  f"DPS {result['dps_change']:+.2f}%, "
                  f"Life {result['life_change']:+.2f}%, "
                  f"EHP {result['ehp_change']:+.2f}%")

    print("\n" + "=" * 70)
    print("INSIGHTS")
    print("=" * 70)

    # Count nodes by impact
    minimal = len([r for r in results if abs(r['dps_change']) < 1.0])
    moderate = len([r for r in results if 1.0 <= abs(r['dps_change']) < 5.0])
    high = len([r for r in results if abs(r['dps_change']) >= 5.0])

    print(f"\nOut of {len(results)} nodes analyzed:")
    print(f"  {minimal} nodes have minimal DPS impact (<1%)")
    print(f"  {moderate} nodes have moderate DPS impact (1-5%)")
    print(f"  {high} nodes have high DPS impact (≥5%)")

    if minimal > 0:
        print(f"\n💡 You could reallocate the {minimal} minimal-impact nodes")
        print(f"   to potentially gain more DPS elsewhere!")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

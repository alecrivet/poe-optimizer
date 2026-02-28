#!/usr/bin/env python3
"""
Test the Greedy Tree Optimizer

This script tests the passive tree optimizer on build1.
"""

import logging

from src.pob.codec import decode_pob_code, encode_pob_code
from src.optimizer import GreedyTreeOptimizer

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def main():
    print("=" * 70)
    print("Testing Greedy Tree Optimizer")
    print("=" * 70)

    # Load build1
    print("\n1. Loading build...")
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    original_xml = decode_pob_code(code)
    print("   ✓ Build loaded")

    # Create optimizer
    print("\n2. Initializing optimizer...")
    optimizer = GreedyTreeOptimizer(
        max_iterations=10,  # Start small for testing
        min_improvement=0.5,  # 0.5% minimum improvement
        max_points_change=5,  # Can remove up to 5 points
    )
    print("   ✓ Optimizer initialized")

    # Run optimization
    print("\n3. Running optimization (this may take a few minutes)...")
    print("   Objective: Maximize DPS")
    print("   Max iterations: 10")
    print("   Min improvement: 0.5%")
    print()

    result = optimizer.optimize(
        original_xml,
        objective='dps',
        allow_point_increase=False  # Only reallocate existing points
    )

    # Display results
    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULTS")
    print("=" * 70)

    print(f"\nIterations: {result.iterations}")

    print(f"\nOriginal Stats:")
    print(f"  DPS:  {result.original_stats.baseline_dps:,.0f}")
    print(f"  Life: {result.original_stats.baseline_life:,.0f}")
    print(f"  EHP:  {result.original_stats.baseline_ehp:,.0f}")

    print(f"\nOptimized Stats:")
    print(f"  DPS:  {result.optimized_stats.estimated_dps:,.0f} ({result.optimized_stats.dps_change_percent:+.2f}%)")
    print(f"  Life: {result.optimized_stats.estimated_life:,.0f} ({result.optimized_stats.life_change_percent:+.2f}%)")
    print(f"  EHP:  {result.optimized_stats.estimated_ehp:,.0f} ({result.optimized_stats.ehp_change_percent:+.2f}%)")

    print(f"\nImprovements Applied:")
    for mod in result.modifications_applied:
        print(f"  {mod['iteration']}. {mod['modification']} (+{mod['improvement_pct']:.2f}% DPS)")

    print(f"\nTotal Improvement: {result.get_improvement('dps'):+.2f}% DPS")

    # Generate optimized PoB code
    print("\n" + "=" * 70)
    print("OPTIMIZED BUILD CODE")
    print("=" * 70)

    optimized_code = encode_pob_code(result.optimized_xml)
    print(f"\nOptimized PoB Code (paste into Path of Building):")
    print(optimized_code[:100] + "...")
    print(f"(Full code length: {len(optimized_code)} characters)")

    # Save to file
    output_file = "optimized_build1.txt"
    with open(output_file, 'w') as f:
        f.write(optimized_code)
    print(f"\n✓ Saved full code to: {output_file}")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("1. Copy the optimized PoB code")
    print("2. Paste it into Path of Building (Import/Export Build)")
    print("3. Verify the stats match expectations")
    print("4. Check which nodes were removed")
    print("=" * 70)


if __name__ == "__main__":
    main()

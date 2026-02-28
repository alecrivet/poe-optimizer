#!/usr/bin/env python3
"""
Example 1: Quick Build Optimization

Shows the simplest workflow:
1. Load a build from PoB code
2. Run greedy optimizer for fast results
3. Display improvements

Use case: Quick optimization for immediate improvements
"""

import sys
sys.path.insert(0, '../..')

from src.pob.codec import decode_pob_code, encode_pob_code
from src.optimizer.tree_optimizer import GreedyTreeOptimizer
from src.visualization.tree_diff import print_tree_diff_summary

def main():
    print("\n" + "="*80)
    print("EXAMPLE 1: Quick Build Optimization")
    print("="*80)

    # Step 1: Load build from file
    print("\n📖 Step 1: Loading build...")
    with open('../../examples/build1', 'r') as f:
        pob_code = f.read().strip()

    build_xml = decode_pob_code(pob_code)
    print("   ✅ Build loaded successfully")

    # Step 2: Create optimizer
    print("\n🔧 Step 2: Creating greedy optimizer...")
    optimizer = GreedyTreeOptimizer(
        max_iterations=50,
        min_improvement=0.1,
        optimize_masteries=True,
    )
    print("   ✅ Optimizer ready")

    # Step 3: Optimize for DPS
    print("\n🚀 Step 3: Optimizing for maximum DPS...")
    print("   (This will take ~2 minutes)")

    result = optimizer.optimize(
        build_xml,
        objective='dps',
        allow_point_increase=False  # Only reallocate existing points
    )

    # Step 4: Display results
    print("\n" + "="*80)
    print("OPTIMIZATION RESULTS")
    print("="*80)

    print(f"\n📊 Improvements:")
    print(f"   DPS:  {result.optimized_stats.dps_change_percent:+.2f}%")
    print(f"   Life: {result.optimized_stats.life_change_percent:+.2f}%")
    print(f"   EHP:  {result.optimized_stats.ehp_change_percent:+.2f}%")

    print(f"\n🔄 Optimization Details:")
    print(f"   Iterations: {result.iterations}")
    print(f"   Modifications: {len(result.modifications_applied)}")

    if result.modifications_applied:
        print(f"\n📝 Changes Made:")
        for mod in result.modifications_applied[:5]:  # Show first 5
            print(f"   {mod['iteration']}. {mod['modification']} "
                  f"({mod['improvement_pct']:+.2f}%)")
        if len(result.modifications_applied) > 5:
            print(f"   ... and {len(result.modifications_applied) - 5} more")

    # Step 5: Show tree differences
    print(f"\n🌳 Tree Changes:")
    print_tree_diff_summary(result.original_xml, result.optimized_xml)

    # Step 6: Save optimized build
    print(f"\n💾 Saving optimized build...")
    optimized_code = encode_pob_code(result.optimized_xml)

    with open('optimized_build_quick.txt', 'w') as f:
        f.write(optimized_code)

    print(f"   ✅ Saved to: optimized_build_quick.txt")
    print(f"   📋 Import this code into Path of Building!")

    print("\n" + "="*80)
    print("✅ OPTIMIZATION COMPLETE!")
    print("="*80)
    print("\n💡 Next steps:")
    print("   1. Copy the code from optimized_build_quick.txt")
    print("   2. Import into Path of Building")
    print("   3. Test the build!")
    print("\n")

if __name__ == "__main__":
    main()

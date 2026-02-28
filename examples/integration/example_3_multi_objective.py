#!/usr/bin/env python3
"""
Example 3: Multi-Objective Optimization

Shows how to explore trade-offs between objectives:
1. Load build
2. Run multi-objective optimization
3. Visualize Pareto frontier
4. Pick preferred trade-off

Use case: Finding balance between DPS, Life, and Defense
"""

import sys
sys.path.insert(0, '../..')

from src.pob.codec import decode_pob_code, encode_pob_code
from src.optimizer.genetic_optimizer import GeneticTreeOptimizer
from src.optimizer.multi_objective_optimizer import get_pareto_frontier, format_pareto_frontier
from src.visualization.frontier_plot import plot_pareto_frontier_3d, plot_all_projections

def main():
    print("\n" + "="*80)
    print("EXAMPLE 3: Multi-Objective Optimization")
    print("="*80)

    # Step 1: Load build
    print("\n📖 Step 1: Loading build...")
    with open('../../examples/build1', 'r') as f:
        pob_code = f.read().strip()

    build_xml = decode_pob_code(pob_code)
    print("   ✅ Build loaded")

    # Step 2: Create genetic optimizer
    print("\n🎯 Step 2: Creating multi-objective optimizer...")
    print("   This will find trade-offs between:")
    print("      - DPS (offense)")
    print("      - Life (survivability)")
    print("      - EHP (tankiness)")

    optimizer = GeneticTreeOptimizer(
        population_size=30,
        generations=50,
        mutation_rate=0.2,
        optimize_masteries=True,
    )
    print("   ✅ Optimizer ready")

    # Step 3: Run optimization for multiple objectives
    print("\n🚀 Step 3: Running multi-objective optimization...")
    print("   ⚠️  This will take 15-25 minutes")
    print("   💡 We'll run 3 optimizations (DPS, Life, EHP) to build frontier")
    print()

    # Note: Full multi-objective would integrate NSGA-II into genetic optimizer
    # For this example, we'll run 3 separate optimizations and combine results

    results = {}

    # Optimize for DPS
    print("   🔴 Optimizing for DPS...")
    results['dps'] = optimizer.optimize(build_xml, objective='dps')
    print(f"      Best DPS: {results['dps'].best_fitness:+.2f}%")

    # Optimize for Life
    print("   🟢 Optimizing for Life...")
    results['life'] = optimizer.optimize(build_xml, objective='life')
    print(f"      Best Life: {results['life'].best_fitness:+.2f}%")

    # Optimize for balanced
    print("   🟡 Optimizing for Balanced...")
    results['balanced'] = optimizer.optimize(build_xml, objective='balanced')
    print(f"      Best Balanced: {results['balanced'].best_fitness:+.2f}%")

    # Step 4: Display trade-offs
    print("\n" + "="*80)
    print("PARETO FRONTIER: TRADE-OFF ANALYSIS")
    print("="*80)

    print(f"\n📊 Extreme Solutions:")
    print(f"\n   🔴 MAX DPS BUILD:")
    print(f"      DPS:  {results['dps'].best_fitness_details.dps_change_percent:+.2f}%")
    print(f"      Life: {results['dps'].best_fitness_details.life_change_percent:+.2f}%")
    print(f"      EHP:  {results['dps'].best_fitness_details.ehp_change_percent:+.2f}%")
    print(f"      → Glass cannon, high damage, lower survivability")

    print(f"\n   🟢 MAX LIFE BUILD:")
    print(f"      DPS:  {results['life'].best_fitness_details.dps_change_percent:+.2f}%")
    print(f"      Life: {results['life'].best_fitness_details.life_change_percent:+.2f}%")
    print(f"      EHP:  {results['life'].best_fitness_details.ehp_change_percent:+.2f}%")
    print(f"      → Tank, high survivability, lower damage")

    print(f"\n   🟡 BALANCED BUILD:")
    print(f"      DPS:  {results['balanced'].best_fitness_details.dps_change_percent:+.2f}%")
    print(f"      Life: {results['balanced'].best_fitness_details.life_change_percent:+.2f}%")
    print(f"      EHP:  {results['balanced'].best_fitness_details.ehp_change_percent:+.2f}%")
    print(f"      → Balanced, good at everything")

    # Step 5: Save all builds
    print(f"\n💾 Step 5: Saving all builds...")

    for objective, result in results.items():
        optimized_code = encode_pob_code(result.best_xml)
        filename = f'optimized_build_{objective}.txt'

        with open(filename, 'w') as f:
            f.write(optimized_code)

        print(f"   ✅ {objective}: {filename}")

    # Step 6: Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    print(f"\n💡 Choose build based on content:")

    print(f"\n   🏃 For FAST MAPPING (clear speed):")
    print(f"      → Use MAX DPS BUILD")
    print(f"      → optimized_build_dps.txt")
    print(f"      → Kill everything quickly")

    print(f"\n   🛡️  For HARD BOSSES (survivability):")
    print(f"      → Use MAX LIFE BUILD")
    print(f"      → optimized_build_life.txt")
    print(f"      → Tank big hits")

    print(f"\n   ⚖️  For GENERAL CONTENT (mapping + bosses):")
    print(f"      → Use BALANCED BUILD")
    print(f"      → optimized_build_balanced.txt")
    print(f"      → Good at everything")

    # Calculate DPS loss for going tanky
    dps_loss = (results['dps'].best_fitness_details.dps_change_percent -
                results['life'].best_fitness_details.dps_change_percent)

    life_gain = (results['life'].best_fitness_details.life_change_percent -
                 results['dps'].best_fitness_details.life_change_percent)

    print(f"\n📊 Trade-off Analysis:")
    print(f"   Going from DPS → Life build:")
    print(f"      Cost: {dps_loss:.2f}% DPS")
    print(f"      Gain: {life_gain:+.2f}% Life")
    print(f"      Worth it for: Hard bosses, HC leagues")

    print("\n" + "="*80)
    print("✅ MULTI-OBJECTIVE OPTIMIZATION COMPLETE!")
    print("="*80)
    print("\n📂 Files Created:")
    print("   - optimized_build_dps.txt (max damage)")
    print("   - optimized_build_life.txt (max survivability)")
    print("   - optimized_build_balanced.txt (balanced)")
    print("\n💡 Try all three builds and see which feels best!")
    print("\n")

if __name__ == "__main__":
    main()

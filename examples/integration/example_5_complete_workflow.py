#!/usr/bin/env python3
"""
Example 5: Complete Workflow

Shows a complete optimization workflow:
1. Load and validate build
2. Run all three optimization methods
3. Create all visualizations
4. Compare results
5. Pick the best approach

Use case: Comprehensive optimization with full analysis
"""

import sys
sys.path.insert(0, '../..')

from src.pob.codec import decode_pob_code, encode_pob_code
from src.pob.modifier import get_passive_tree_summary
from src.optimizer.tree_optimizer import GreedyTreeOptimizer
from src.optimizer.genetic_optimizer import GeneticTreeOptimizer
from src.visualization.evolution_plot import create_evolution_report
from src.visualization.tree_diff import visualize_tree_diff, print_tree_diff_summary
import time

def main():
    print("\n" + "="*80)
    print("EXAMPLE 5: Complete Optimization Workflow")
    print("="*80)
    print("\nThis example demonstrates a full optimization pipeline:")
    print("  1. Greedy optimization (fast)")
    print("  2. Genetic algorithm (better)")
    print("  3. Comparison and recommendation")
    print("\n⚠️  Total time: ~15-20 minutes")
    print()

    # Step 1: Load build
    print("="*80)
    print("STEP 1: Load and Validate Build")
    print("="*80)

    with open('../../examples/build1', 'r') as f:
        pob_code = f.read().strip()

    build_xml = decode_pob_code(pob_code)
    summary = get_passive_tree_summary(build_xml)

    print(f"\n📊 Build Information:")
    print(f"   Class: {summary['class_name']}")
    print(f"   Ascendancy: {summary['ascendancy_name']}")
    print(f"   Points allocated: {len(summary['allocated_nodes'])}")
    print(f"   Masteries selected: {len(summary['mastery_effects'])}")
    print(f"   ✅ Build loaded successfully")

    # Step 2: Greedy Optimization
    print("\n" + "="*80)
    print("STEP 2: Greedy Optimization (Fast Local Search)")
    print("="*80)

    print(f"\n🏃 Running greedy optimizer...")
    print(f"   Expected time: ~2 minutes")

    greedy_start = time.time()

    greedy_optimizer = GreedyTreeOptimizer(
        max_iterations=50,
        optimize_masteries=True,
    )

    greedy_result = greedy_optimizer.optimize(
        build_xml,
        objective='dps',
        allow_point_increase=False
    )

    greedy_time = time.time() - greedy_start

    print(f"\n✅ Greedy optimization complete!")
    print(f"   Time: {greedy_time:.1f} seconds ({greedy_time/60:.1f} minutes)")
    print(f"   DPS:  {greedy_result.optimized_stats.dps_change_percent:+.2f}%")
    print(f"   Life: {greedy_result.optimized_stats.life_change_percent:+.2f}%")
    print(f"   EHP:  {greedy_result.optimized_stats.ehp_change_percent:+.2f}%")

    # Save greedy result
    greedy_code = encode_pob_code(greedy_result.optimized_xml)
    with open('optimized_build_greedy.txt', 'w') as f:
        f.write(greedy_code)

    print(f"   💾 Saved: optimized_build_greedy.txt")

    # Step 3: Genetic Algorithm
    print("\n" + "="*80)
    print("STEP 3: Genetic Algorithm (Better Global Search)")
    print("="*80)

    print(f"\n🧬 Running genetic algorithm...")
    print(f"   Expected time: ~10-15 minutes")
    print(f"   (Progress will be shown for each generation)")
    print()

    genetic_start = time.time()

    genetic_optimizer = GeneticTreeOptimizer(
        population_size=30,
        generations=50,
        mutation_rate=0.2,
        optimize_masteries=True,
    )

    genetic_result = genetic_optimizer.optimize(
        build_xml,
        objective='dps',
    )

    genetic_time = time.time() - genetic_start

    print(f"\n✅ Genetic optimization complete!")
    print(f"   Time: {genetic_time:.1f} seconds ({genetic_time/60:.1f} minutes)")
    print(f"   DPS:  {genetic_result.best_fitness_details.dps_change_percent:+.2f}%")
    print(f"   Life: {genetic_result.best_fitness_details.life_change_percent:+.2f}%")
    print(f"   EHP:  {genetic_result.best_fitness_details.ehp_change_percent:+.2f}%")

    # Save genetic result
    genetic_code = encode_pob_code(genetic_result.best_xml)
    with open('optimized_build_genetic.txt', 'w') as f:
        f.write(genetic_code)

    print(f"   💾 Saved: optimized_build_genetic.txt")

    # Step 4: Create visualizations
    print("\n" + "="*80)
    print("STEP 4: Create Visualizations")
    print("="*80)

    print(f"\n📈 Creating evolution plots...")
    plot_files = create_evolution_report(
        genetic_result,
        output_dir='plots',
        base_name='complete_workflow'
    )
    print(f"   ✅ Created {len(plot_files)} evolution plots")

    print(f"\n📄 Creating tree diff reports...")
    greedy_diff = visualize_tree_diff(
        build_xml,
        greedy_result.optimized_xml,
        'tree_diff_greedy.txt'
    )
    print(f"   ✅ Greedy diff: {greedy_diff}")

    genetic_diff = visualize_tree_diff(
        build_xml,
        genetic_result.best_xml,
        'tree_diff_genetic.txt'
    )
    print(f"   ✅ Genetic diff: {genetic_diff}")

    # Step 5: Comparison
    print("\n" + "="*80)
    print("STEP 5: Method Comparison")
    print("="*80)

    print(f"\n📊 Results Comparison:")
    print(f"\n   Method        | Time   | DPS    | Life   | EHP    |")
    print(f"   --------------|--------|--------|--------|--------|")
    print(f"   Greedy        | {greedy_time/60:5.1f}m | {greedy_result.optimized_stats.dps_change_percent:+5.1f}% | "
          f"{greedy_result.optimized_stats.life_change_percent:+5.1f}% | {greedy_result.optimized_stats.ehp_change_percent:+5.1f}% |")
    print(f"   Genetic       | {genetic_time/60:5.1f}m | {genetic_result.best_fitness_details.dps_change_percent:+5.1f}% | "
          f"{genetic_result.best_fitness_details.life_change_percent:+5.1f}% | {genetic_result.best_fitness_details.ehp_change_percent:+5.1f}% |")

    # Calculate improvements
    dps_improvement = (genetic_result.best_fitness_details.dps_change_percent -
                       greedy_result.optimized_stats.dps_change_percent)

    time_cost = genetic_time / greedy_time

    print(f"\n   💡 Analysis:")
    print(f"      Genetic is {dps_improvement:+.2f}% better for DPS")
    print(f"      But takes {time_cost:.1f}x longer")

    if dps_improvement > 2.0:
        print(f"      ✅ Genetic algorithm worth the extra time!")
    elif dps_improvement > 0.5:
        print(f"      ⚖️  Genetic algorithm slightly better (marginal gain)")
    else:
        print(f"      ⏱️  Greedy is sufficient (fast and nearly optimal)")

    # Step 6: Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)

    print(f"\n🎯 For your build:")

    if dps_improvement > 2.0:
        print(f"\n   ✅ Use GENETIC ALGORITHM result")
        print(f"      File: optimized_build_genetic.txt")
        print(f"      Why: Significantly better (+{dps_improvement:.2f}% DPS)")
        winner = "genetic"
    else:
        print(f"\n   ⏱️  Use GREEDY result")
        print(f"      File: optimized_build_greedy.txt")
        print(f"      Why: Fast and nearly optimal (only {abs(dps_improvement):.2f}% worse)")
        winner = "greedy"

    # Step 7: Summary
    print("\n" + "="*80)
    print("WORKFLOW COMPLETE!")
    print("="*80)

    print(f"\n📂 Files Created:")
    print(f"   Builds:")
    print(f"      - optimized_build_greedy.txt")
    print(f"      - optimized_build_genetic.txt")
    print(f"   Reports:")
    print(f"      - tree_diff_greedy.txt")
    print(f"      - tree_diff_genetic.txt")
    print(f"   Plots:")
    print(f"      - plots/complete_workflow_progress.png")
    print(f"      - plots/complete_workflow_distribution.png")
    print(f"      - plots/complete_workflow_convergence.png")

    print(f"\n🏆 Winner: {winner.upper()}")
    print(f"   Import optimized_build_{winner}.txt into Path of Building")

    print(f"\n⏱️  Total workflow time: {(time.time() - greedy_start - greedy_time):.1f} seconds")

    print(f"\n💡 Next steps:")
    print(f"   1. Review tree_diff_{winner}.txt for detailed changes")
    print(f"   2. View plots to see optimization progress")
    print(f"   3. Import optimized_build_{winner}.txt into PoB")
    print(f"   4. Test the build in-game!")

    print("\n")

if __name__ == "__main__":
    main()

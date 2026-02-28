#!/usr/bin/env python3
"""
Example 2: Genetic Algorithm Optimization

Shows advanced optimization with genetic algorithm:
1. Load build
2. Run genetic algorithm for better results
3. Visualize evolution progress
4. Compare with greedy results

Use case: Finding better global optimum, novel tree configurations
"""

import sys
sys.path.insert(0, '../..')

from src.pob.codec import decode_pob_code, encode_pob_code
from src.optimizer.genetic_optimizer import GeneticTreeOptimizer
from src.visualization.evolution_plot import create_evolution_report
from src.visualization.tree_diff import visualize_tree_diff

def main():
    print("\n" + "="*80)
    print("EXAMPLE 2: Genetic Algorithm Optimization")
    print("="*80)

    # Step 1: Load build
    print("\n📖 Step 1: Loading build...")
    with open('../../examples/build1', 'r') as f:
        pob_code = f.read().strip()

    build_xml = decode_pob_code(pob_code)
    print("   ✅ Build loaded")

    # Step 2: Create genetic optimizer
    print("\n🧬 Step 2: Creating genetic algorithm optimizer...")
    optimizer = GeneticTreeOptimizer(
        population_size=30,      # 30 individuals in population
        generations=50,          # Evolve for 50 generations
        mutation_rate=0.2,       # 20% mutation chance
        crossover_rate=0.8,      # 80% crossover chance
        elitism_count=5,         # Preserve 5 best
        optimize_masteries=True, # Optimize mastery selections
    )
    print("   ✅ Genetic algorithm configured")
    print(f"      Population: 30 individuals")
    print(f"      Generations: 50")
    print(f"      Total evaluations: ~1,500")

    # Step 3: Run optimization
    print("\n🚀 Step 3: Running genetic algorithm...")
    print("   ⚠️  This will take 10-20 minutes")
    print("   💡 Tip: The algorithm will show progress for each generation")
    print()

    result = optimizer.optimize(
        build_xml,
        objective='dps',
    )

    # Step 4: Display results
    print("\n" + "="*80)
    print("GENETIC ALGORITHM RESULTS")
    print("="*80)

    print(f"\n📊 Final Improvements:")
    print(f"   DPS:  {result.best_fitness_details.dps_change_percent:+.2f}%")
    print(f"   Life: {result.best_fitness_details.life_change_percent:+.2f}%")
    print(f"   EHP:  {result.best_fitness_details.ehp_change_percent:+.2f}%")

    print(f"\n🧬 Evolution Statistics:")
    print(f"   Generations completed: {result.generations}")
    print(f"   Best fitness: {result.best_fitness:+.2f}%")
    print(f"   Initial fitness: {result.best_fitness_history[0]:+.2f}%")
    print(f"   Total improvement: {result.best_fitness - result.best_fitness_history[0]:+.2f}%")

    # Step 5: Create visualizations
    print(f"\n📈 Step 5: Creating visualizations...")

    # Evolution progress plots
    plot_files = create_evolution_report(
        result,
        output_dir='plots',
        base_name='genetic_evolution'
    )

    print(f"   ✅ Created {len(plot_files)} plots:")
    for plot_type, filepath in plot_files.items():
        print(f"      - {plot_type}: {filepath}")

    # Tree difference report
    diff_file = visualize_tree_diff(
        result.original_xml,
        result.best_xml,
        'tree_diff_genetic.txt'
    )
    print(f"   ✅ Tree diff: {diff_file}")

    # Step 6: Save optimized build
    print(f"\n💾 Step 6: Saving optimized build...")
    optimized_code = encode_pob_code(result.best_xml)

    with open('optimized_build_genetic.txt', 'w') as f:
        f.write(optimized_code)

    print(f"   ✅ Saved to: optimized_build_genetic.txt")

    # Step 7: Analysis
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)

    print(f"\n🎯 Key Insights:")

    # Check if converged
    if result.generations < 50:
        print(f"   ✅ Algorithm converged early (gen {result.generations}/50)")
        print(f"      No improvement for 10+ generations")
    else:
        print(f"   ⏱️  Ran all 50 generations")

    # Check improvement trajectory
    early_improvement = result.best_fitness_history[10] - result.best_fitness_history[0]
    late_improvement = result.best_fitness - result.best_fitness_history[-10]

    print(f"\n   📊 Improvement Trajectory:")
    print(f"      First 10 generations: {early_improvement:+.2f}%")
    print(f"      Last 10 generations:  {late_improvement:+.2f}%")

    if abs(late_improvement) < 0.5:
        print(f"      💡 Optimization reached plateau")

    print("\n" + "="*80)
    print("✅ GENETIC OPTIMIZATION COMPLETE!")
    print("="*80)
    print("\n📂 Files Created:")
    print("   - optimized_build_genetic.txt (PoB import code)")
    print("   - plots/genetic_evolution_progress.png")
    print("   - plots/genetic_evolution_distribution.png")
    print("   - plots/genetic_evolution_convergence.png")
    print("   - tree_diff_genetic.txt")
    print("\n💡 Next steps:")
    print("   1. View plots to see evolution progress")
    print("   2. Read tree_diff_genetic.txt for detailed changes")
    print("   3. Import optimized_build_genetic.txt into Path of Building")
    print("\n")

if __name__ == "__main__":
    main()

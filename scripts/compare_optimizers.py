#!/usr/bin/env python3
"""
Compare greedy vs genetic optimizer performance.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.optimizer.tree_optimizer import GreedyTreeOptimizer
from src.optimizer.genetic_optimizer import GeneticTreeOptimizer
from src.pob.codec import encode_pob_code


def save_optimization_result(result_xml: str, optimizer_name: str, output_dir: Path) -> Path:
    """Save optimization result to files and return the PoB code path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save XML
    xml_path = output_dir / f"{optimizer_name}_{timestamp}.xml"
    with open(xml_path, 'w') as f:
        f.write(result_xml)

    # Save PoB code
    pob_code = encode_pob_code(result_xml)
    pob_path = output_dir / f"{optimizer_name}_{timestamp}.txt"
    with open(pob_path, 'w') as f:
        f.write(pob_code)

    return pob_path


def main():
    # Setup output directory
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "output"

    # Load test build
    with open('tests/fixtures/builds/cyclone_slayer.xml', 'r') as f:
        build_xml = f.read()

    print("=" * 70)
    print("OPTIMIZER COMPARISON: Greedy vs Genetic")
    print("=" * 70)
    print(f"Workers: {os.cpu_count()} CPUs")
    print()

    # Run Greedy Optimizer
    print("=" * 70)
    print("GREEDY OPTIMIZER (20 iterations, batch evaluation)")
    print("=" * 70)

    greedy = GreedyTreeOptimizer(
        max_iterations=20,
        min_improvement=0.1,
        optimize_masteries=True,
        optimize_jewel_sockets=False,  # Skip jewel sockets for fair comparison
        max_workers=os.cpu_count(),
        use_batch_evaluation=True,
        show_progress=True,
    )

    greedy_start = time.time()
    greedy_result = greedy.optimize(build_xml, objective='balanced')
    greedy_time = time.time() - greedy_start

    print(f"\nGreedy Results:")
    print(f"  Time: {greedy_time:.1f}s")
    print(f"  DPS:  {greedy_result.optimized_stats.dps_change_percent:+.2f}%")
    print(f"  Life: {greedy_result.optimized_stats.life_change_percent:+.2f}%")
    print(f"  EHP:  {greedy_result.optimized_stats.ehp_change_percent:+.2f}%")
    print(f"  Modifications: {len(greedy_result.modifications_applied)}")

    # Save greedy result
    greedy_pob_path = save_optimization_result(greedy_result.optimized_xml, "greedy", output_dir)
    print(f"\n  Saved to: {output_dir.resolve()}/")
    print(f"    PoB code: {greedy_pob_path.name}")

    print()

    # Run Genetic Optimizer
    print("=" * 70)
    print("GENETIC OPTIMIZER (10 generations, pop=20, batch evaluation)")
    print("=" * 70)

    with GeneticTreeOptimizer(
        population_size=20,
        generations=10,
        mutation_rate=0.3,
        crossover_rate=0.7,
        elitism_count=2,
        optimize_masteries=True,
        optimize_jewel_sockets=False,
        max_workers=os.cpu_count(),
        use_batch_evaluation=True,
        show_progress=True,
    ) as genetic:
        genetic_start = time.time()
        genetic_result = genetic.optimize(build_xml, objective='balanced')
        genetic_time = time.time() - genetic_start

    print(f"\nGenetic Results:")
    print(f"  Time: {genetic_time:.1f}s")
    print(f"  DPS:  {genetic_result.best_fitness_details.dps_change_percent:+.2f}%")
    print(f"  Life: {genetic_result.best_fitness_details.life_change_percent:+.2f}%")
    print(f"  EHP:  {genetic_result.best_fitness_details.ehp_change_percent:+.2f}%")
    print(f"  Generations: {len(genetic_result.best_fitness_history)}")

    # Save genetic result
    genetic_pob_path = save_optimization_result(genetic_result.best_xml, "genetic", output_dir)
    print(f"\n  Saved to: {output_dir.resolve()}/")
    print(f"    PoB code: {genetic_pob_path.name}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Optimizer':<15} {'Time':>10} {'DPS':>10} {'Life':>10} {'EHP':>10}")
    print("-" * 55)
    print(f"{'Greedy':<15} {greedy_time:>9.1f}s {greedy_result.optimized_stats.dps_change_percent:>+9.2f}% {greedy_result.optimized_stats.life_change_percent:>+9.2f}% {greedy_result.optimized_stats.ehp_change_percent:>+9.2f}%")
    print(f"{'Genetic':<15} {genetic_time:>9.1f}s {genetic_result.best_fitness_details.dps_change_percent:>+9.2f}% {genetic_result.best_fitness_details.life_change_percent:>+9.2f}% {genetic_result.best_fitness_details.ehp_change_percent:>+9.2f}%")


if __name__ == '__main__':
    main()

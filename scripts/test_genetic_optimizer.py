#!/usr/bin/env python3
"""
Test genetic optimizer with result saving.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    print("GENETIC OPTIMIZER TEST")
    print("=" * 70)
    print(f"Workers: {os.cpu_count()} CPUs")
    print(f"Output directory: {output_dir.resolve()}")
    print()

    print("=" * 70)
    print("Running genetic optimizer (10 generations, pop=20, batch evaluation)")
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
        start_time = time.time()
        result = genetic.optimize(build_xml, objective='balanced')
        elapsed = time.time() - start_time

    print(f"\nResults:")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  DPS:  {result.best_fitness_details.dps_change_percent:+.2f}%")
    print(f"  Life: {result.best_fitness_details.life_change_percent:+.2f}%")
    print(f"  EHP:  {result.best_fitness_details.ehp_change_percent:+.2f}%")
    print(f"  Balanced: {result.best_fitness:+.2f}%")
    print(f"  Generations: {len(result.best_fitness_history)}")

    # Save result
    pob_path = save_optimization_result(result.best_xml, "genetic", output_dir)
    print(f"\nSaved to: {output_dir.resolve()}/")
    print(f"  XML: genetic_*.xml")
    print(f"  PoB code: {pob_path.name}")


if __name__ == '__main__':
    main()

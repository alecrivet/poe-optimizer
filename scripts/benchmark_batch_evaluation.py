#!/usr/bin/env python3
"""
Compare batch evaluation vs regular evaluation performance.
Tests that both produce the same results.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pob.caller import PoBCalculator
from pob.worker_pool import PoBWorkerPool

def main():
    # Load test build
    build_path = Path(__file__).parent.parent / "tests/fixtures/builds/cyclone_slayer.xml"
    with open(build_path, "r") as f:
        build_xml = f.read()

    num_builds = 10
    print(f"=== Testing Batch vs Regular Evaluation ({num_builds} builds) ===\n")

    # Create simple modifications by changing the xml slightly
    builds = []
    for i in range(num_builds):
        # Create slightly different builds by changing the build name
        # (shouldn't affect stats but exercises the pipeline)
        modified = build_xml.replace('className="Duelist"', f'className="Duelist" testId="{i}"')
        builds.append(modified)

    # Regular evaluation (uses Lua subprocess each time)
    print("Regular evaluation (subprocess per build)...")
    calc = PoBCalculator()
    regular_start = time.time()
    regular_results = []
    for i, xml in enumerate(builds):
        result = calc.evaluate_build(xml, use_xml_stats=False)  # Force Lua evaluation
        regular_results.append(result)
        print(f"  Build {i}: Life={result.get('life')}, DPS={result.get('combinedDPS'):.0f}")
    regular_time = time.time() - regular_start
    print(f"Regular evaluation time: {regular_time:.2f}s\n")

    # Batch evaluation (persistent worker pool)
    print("Batch evaluation (persistent worker)...")
    with PoBWorkerPool(num_workers=1) as pool:
        batch_start = time.time()
        batch_results = []
        for i, xml in enumerate(builds):
            result = pool.evaluate(xml)
            if result.success:
                batch_results.append(result.stats)
                print(f"  Build {i}: Life={result.stats.get('life')}, DPS={result.stats.get('combinedDPS'):.0f}")
            else:
                print(f"  Build {i}: FAILED - {result.error}")
                batch_results.append({})
        batch_time = time.time() - batch_start
    print(f"Batch evaluation time: {batch_time:.2f}s\n")

    # Compare results
    print("=== Comparison ===")
    match = True
    for i in range(len(builds)):
        r_life = regular_results[i].get('life', 0)
        b_life = batch_results[i].get('life', 0)
        r_dps = regular_results[i].get('combinedDPS', 0)
        b_dps = batch_results[i].get('combinedDPS', 0)

        if abs(r_life - b_life) > 1 or abs(r_dps - b_dps) > 1:
            print(f"  Build {i}: MISMATCH - Regular({r_life}, {r_dps}) vs Batch({b_life}, {b_dps})")
            match = False
        else:
            print(f"  Build {i}: MATCH")

    print(f"\n=== Summary ===")
    print(f"Regular time: {regular_time:.2f}s ({regular_time/len(builds):.2f}s per build)")
    print(f"Batch time:   {batch_time:.2f}s ({batch_time/len(builds):.2f}s per build)")
    if batch_time > 0:
        print(f"Speedup:      {regular_time/batch_time:.2f}x")
    print(f"Results match: {'YES' if match else 'NO'}")

if __name__ == "__main__":
    main()

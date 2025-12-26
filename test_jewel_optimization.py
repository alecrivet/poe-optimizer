#!/usr/bin/env python3
"""
Test jewel socket optimization on cyclone build.

This script runs the greedy optimizer with jewel socket swapping enabled
to see if moving jewels between sockets improves the build.
"""

import sys
import time

from src.optimizer.tree_optimizer import GreedyTreeOptimizer
from src.pob.codec import encode_pob_code
from src.pob.jewel.registry import JewelRegistry

# Load cyclone build
print("Loading cyclone slayer build...")
with open('tests/fixtures/builds/cyclone_slayer.xml', 'r') as f:
    build_xml = f.read()

# Show current jewels
print("\nCurrent jewels:")
registry = JewelRegistry.from_build_xml(build_xml)
for jewel in registry.all_jewels:
    print(f"  - {jewel.category.value}: {jewel.display_name} (socket {jewel.socket_node_id})")

# Run greedy optimizer WITH jewel socket optimization
print("\n" + "="*60)
print("Running greedy optimizer WITH jewel socket swapping...")
print("="*60)

optimizer = GreedyTreeOptimizer(
    max_iterations=20,
    min_improvement=0.1,
    optimize_masteries=True,
    optimize_jewel_sockets=True,  # ENABLE JEWEL SOCKET OPTIMIZATION
)

start_time = time.time()
result = optimizer.optimize(build_xml, objective='balanced')
elapsed = time.time() - start_time

print(f"\n✓ Optimization completed in {elapsed:.1f}s")
print(f"\nResults:")
print(f"  DPS change:  {result.optimized_stats.dps_change_percent:+.2f}%")
print(f"  Life change: {result.optimized_stats.life_change_percent:+.2f}%")
print(f"  EHP change:  {result.optimized_stats.ehp_change_percent:+.2f}%")
print(f"\nModifications applied: {len(result.modifications_applied)}")

# Show what changed
if result.modifications_applied:
    print("\nChanges made:")
    for mod in result.modifications_applied:
        print(f"  {mod['iteration']}. {mod['modification']} ({mod['improvement_pct']:+.2f}%)")

    # Check for jewel swaps
    jewel_swaps = [m for m in result.modifications_applied if 'jewel' in m['modification'].lower()]
    if jewel_swaps:
        print(f"\n🎯 Found {len(jewel_swaps)} jewel socket swap(s)!")
        for swap in jewel_swaps:
            print(f"   - {swap['modification']}")
    else:
        print("\nNo jewel socket swaps were beneficial (current placement is optimal)")

# Save results
output_file = 'output/cyclone_jewel_optimized.xml'
with open(output_file, 'w') as f:
    f.write(result.optimized_xml)

pob_code = encode_pob_code(result.optimized_xml)
with open('output/cyclone_jewel_optimized.txt', 'w') as f:
    f.write(pob_code)

print(f"\n✓ Saved optimized build to {output_file}")
print(f"✓ Saved PoB code to output/cyclone_jewel_optimized.txt")

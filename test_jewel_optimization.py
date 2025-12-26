#!/usr/bin/env python3
"""
Test jewel socket optimization on cyclone build.

This script runs the greedy optimizer with jewel socket swapping enabled
to see if moving jewels between sockets improves the build.

Enhanced to test:
- Socket discovery (including empty sockets)
- Pathing cost calculation
- Moves to empty sockets (not just swaps)
"""

import sys
import time

from src.optimizer.tree_optimizer import GreedyTreeOptimizer
from src.pob.codec import encode_pob_code
from src.pob.jewel.registry import JewelRegistry
from src.pob.jewel.socket_optimizer import SocketDiscovery
from src.pob.modifier import get_passive_tree_summary

# Load cyclone build
print("Loading cyclone slayer build...")
with open('tests/fixtures/builds/cyclone_slayer.xml', 'r') as f:
    build_xml = f.read()

# Show current jewels
print("\nCurrent jewels:")
registry = JewelRegistry.from_build_xml(build_xml)
for jewel in registry.all_jewels:
    print(f"  - {jewel.category.value}: {jewel.display_name} (socket {jewel.socket_node_id})")

# Show socket discovery info
print("\n--- Socket Discovery ---")
from src.pob.tree_parser import load_passive_tree
tree_graph = load_passive_tree()
discovery = SocketDiscovery(tree_graph)
all_sockets = discovery.discover_all_sockets()
print(f"Total jewel sockets discovered: {len(all_sockets)}")
print(f"  - Regular sockets: {sum(1 for s in all_sockets.values() if s.socket_type.value == 'regular')}")
print(f"  - Large cluster sockets: {sum(1 for s in all_sockets.values() if s.socket_type.value == 'large_cluster')}")

# Show socket distances
summary = get_passive_tree_summary(build_xml)
allocated_nodes = set(summary['allocated_nodes'])
print(f"\nAllocated nodes: {len(allocated_nodes)}")

socket_distances = discovery.calculate_socket_distances(allocated_nodes)
print(f"\nSocket distances from current tree:")
occupied_sockets = {j.socket_node_id for j in registry.all_jewels if j.socket_node_id}
for socket_id, distance in sorted(socket_distances.items(), key=lambda x: x[1]):
    status = "OCCUPIED" if socket_id in occupied_sockets else "empty"
    if distance <= 10:  # Only show sockets within 10 points
        print(f"  Socket {socket_id}: {distance} pts ({status})")

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

    # Check for jewel moves/swaps
    jewel_changes = [m for m in result.modifications_applied if 'jewel' in m['modification'].lower()]
    if jewel_changes:
        print(f"\n🎯 Found {len(jewel_changes)} jewel socket change(s)!")
        for change in jewel_changes:
            print(f"   - {change['modification']}")
    else:
        print("\nNo jewel socket changes were beneficial (current placement is optimal)")

# Save results
output_file = 'output/cyclone_jewel_optimized.xml'
with open(output_file, 'w') as f:
    f.write(result.optimized_xml)

pob_code = encode_pob_code(result.optimized_xml)
with open('output/cyclone_jewel_optimized.txt', 'w') as f:
    f.write(pob_code)

print(f"\n✓ Saved optimized build to {output_file}")
print(f"✓ Saved PoB code to output/cyclone_jewel_optimized.txt")

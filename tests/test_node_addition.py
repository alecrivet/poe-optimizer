#!/usr/bin/env python3
"""
Quick test for node addition functionality.
"""

import logging
from src.pob.codec import decode_pob_code
from src.pob.modifier import get_passive_tree_summary
from src.optimizer.tree_optimizer import GreedyTreeOptimizer

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_node_addition():
    """Test that node addition generates candidates."""
    print("\n" + "="*80)
    print("Testing Node Addition Integration")
    print("="*80)

    # Load build
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    summary = get_passive_tree_summary(xml)

    print(f"\n📊 Build Info:")
    print(f"   Allocated nodes: {len(summary['allocated_nodes'])}")
    print(f"   Mastery effects: {len(summary['mastery_effects'])}")
    print(f"   Class: {summary['class_name']}")
    print(f"   Ascendancy: {summary['ascendancy_name']}")

    # Create optimizer with node addition enabled
    print(f"\n🚀 Initializing optimizer with node addition...")
    optimizer = GreedyTreeOptimizer(
        max_iterations=1,  # Just one iteration for testing
        optimize_masteries=True,
        enable_node_addition=True,
    )

    # Generate candidates
    print(f"\n🔍 Generating candidates...")
    allocated_nodes = set(summary['allocated_nodes'])

    candidates = optimizer._generate_candidates(
        current_xml=xml,
        allocated_nodes=allocated_nodes,
        original_points=len(allocated_nodes),
        allow_point_increase=True,
        objective='dps'
    )

    print(f"\n✅ Generated {len(candidates)} candidates")

    # Count candidate types
    mastery_opts = sum(1 for name in candidates if 'mastery' in name.lower())
    removals = sum(1 for name in candidates if 'Remove' in name)
    additions = sum(1 for name in candidates if 'Add' in name)

    print(f"   - Mastery optimizations: {mastery_opts}")
    print(f"   - Node removals: {removals}")
    print(f"   - Node additions: {additions}")

    if additions > 0:
        print(f"\n🎉 SUCCESS! Node addition is working!")
        print(f"\nSample addition candidates:")
        for name in list(candidates.keys()):
            if 'Add' in name:
                print(f"   - {name}")
                # Only show first 5
                if name == list(k for k in candidates if 'Add' in k)[4]:
                    break
    else:
        print(f"\n⚠️  WARNING: No node additions generated")

    print("\n" + "="*80)

if __name__ == "__main__":
    test_node_addition()

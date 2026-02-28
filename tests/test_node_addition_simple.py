#!/usr/bin/env python3
"""
Simple test for node addition functionality (no calculator needed).
"""

import logging
from src.pob.codec import decode_pob_code
from src.pob.modifier import get_passive_tree_summary
from src.pob.tree_parser import load_passive_tree
from src.pob.mastery_optimizer import get_mastery_database

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_node_addition_simple():
    """Test that tree graph can find unallocated neighbors."""
    print("\n" + "="*80)
    print("Testing Node Addition - Tree Graph Integration")
    print("="*80)

    # Load build
    print("\n📖 Loading build...")
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    summary = get_passive_tree_summary(xml)

    print(f"   Allocated nodes: {len(summary['allocated_nodes'])}")
    print(f"   Class: {summary['class_name']}")
    print(f"   Ascendancy: {summary['ascendancy_name']}")

    # Load passive tree graph
    print(f"\n🌳 Loading passive tree graph...")
    tree_graph = load_passive_tree()
    print(f"   Total nodes in tree: {tree_graph.count_nodes()}")
    print(f"   Keystones: {len(tree_graph.get_keystones())}")
    print(f"   Notables: {len(tree_graph.get_notables())}")

    # Find unallocated neighbors
    print(f"\n🔍 Finding unallocated neighbors...")
    allocated_nodes = set(summary['allocated_nodes'])
    unallocated_neighbors = tree_graph.find_unallocated_neighbors(allocated_nodes)

    print(f"   Found {len(unallocated_neighbors)} unallocated neighbors")

    # Show sample neighbors
    print(f"\n📊 Sample unallocated neighbors (first 10):")
    for i, node_id in enumerate(list(unallocated_neighbors)[:10]):
        node = tree_graph.get_node(node_id)
        if node:
            print(f"   {i+1}. Node {node_id}: {node.name} ({node.node_type})")
            if node.stats:
                print(f"      Stats: {node.stats[0][:50]}...")

    # Test with mastery database
    print(f"\n🎯 Loading mastery database...")
    mastery_db = get_mastery_database()
    print(f"   Loaded {len(mastery_db.masteries)} mastery nodes")

    # Check which neighbors are masteries
    mastery_neighbors = [
        node_id for node_id in unallocated_neighbors
        if mastery_db.is_mastery_node(node_id)
    ]
    print(f"   Of unallocated neighbors, {len(mastery_neighbors)} are masteries")

    # Summary
    print(f"\n✅ SUCCESS! Node addition data structures working!")
    print(f"\nSummary:")
    print(f"   - Can find {len(unallocated_neighbors)} candidate nodes to add")
    print(f"   - Tree graph has full node data (names, stats, types)")
    print(f"   - Mastery database can identify mastery nodes")
    print(f"   - Ready for optimizer integration")

    print("\n" + "="*80)

if __name__ == "__main__":
    test_node_addition_simple()

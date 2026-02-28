#!/usr/bin/env python3
"""
Debug script to verify passive tree node modifications are working.

This checks if XML is actually being modified when we remove nodes.
"""

from src.pob.codec import decode_pob_code
from src.pob.modifier import modify_passive_tree_nodes, get_passive_tree_summary

def main():
    print("=" * 70)
    print("Debugging Passive Tree Node Modifications")
    print("=" * 70)

    # Load build2
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    original_xml = decode_pob_code(code)

    # Get original tree summary
    print("\n1. Original passive tree:")
    original_summary = get_passive_tree_summary(original_xml)
    print(f"   Total nodes: {original_summary['total_nodes']}")
    print(f"   Class: {original_summary['class_name']}")
    print(f"   Ascendancy: {original_summary['ascendancy_name']}")
    print(f"   Allocated nodes (first 20): {list(original_summary['allocated_nodes'])[:20]}")

    # Get some nodes to remove
    allocated_nodes = list(original_summary['allocated_nodes'])
    nodes_to_remove_5 = allocated_nodes[:5]
    nodes_to_remove_10 = allocated_nodes[:10]

    print(f"\n2. Removing first 5 nodes:")
    print(f"   Nodes to remove: {nodes_to_remove_5}")

    # Modify XML
    modified_xml_5 = modify_passive_tree_nodes(
        original_xml,
        nodes_to_remove=nodes_to_remove_5
    )

    # Check modified tree
    modified_summary_5 = get_passive_tree_summary(modified_xml_5)
    print(f"   Modified total nodes: {modified_summary_5['total_nodes']}")
    print(f"   Change: {modified_summary_5['total_nodes'] - original_summary['total_nodes']} nodes")

    # Verify specific nodes are gone
    still_allocated = [n for n in nodes_to_remove_5 if n in modified_summary_5['allocated_nodes']]
    if still_allocated:
        print(f"   ❌ ERROR: These nodes still allocated: {still_allocated}")
    else:
        print(f"   ✓ All 5 nodes successfully removed from XML")

    print(f"\n3. Removing first 10 nodes:")
    print(f"   Nodes to remove: {nodes_to_remove_10}")

    modified_xml_10 = modify_passive_tree_nodes(
        original_xml,
        nodes_to_remove=nodes_to_remove_10
    )

    modified_summary_10 = get_passive_tree_summary(modified_xml_10)
    print(f"   Modified total nodes: {modified_summary_10['total_nodes']}")
    print(f"   Change: {modified_summary_10['total_nodes'] - original_summary['total_nodes']} nodes")

    still_allocated_10 = [n for n in nodes_to_remove_10 if n in modified_summary_10['allocated_nodes']]
    if still_allocated_10:
        print(f"   ❌ ERROR: These nodes still allocated: {still_allocated_10}")
    else:
        print(f"   ✓ All 10 nodes successfully removed from XML")

    # Show a sample of the XML to verify changes
    print("\n4. XML Verification:")

    # Extract Spec element from original
    import xml.etree.ElementTree as ET
    original_root = ET.fromstring(original_xml)
    original_spec = original_root.find(".//Tree/Spec")
    if original_spec is not None:
        original_spec_text = ET.tostring(original_spec, encoding='unicode')
        print(f"   Original Spec length: {len(original_spec_text)} chars")
        print(f"   Original Spec (first 200 chars): {original_spec_text[:200]}...")

    # Extract Spec element from modified
    modified_root_5 = ET.fromstring(modified_xml_5)
    modified_spec_5 = modified_root_5.find(".//Tree/Spec")
    if modified_spec_5 is not None:
        modified_spec_text_5 = ET.tostring(modified_spec_5, encoding='unicode')
        print(f"   Modified Spec length (5 removed): {len(modified_spec_text_5)} chars")
        print(f"   Modified Spec (first 200 chars): {modified_spec_text_5[:200]}...")

        if original_spec_text == modified_spec_text_5:
            print(f"   ❌ ERROR: Spec XML is IDENTICAL (no changes made!)")
        else:
            print(f"   ✓ Spec XML is different (changes detected)")

    print("\n" + "=" * 70)
    print("Conclusion:")
    print("=" * 70)
    print("If XML modifications are working but HeadlessWrapper shows 0% change,")
    print("then the issue is with HeadlessWrapper not re-parsing the tree.")
    print("=" * 70)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Debug script to check if HeadlessWrapper properly parses passive tree changes.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

from src.pob.codec import decode_pob_code
from src.pob.modifier import modify_passive_tree_nodes, get_passive_tree_summary

def evaluate_with_debug(build_xml: str) -> dict:
    """
    Evaluate build using debug evaluator that outputs tree info.
    """
    pob_src_path = Path("PathOfBuilding/src").resolve()
    evaluator_script = Path("src/pob/evaluator_debug.lua").resolve()

    # Create temporary file for build XML
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.xml',
        delete=False,
        encoding='utf-8'
    ) as temp_file:
        temp_file.write(build_xml)
        temp_path = temp_file.name

    try:
        # Run the debug evaluator
        result = subprocess.run(
            ["luajit", str(evaluator_script), temp_path],
            cwd=str(pob_src_path),
            capture_output=True,
            text=True,
            timeout=30
        )

        # Parse JSON output
        json_lines = [line for line in result.stdout.split('\n') if line.strip().startswith('{')]
        if not json_lines:
            print(f"ERROR: No JSON output")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return None

        json_str = json_lines[-1].strip()
        output = json.loads(json_str)

        return output

    finally:
        # Clean up
        try:
            os.unlink(temp_path)
        except:
            pass

def main():
    print("=" * 70)
    print("Debugging HeadlessWrapper Passive Tree Parsing")
    print("=" * 70)

    # Load build2
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    original_xml = decode_pob_code(code)

    # Get XML tree info
    print("\n1. XML Analysis - Original:")
    original_tree = get_passive_tree_summary(original_xml)
    print(f"   Nodes in XML: {original_tree['total_nodes']}")
    allocated_nodes = list(original_tree['allocated_nodes'])
    print(f"   Sample nodes: {allocated_nodes[:10]}")

    # Get what HeadlessWrapper sees
    print("\n2. HeadlessWrapper Analysis - Original:")
    original_result = evaluate_with_debug(original_xml)
    if original_result and 'debug' in original_result:
        debug = original_result['debug']
        print(f"   Nodes HeadlessWrapper sees:")
        print(f"     tree.allocNodes count: {debug['treeNodeCount']}")
        print(f"     spec.allocNodes count: {debug['specNodeCount']}")
        print(f"     Sample from tree: {debug['treeNodesSample']}")
        print(f"     Sample from spec: {debug['specNodesSample']}")

        stats = original_result['stats']
        print(f"   Stats:")
        print(f"     CombinedDPS: {stats['combinedDPS']:,.0f}")
        print(f"     Life: {stats['life']:,.0f}")

    # Create modified XML
    print("\n3. Creating Modified Build (removing 5 nodes):")
    nodes_to_remove = allocated_nodes[:5]
    print(f"   Removing nodes: {nodes_to_remove}")

    modified_xml = modify_passive_tree_nodes(
        original_xml,
        nodes_to_remove=nodes_to_remove
    )

    # Get modified XML tree info
    print("\n4. XML Analysis - Modified:")
    modified_tree = get_passive_tree_summary(modified_xml)
    print(f"   Nodes in XML: {modified_tree['total_nodes']}")
    print(f"   Change: {modified_tree['total_nodes'] - original_tree['total_nodes']} nodes")

    # Check if removed nodes are gone
    still_present = [n for n in nodes_to_remove if n in modified_tree['allocated_nodes']]
    if still_present:
        print(f"   ❌ ERROR: Nodes still in XML: {still_present}")
    else:
        print(f"   ✓ Nodes successfully removed from XML")

    # Get what HeadlessWrapper sees for modified
    print("\n5. HeadlessWrapper Analysis - Modified:")
    modified_result = evaluate_with_debug(modified_xml)
    if modified_result and 'debug' in modified_result:
        debug = modified_result['debug']
        print(f"   Nodes HeadlessWrapper sees:")
        print(f"     tree.allocNodes count: {debug['treeNodeCount']}")
        print(f"     spec.allocNodes count: {debug['specNodeCount']}")
        print(f"     Sample from tree: {debug['treeNodesSample']}")
        print(f"     Sample from spec: {debug['specNodesSample']}")

        stats = modified_result['stats']
        print(f"   Stats:")
        print(f"     CombinedDPS: {stats['combinedDPS']:,.0f}")
        print(f"     Life: {stats['life']:,.0f}")

    # Compare
    print("\n6. Comparison:")
    print("-" * 70)

    if original_result and modified_result:
        orig_debug = original_result['debug']
        mod_debug = modified_result['debug']
        orig_stats = original_result['stats']
        mod_stats = modified_result['stats']

        tree_count_change = mod_debug['treeNodeCount'] - orig_debug['treeNodeCount']
        spec_count_change = mod_debug['specNodeCount'] - orig_debug['specNodeCount']
        dps_change = mod_stats['combinedDPS'] - orig_stats['combinedDPS']
        life_change = mod_stats['life'] - orig_stats['life']

        print(f"   Tree node count change: {tree_count_change}")
        print(f"   Spec node count change: {spec_count_change}")
        print(f"   DPS change: {dps_change:,.0f}")
        print(f"   Life change: {life_change:,.0f}")

        print("\n7. Diagnosis:")
        print("-" * 70)

        if tree_count_change == 0 and spec_count_change == 0:
            print("   ❌ PROBLEM: HeadlessWrapper sees SAME node count")
            print("      → HeadlessWrapper is NOT parsing tree changes from XML")
            print("      → This explains why stats don't change")
        elif tree_count_change != 0 or spec_count_change != 0:
            if dps_change == 0 and life_change == 0:
                print("   ⚠️  PROBLEM: HeadlessWrapper sees different nodes BUT stats unchanged")
                print("      → Tree is parsed correctly")
                print("      → But calculations don't use the tree data")
                print("      → This is a deeper HeadlessWrapper issue")
            else:
                print("   ✓ SUCCESS: Tree changes detected and stats changed")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

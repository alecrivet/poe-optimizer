#!/usr/bin/env python3
"""
Test if manual tree loading detects passive tree modifications.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

from src.pob.codec import decode_pob_code
from src.pob.modifier import modify_passive_tree_nodes, get_passive_tree_summary

def evaluate_with_manual_tree(build_xml: str) -> dict:
    """Evaluate build using manual tree loading evaluator."""
    pob_src_path = Path("PathOfBuilding/src").resolve()
    evaluator_script = Path("src/pob/evaluator_manual_tree.lua").resolve()

    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.xml',
        delete=False,
        encoding='utf-8'
    ) as temp_file:
        temp_file.write(build_xml)
        temp_path = temp_file.name

    try:
        result = subprocess.run(
            ["luajit", str(evaluator_script), temp_path],
            cwd=str(pob_src_path),
            capture_output=True,
            text=True,
            timeout=60
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
        try:
            os.unlink(temp_path)
        except:
            pass

def main():
    print("=" * 70)
    print("Testing Manual Tree Loading with Modifications")
    print("=" * 70)

    # Load build1 (no Timeless Jewels)
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    original_xml = decode_pob_code(code)

    # Get tree info
    tree = get_passive_tree_summary(original_xml)
    print(f"\n1. Original build:")
    print(f"   Total nodes: {tree['total_nodes']}")
    print(f"   Class: {tree['class_name']}")
    print(f"   Ascendancy: {tree['ascendancy_name']}")

    # Evaluate original
    print(f"\n2. Evaluating original build...")
    original_result = evaluate_with_manual_tree(original_xml)

    if not original_result or not original_result.get('success'):
        print(f"   ❌ Failed to evaluate original build")
        return

    orig_stats = original_result['stats']
    print(f"   ✓ CombinedDPS: {orig_stats['combinedDPS']:,.0f}")
    print(f"   ✓ Life: {orig_stats['life']:,.0f}")
    print(f"   ✓ Total EHP: {orig_stats['totalEHP']:,.2f}")

    # Remove 5 nodes
    allocated_nodes = list(tree['allocated_nodes'])
    nodes_to_remove = allocated_nodes[:5]
    print(f"\n3. Removing 5 nodes: {nodes_to_remove}")

    modified_xml = modify_passive_tree_nodes(
        original_xml,
        nodes_to_remove=nodes_to_remove
    )

    # Verify XML changed
    modified_tree = get_passive_tree_summary(modified_xml)
    print(f"   Modified total nodes: {modified_tree['total_nodes']}")
    print(f"   Change: {modified_tree['total_nodes'] - tree['total_nodes']} nodes")

    # Evaluate modified
    print(f"\n4. Evaluating modified build...")
    modified_result = evaluate_with_manual_tree(modified_xml)

    if not modified_result or not modified_result.get('success'):
        print(f"   ❌ Failed to evaluate modified build")
        return

    mod_stats = modified_result['stats']
    print(f"   ✓ CombinedDPS: {mod_stats['combinedDPS']:,.0f}")
    print(f"   ✓ Life: {mod_stats['life']:,.0f}")
    print(f"   ✓ Total EHP: {mod_stats['totalEHP']:,.2f}")

    # Calculate changes
    print(f"\n5. Changes:")
    print("=" * 70)

    dps_change = mod_stats['combinedDPS'] - orig_stats['combinedDPS']
    dps_change_pct = (dps_change / orig_stats['combinedDPS']) * 100 if orig_stats['combinedDPS'] else 0

    life_change = mod_stats['life'] - orig_stats['life']
    life_change_pct = (life_change / orig_stats['life']) * 100 if orig_stats['life'] else 0

    ehp_change = mod_stats['totalEHP'] - orig_stats['totalEHP']
    ehp_change_pct = (ehp_change / orig_stats['totalEHP']) * 100 if orig_stats['totalEHP'] else 0

    print(f"   DPS: {dps_change:+,.0f} ({dps_change_pct:+.2f}%)")
    print(f"   Life: {life_change:+,.0f} ({life_change_pct:+.2f}%)")
    print(f"   EHP: {ehp_change:+,.2f} ({ehp_change_pct:+.2f}%)")

    print(f"\n6. Validation:")
    print("=" * 70)

    if dps_change != 0:
        print(f"   ✓ DPS changed (not zero)")
    else:
        print(f"   ❌ DPS did not change (still zero)")

    if life_change != 0:
        print(f"   ✓ Life changed (not zero)")
    else:
        print(f"   ❌ Life did not change (still zero)")

    if dps_change < 0 or life_change < 0:
        print(f"   ✓ Stats decreased (expected when removing nodes)")
    else:
        print(f"   ⚠️  Stats did not decrease")

    print(f"\n" + "=" * 70)
    print("CONCLUSION:")
    print("=" * 70)

    if dps_change != 0 or life_change != 0:
        print("🎉 SUCCESS! Tree modifications ARE detected!")
        print("   The manual tree loading workaround WORKS!")
        print("   Relative calculator approach is VIABLE!")
    else:
        print("❌ FAILURE: Tree modifications NOT detected")
        print("   Stats are still the same after removing nodes")

    print("=" * 70)

if __name__ == "__main__":
    main()

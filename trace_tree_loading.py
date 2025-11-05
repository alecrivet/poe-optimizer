#!/usr/bin/env python3
"""
Trace tree loading process in HeadlessWrapper.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

from src.pob.codec import decode_pob_code

def trace_with_debug(build_xml: str) -> dict:
    """
    Run advanced debug tracer.
    """
    pob_src_path = Path("PathOfBuilding/src").resolve()
    tracer_script = Path("src/pob/evaluator_trace_tree.lua").resolve()

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
        # Run the tracer
        result = subprocess.run(
            ["luajit", str(tracer_script), temp_path],
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
    print("Tracing HeadlessWrapper Tree Loading Process")
    print("=" * 70)

    # Load build2
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    original_xml = decode_pob_code(code)

    # Trace tree loading
    print("\n🔍 Analyzing HeadlessWrapper tree loading...\n")
    result = trace_with_debug(original_xml)

    if not result:
        print("❌ Trace failed")
        return

    # Display results
    xml_info = result.get('xmlInfo', {})
    build_info = result.get('buildInfo', {})
    stats = result.get('stats', {})

    print("1. XML Analysis:")
    print(f"   Sections in XML: {xml_info.get('sectionsFound', 'N/A')}")
    print(f"   Nodes in XML (from Spec): {xml_info.get('nodesInXML', 0)}")

    print("\n2. Build Object State:")
    print(f"   build exists: {build_info.get('buildExists', False)}")
    print(f"   build.tree exists: {build_info.get('hasTree', False)}")
    print(f"   build.spec exists: {build_info.get('hasSpec', False)}")
    print(f"   build.treeTab exists: {build_info.get('hasTreeTab', False)}")
    print(f"   build.calcsTab exists: {build_info.get('hasCalcsTab', False)}")
    print(f"   build.xmlSectionList exists: {build_info.get('hasXmlSectionList', False)}")

    print("\n3. XML Section List:")
    if 'xmlSectionCount' in build_info:
        print(f"   Count: {build_info['xmlSectionCount']}")
        if 'xmlSections' in build_info:
            print(f"   Sections: {build_info['xmlSections']}")
    else:
        print("   ❌ No xmlSectionList found")

    print("\n4. Tree Data Structures:")
    print(f"   tree.allocNodes count: {build_info.get('treeAllocNodesCount', 0)}")
    if build_info.get('treeAllocNodesSample'):
        print(f"   tree.allocNodes sample: {build_info['treeAllocNodesSample']}")

    print(f"\n   spec.allocNodes count: {build_info.get('specAllocNodesCount', 0)}")
    if build_info.get('specAllocNodesSample'):
        print(f"   spec.allocNodes sample: {build_info['specAllocNodesSample']}")

    if 'specNodesCount' in build_info:
        print(f"\n   spec.nodes count: {build_info['specNodesCount']}")
        if build_info.get('specNodesSample'):
            print(f"   spec.nodes sample: {build_info['specNodesSample']}")

    print("\n5. TreeTab State:")
    if 'specListCount' in build_info:
        print(f"   treeTab.specList count: {build_info['specListCount']}")
        if build_info.get('spec1Exists'):
            print(f"   specList[1] exists: True")
            print(f"   specList[1].allocNodes exists: {build_info.get('spec1HasAllocNodes', False)}")
            if 'spec1AllocNodesCount' in build_info:
                print(f"   specList[1].allocNodes count: {build_info['spec1AllocNodesCount']}")

    if build_info.get('hasTreeTabSpec'):
        print(f"   treeTab.spec exists: True")
        if 'treeTabSpecNodes' in build_info:
            print(f"   treeTab.spec.nodes count: {build_info['treeTabSpecNodes']}")
    else:
        print(f"   treeTab.spec exists: {build_info.get('hasTreeTabSpec', False)}")

    print("\n6. Calculation Results:")
    print(f"   CombinedDPS: {stats.get('combinedDPS', 0):,.0f}")
    print(f"   Life: {stats.get('life', 0):,.0f}")

    print("\n" + "=" * 70)
    print("Analysis:")
    print("=" * 70)

    xml_nodes = xml_info.get('nodesInXML', 0)
    tree_nodes = build_info.get('treeAllocNodesCount', 0)
    spec_alloc_nodes = build_info.get('specAllocNodesCount', 0)
    spec_nodes = build_info.get('specNodesCount', 0)

    if xml_nodes > 0:
        print(f"✓ XML has {xml_nodes} nodes in Spec")
    else:
        print(f"❌ No nodes found in XML Spec")

    if tree_nodes == 0:
        print(f"❌ tree.allocNodes is empty (should have {xml_nodes} nodes)")
    else:
        print(f"✓ tree.allocNodes has {tree_nodes} nodes")

    if spec_alloc_nodes == 0:
        print(f"❌ spec.allocNodes is empty (should have {xml_nodes} nodes)")
    elif spec_alloc_nodes == 1:
        print(f"⚠️  spec.allocNodes has only 1 node (likely just starting class)")
    else:
        print(f"✓ spec.allocNodes has {spec_alloc_nodes} nodes")

    if spec_nodes == 0:
        print(f"⚠️  spec.nodes is empty")
    else:
        print(f"✓ spec.nodes has {spec_nodes} nodes")

    if 'xmlSections' in build_info:
        sections_str = build_info['xmlSections']
        if 'Tree' in sections_str or 'Spec' in sections_str:
            print(f"✓ Tree/Spec section found in xmlSectionList")
        else:
            print(f"❌ No Tree/Spec section in xmlSectionList")
            print(f"   Sections found: {sections_str}")

    print("\n" + "=" * 70)
    print("Conclusion:")
    print("=" * 70)

    if tree_nodes == 0 and spec_alloc_nodes <= 1:
        print("🔴 PROBLEM CONFIRMED: Tree is not being loaded from XML")
        print("\nPossible causes:")
        print("1. Tree section not in xmlSectionList")
        print("2. treeTab:Load() not being called")
        print("3. treeTab:Load() failing silently")
        print("4. Tree data structures not initialized properly")
        print("\nNext steps:")
        print("- Check if Tree section is being parsed from XML")
        print("- Add logging to treeTab:Load() to see if it's called")
        print("- Check for errors during tree loading")
    elif spec_alloc_nodes > 1:
        print("🟢 SUCCESS: Tree data is being loaded!")
        print(f"\nspec.allocNodes has {spec_alloc_nodes} nodes")
        print("The issue might be that calculations aren't using spec data")
    else:
        print("🟡 PARTIAL: Some tree structures exist but not fully populated")

    print("=" * 70)

if __name__ == "__main__":
    main()

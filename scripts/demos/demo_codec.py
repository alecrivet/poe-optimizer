#!/usr/bin/env python3
"""
Demo script showing PoB codec (encoder/decoder) working.
"""

from src.pob.codec import encode_pob_code, decode_pob_code, is_valid_pob_code
from src.pob.caller import PoBCalculator

# Minimal build XML for demonstration
DEMO_BUILD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" targetVersion="3_0" className="Marauder" ascendClassName="Juggernaut">
        <PlayerStat stat="Strength" value="200"/>
        <PlayerStat stat="Dexterity" value="100"/>
        <PlayerStat stat="Intelligence" value="50"/>
    </Build>
    <Tree activeSpec="1">
        <Spec title="Demo Build" treeVersion="3_25" classId="1" ascendClassId="1"
              nodes="0,1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90,100"/>
    </Tree>
    <Items activeItemSet="1">
        <ItemSet id="1" title="Gear"/>
    </Items>
    <Skills activeSkillSet="1">
        <SkillSet id="1"/>
    </Skills>
    <Config/>
</PathOfBuilding>"""


def main():
    print("=" * 70)
    print("Path of Building Codec Demo")
    print("=" * 70)
    print()

    # Step 1: Encode XML to PoB code
    print("Step 1: Encoding XML to PoB import code...")
    print("-" * 70)
    pob_code = encode_pob_code(DEMO_BUILD_XML)
    print(f"✓ Encoded successfully!")
    print(f"  Code length: {len(pob_code)} characters")
    print(f"  Code preview: {pob_code[:60]}...")
    print()

    # Step 2: Validate the code
    print("Step 2: Validating PoB code...")
    print("-" * 70)
    is_valid = is_valid_pob_code(pob_code)
    print(f"✓ Code is valid: {is_valid}")
    print()

    # Step 3: Decode back to XML
    print("Step 3: Decoding PoB code back to XML...")
    print("-" * 70)
    decoded_xml = decode_pob_code(pob_code)
    print(f"✓ Decoded successfully!")
    print(f"  XML length: {len(decoded_xml)} characters")
    print(f"  XML preview: {decoded_xml[:100]}...")
    print()

    # Step 4: Verify round-trip
    print("Step 4: Verifying round-trip encoding...")
    print("-" * 70)
    matches = decoded_xml.strip() == DEMO_BUILD_XML.strip()
    print(f"✓ Round-trip successful: {matches}")
    print()

    # Step 5: Evaluate the decoded build
    print("Step 5: Evaluating decoded build with PoBCalculator...")
    print("-" * 70)
    calc = PoBCalculator()
    stats = calc.evaluate_build(decoded_xml)
    print(f"✓ Build evaluated successfully!")
    print(f"  Life: {stats['life']:.0f}")
    print(f"  Total DPS: {stats['totalDPS']:.2f}")
    print(f"  Fire Resist: {stats['fireRes']:.0f}%")
    print()

    # Step 6: URL-encoded version
    print("Step 6: Creating URL-safe version...")
    print("-" * 70)
    url_safe_code = encode_pob_code(DEMO_BUILD_XML, url_encode=True)
    print(f"✓ URL-encoded successfully!")
    print(f"  Code length: {len(url_safe_code)} characters")
    print(f"  Code preview: {url_safe_code[:60]}...")
    # Verify it still decodes
    decoded_from_url = decode_pob_code(url_safe_code)
    print(f"✓ URL-encoded code decodes correctly: {decoded_from_url.strip() == DEMO_BUILD_XML.strip()}")
    print()

    print("=" * 70)
    print("✓ PoB Codec Working Successfully!")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("  1. Get real PoB codes from poe.ninja")
    print("  2. Test decoding with real builds")
    print("  3. Save example XMLs to examples/ directory")
    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test that verifies the Lua calculation engine is working properly.
This forces use of Lua evaluator instead of XML parser.
"""

from src.pob.codec import decode_pob_code
from src.pob.caller import PoBCalculator

def main():
    print("=" * 70)
    print("Testing Lua Calculation Engine")
    print("=" * 70)

    # Load build2 code
    with open('examples/build2', 'r') as f:
        code = f.read().strip()

    # Decode to XML
    xml = decode_pob_code(code)

    # Test with XML parser (default)
    print("\n1. Using XML Parser (default):")
    calc = PoBCalculator()
    stats_xml = calc.evaluate_build(xml, use_xml_stats=True)
    print(f"   Combined DPS: {stats_xml.get('combinedDPS', 0):,.2f}")
    print(f"   Life: {stats_xml.get('life', 0):,.0f}")
    print(f"   Total EHP: {stats_xml.get('totalEHP', 0):,.0f}")

    # Test with Lua calculator (forced)
    print("\n2. Using Lua Calculator (forced):")
    stats_lua = calc.evaluate_build(xml, use_xml_stats=False)
    print(f"   Combined DPS: {stats_lua.get('combinedDPS', 0):,.2f}")
    print(f"   Life: {stats_lua.get('life', 0):,.0f}")
    print(f"   Total EHP: {stats_lua.get('totalEHP', 0):,.0f}")

    # Compare results
    print("\n3. Comparison:")
    dps_diff = abs(stats_xml.get('combinedDPS', 0) - stats_lua.get('combinedDPS', 0))
    life_diff = abs(stats_xml.get('life', 0) - stats_lua.get('life', 0))

    print(f"   DPS difference: {dps_diff:,.2f}")
    print(f"   Life difference: {life_diff:,.0f}")

    # Check if they're close (within 1% for DPS, exact for Life)
    dps_close = dps_diff < (stats_xml.get('combinedDPS', 0) * 0.01)
    life_close = life_diff < 1

    print("\n4. Results:")
    if dps_close and life_close:
        print("   ✓ Lua calculator is working correctly!")
        print("   ✓ Results match XML pre-calculated stats")
    else:
        print("   ⚠ Results differ between XML and Lua calculation")
        if not dps_close:
            print(f"     - DPS differs by {dps_diff:,.2f} ({dps_diff / stats_xml.get('combinedDPS', 1) * 100:.1f}%)")
        if not life_close:
            print(f"     - Life differs by {life_diff:,.0f}")

    print("=" * 70)

if __name__ == "__main__":
    main()

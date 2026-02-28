#!/usr/bin/env python3
"""
Test script for decoding and evaluating real PoB codes
"""

from src.pob.codec import decode_pob_code, encode_pob_code, is_valid_pob_code
from src.pob.caller import PoBCalculator
import os

def run_build_test(build_file, build_name):
    """Test decoding and evaluating a real PoB build"""
    print(f"\n{'=' * 70}")
    print(f"Testing {build_name}")
    print(f"{'=' * 70}")

    # Read the PoB code from file
    with open(build_file, 'r') as f:
        pob_code = f.read().strip()

    print(f"PoB code length: {len(pob_code)} characters")
    print(f"Code starts with: {pob_code[:20]}...")
    print()

    # Validate the code
    print("Step 1: Validating PoB code...")
    is_valid = is_valid_pob_code(pob_code)
    print(f"✓ Code is valid: {is_valid}")
    print()

    if not is_valid:
        print("✗ Code validation failed!")
        return False

    # Decode to XML
    print("Step 2: Decoding to XML...")
    try:
        xml = decode_pob_code(pob_code)
        print(f"✓ Decoded successfully!")
        print(f"  XML length: {len(xml)} characters")
        print(f"  XML starts with: {xml[:100].strip()}...")
        print()
    except Exception as e:
        print(f"✗ Decoding failed: {e}")
        return False

    # Test round-trip encoding
    print("Step 3: Testing round-trip encoding...")
    try:
        re_encoded = encode_pob_code(xml)
        re_decoded = decode_pob_code(re_encoded)
        matches = xml.strip() == re_decoded.strip()
        print(f"✓ Round-trip successful: {matches}")
        print()
    except Exception as e:
        print(f"✗ Round-trip failed: {e}")
        return False

    # Evaluate with PoBCalculator
    print("Step 4: Evaluating with PoBCalculator...")
    try:
        calc = PoBCalculator()
        stats = calc.evaluate_build(xml)
        print(f"✓ Build evaluated successfully!")
        print()
        print(f"  Build Stats:")
        print(f"    Life:           {stats['life']:>10.0f}")
        print(f"    Energy Shield:  {stats['energyShield']:>10.0f}")
        print(f"    Total EHP:      {stats['totalEHP']:>10.0f}")
        print()
        print(f"  DPS:")
        print(f"    Combined DPS:   {stats['combinedDPS']:>10.2f}  ← PRIMARY METRIC")
        print(f"    Total DPS:      {stats['totalDPS']:>10.2f}")
        print(f"    With Impale:    {stats.get('withImpaleDPS', 0):>10.2f}")
        print()
        print(f"  Resistances:")
        print(f"    Fire:           {stats['fireRes']:>9.0f}%")
        print(f"    Cold:           {stats['coldRes']:>9.0f}%")
        print(f"    Lightning:      {stats['lightningRes']:>9.0f}%")
        print(f"    Chaos:          {stats['chaosRes']:>9.0f}%")
        print()
    except Exception as e:
        print(f"✗ Evaluation failed: {e}")
        return False

    # Save decoded XML to examples directory
    xml_file = build_file.replace('.txt', '.xml').replace('build', 'decoded_build')
    if not os.path.exists(xml_file):
        xml_file = build_file + '.xml'

    print(f"Step 5: Saving decoded XML...")
    try:
        with open(xml_file, 'w') as f:
            f.write(xml)
        print(f"✓ Saved to: {xml_file}")
        print()
    except Exception as e:
        print(f"✗ Failed to save XML: {e}")

    return True


def main():
    print("=" * 70)
    print("Real PoB Build Testing")
    print("=" * 70)

    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    examples_dir = os.path.join(script_dir, "examples")
    builds = [
        (os.path.join(examples_dir, "build1"), "Build 1"),
        (os.path.join(examples_dir, "build2"), "Build 2"),
    ]

    results = []
    for build_file, build_name in builds:
        success = run_build_test(build_file, build_name)
        results.append((build_name, success))

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    for build_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {build_name}: {status}")
    print()

    all_passed = all(success for _, success in results)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

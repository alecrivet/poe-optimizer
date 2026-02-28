"""
Test: Does PoB's headless evaluator detect support gem changes?

This script answers the critical question: when we modify support gems in the
build XML, does the Lua evaluator (via HeadlessWrapper + BuildOutput) produce
different DPS numbers?

If YES → the gem optimizer's ratio-based approach will work.
If NO  → gem optimization is blocked until HeadlessWrapper skill loading is fixed.

Tests:
  1. Lower a support gem's level (Trap and Mine Damage L19 → L1)
  2. Disable a support gem entirely (enabled="false")
  3. Swap a support gem for a useless one (Trap and Mine Damage → Cast on Death)

Build: examples/build1 (Icicle Mine of Fanning, Shadow Assassin)
  - Body Armour (socket group 3):
    - Icicle Mine of Fanning (active)
    - Inspiration
    - Trap and Mine Damage (L19, Q20)  ← target
    - Minefield
    - Charged Mines
    - Power Charge On Critical
"""

import sys
import os
import xml.etree.ElementTree as ET

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pob.codec import decode_pob_code
from src.pob.caller import PoBCalculator
from src.pob.xml_parser import get_build_summary


def load_build1_xml() -> str:
    """Load and decode build1."""
    build_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "build1"
    )
    with open(build_path, "r") as f:
        code = f.read().strip()
    return decode_pob_code(code)


def get_body_armour_skill_elem(root: ET.Element) -> ET.Element:
    """Find the Body Armour socket group (slot='Body Armour')."""
    skills_elem = root.find("Skills")
    active_set_id = skills_elem.get("activeSkillSet", "1")
    skill_set = skills_elem.find(f".//SkillSet[@id='{active_set_id}']")
    for skill_elem in skill_set.findall("Skill"):
        if skill_elem.get("slot") == "Body Armour":
            return skill_elem
    raise RuntimeError("No Body Armour socket group found")


def find_gem_by_name(skill_elem: ET.Element, name: str) -> ET.Element:
    """Find a Gem element by nameSpec."""
    for gem in skill_elem.findall("Gem"):
        if gem.get("nameSpec") == name:
            return gem
    raise RuntimeError(f"Gem '{name}' not found")


def evaluate_lua_dps(calc: PoBCalculator, xml: str) -> dict:
    """Run Lua evaluator and return stats dict."""
    return calc.evaluate_build(xml, use_xml_stats=False)


def test_level_change(original_xml: str, calc: PoBCalculator) -> dict:
    """Test 1: Lower Trap and Mine Damage from L19 to L1."""
    root = ET.fromstring(original_xml)
    skill = get_body_armour_skill_elem(root)
    gem = find_gem_by_name(skill, "Trap and Mine Damage")

    old_level = gem.get("level")
    gem.set("level", "1")

    modified_xml = ET.tostring(root, encoding="unicode")
    stats = evaluate_lua_dps(calc, modified_xml)

    return {
        "test": "Level change (Trap and Mine Damage L19 → L1)",
        "modification": f"level {old_level} → 1",
        "stats": stats,
    }


def test_disable_gem(original_xml: str, calc: PoBCalculator) -> dict:
    """Test 2: Disable Trap and Mine Damage entirely."""
    root = ET.fromstring(original_xml)
    skill = get_body_armour_skill_elem(root)
    gem = find_gem_by_name(skill, "Trap and Mine Damage")

    gem.set("enabled", "false")

    modified_xml = ET.tostring(root, encoding="unicode")
    stats = evaluate_lua_dps(calc, modified_xml)

    return {
        "test": "Disable gem (Trap and Mine Damage enabled=false)",
        "modification": "enabled → false",
        "stats": stats,
    }


def test_swap_gem(original_xml: str, calc: PoBCalculator) -> dict:
    """Test 3: Swap Trap and Mine Damage for Cast on Death."""
    root = ET.fromstring(original_xml)
    skill = get_body_armour_skill_elem(root)
    gem = find_gem_by_name(skill, "Trap and Mine Damage")

    # Replace with Cast on Death attributes (copied from Helmet group in build1)
    gem.set("nameSpec", "Cast on Death")
    gem.set("gemId", "Metadata/Items/Gems/SupportGemCastOnDeath")
    gem.set("variantId", "SupportCastOnDeath")
    gem.set("skillId", "SupportCastOnDeath")
    gem.set("level", "1")
    gem.set("quality", "0")

    modified_xml = ET.tostring(root, encoding="unicode")
    stats = evaluate_lua_dps(calc, modified_xml)

    return {
        "test": "Swap gem (Trap and Mine Damage → Cast on Death)",
        "modification": "full gem swap",
        "stats": stats,
    }


def test_remove_gem(original_xml: str, calc: PoBCalculator) -> dict:
    """Test 4: Remove Trap and Mine Damage from the socket group entirely."""
    root = ET.fromstring(original_xml)
    skill = get_body_armour_skill_elem(root)
    gem = find_gem_by_name(skill, "Trap and Mine Damage")

    skill.remove(gem)

    modified_xml = ET.tostring(root, encoding="unicode")
    stats = evaluate_lua_dps(calc, modified_xml)

    return {
        "test": "Remove gem (Trap and Mine Damage removed from group)",
        "modification": "gem element removed",
        "stats": stats,
    }


def main():
    print("=" * 70)
    print("Support Gem Sensitivity Test")
    print("Does PoB's headless evaluator detect gem changes?")
    print("=" * 70)
    print()

    # Load build
    print("Loading build1 (Icicle Mine of Fanning)...")
    original_xml = load_build1_xml()

    # Get pre-calculated baseline from XML
    xml_summary = get_build_summary(original_xml)
    xml_dps = xml_summary.get("combinedDPS", 0)
    print(f"  XML pre-calculated DPS: {xml_dps:,.0f}")
    print()

    # Initialize calculator
    print("Initializing PoBCalculator...")
    try:
        calc = PoBCalculator()
    except Exception as e:
        print(f"  FAILED: {e}")
        print()
        print("Cannot run tests without a working PoBCalculator.")
        print("Make sure PathOfBuilding submodule is initialized and luajit is installed.")
        sys.exit(1)

    # Get Lua baseline
    print("Evaluating baseline with Lua evaluator...")
    try:
        baseline_stats = evaluate_lua_dps(calc, original_xml)
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    baseline_dps = baseline_stats.get("combinedDPS", 0)
    baseline_life = baseline_stats.get("life", 0)
    print(f"  Lua baseline DPS:  {baseline_dps:,.2f}")
    print(f"  Lua baseline Life: {baseline_life:,.2f}")
    print(f"  DPS accuracy vs XML: {baseline_dps / xml_dps * 100:.1f}%" if xml_dps else "  (no XML DPS)")
    print()

    # Run tests
    tests = [test_level_change, test_disable_gem, test_swap_gem, test_remove_gem]
    results = []

    for test_fn in tests:
        print(f"Running: {test_fn.__doc__.strip()}")
        try:
            result = test_fn(original_xml, calc)
            mod_dps = result["stats"].get("combinedDPS", 0)

            if baseline_dps > 0:
                pct_change = (mod_dps / baseline_dps - 1) * 100
            else:
                pct_change = 0

            result["mod_dps"] = mod_dps
            result["pct_change"] = pct_change
            results.append(result)

            changed = "CHANGED" if abs(pct_change) > 0.01 else "NO CHANGE"
            print(f"  Modified DPS: {mod_dps:,.2f}  ({pct_change:+.2f}%)  [{changed}]")
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"test": test_fn.__doc__.strip(), "error": str(e)})
        print()

    # Summary
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"  XML pre-calculated DPS:    {xml_dps:>15,.0f}")
    print(f"  Lua baseline DPS:          {baseline_dps:>15,.2f}")
    print()

    any_change = False
    for r in results:
        if "error" in r:
            print(f"  {r['test']}: ERROR ({r['error'][:50]})")
        else:
            changed = abs(r["pct_change"]) > 0.01
            any_change = any_change or changed
            marker = "YES" if changed else "NO"
            print(f"  {r['test']}")
            print(f"    DPS: {r['mod_dps']:>15,.2f}  ({r['pct_change']:+.2f}%)  Detected: {marker}")
            print()

    print("-" * 70)
    if any_change:
        print("VERDICT: Lua evaluator DOES detect support gem changes.")
        print("         The gem optimizer's ratio-based approach should work.")
    else:
        print("VERDICT: Lua evaluator does NOT detect support gem changes.")
        print("         HeadlessWrapper is not loading skills into the calc engine.")
        print("         Gem optimization is BLOCKED until this is resolved.")
    print("-" * 70)


if __name__ == "__main__":
    main()

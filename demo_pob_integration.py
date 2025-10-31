#!/usr/bin/env python3
"""
Demo script showing PoB integration working end-to-end.
"""

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
    print("=" * 60)
    print("Path of Building Integration Demo")
    print("=" * 60)
    print()

    # Initialize calculator
    print("Initializing PoBCalculator...")
    calc = PoBCalculator()
    print(f"✓ {calc}")
    print()

    # Evaluate build
    print("Evaluating demo build...")
    print("This will:")
    print("  1. Write build XML to temporary file")
    print("  2. Run PoB's calculation engine via Lua")
    print("  3. Parse and return build statistics")
    print()

    stats = calc.evaluate_build(DEMO_BUILD_XML)

    print("✓ Build evaluated successfully!")
    print()
    print("=" * 60)
    print("Build Statistics")
    print("=" * 60)
    print()

    # Display results
    print(f"{'Offensive Stats':<30} {'Value':>15}")
    print("-" * 45)
    print(f"  {'Total DPS':<28} {stats['totalDPS']:>15.2f}")
    print(f"  {'Full DPS (all skills)':<28} {stats['fullDPS']:>15.2f}")
    print()

    print(f"{'Defensive Stats':<30} {'Value':>15}")
    print("-" * 45)
    print(f"  {'Life':<28} {stats['life']:>15.0f}")
    print(f"  {'Energy Shield':<28} {stats['energyShield']:>15.0f}")
    print(f"  {'Total EHP':<28} {stats['totalEHP']:>15.2f}")
    print()

    print(f"{'Resistances':<30} {'Value':>15}")
    print("-" * 45)
    print(f"  {'Fire Resist':<28} {stats['fireRes']:>14.0f}%")
    print(f"  {'Cold Resist':<28} {stats['coldRes']:>14.0f}%")
    print(f"  {'Lightning Resist':<28} {stats['lightningRes']:>14.0f}%")
    print(f"  {'Chaos Resist':<28} {stats['chaosRes']:>14.0f}%")
    print()

    print(f"{'Attributes':<30} {'Value':>15}")
    print("-" * 45)
    print(f"  {'Strength':<28} {stats['strength']:>15.0f}")
    print(f"  {'Dexterity':<28} {stats['dexterity']:>15.0f}")
    print(f"  {'Intelligence':<28} {stats['intelligence']:>15.0f}")
    print()

    print("=" * 60)
    print("✓ PoB Integration Working Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()

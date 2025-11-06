#!/usr/bin/env python3
"""
Example 4: Advanced Features

Shows how to use all advanced features:
1. Extended objectives (Mana, ES, Block, Clear Speed)
2. Constraints (point budget, attributes, jewel sockets)
3. Visualization of all results

Use case: Specialized builds with specific requirements
"""

import sys
sys.path.insert(0, '../..')

from src.pob.codec import decode_pob_code, encode_pob_code
from src.pob.modifier import get_passive_tree_summary
from src.optimizer.tree_optimizer import GreedyTreeOptimizer
from src.optimizer.extended_objectives import evaluate_extended_objectives, OBJECTIVE_DESCRIPTIONS
from src.optimizer.constraints import create_standard_constraints
from src.pob.relative_calculator import RelativeCalculator

def main():
    print("\n" + "="*80)
    print("EXAMPLE 4: Advanced Features - Extended Objectives & Constraints")
    print("="*80)

    # Step 1: Load build
    print("\n📖 Step 1: Loading build...")
    with open('../../examples/build1', 'r') as f:
        pob_code = f.read().strip()

    build_xml = decode_pob_code(pob_code)
    summary = get_passive_tree_summary(build_xml)
    print(f"   ✅ Build loaded")
    print(f"      Current points: {len(summary['allocated_nodes'])}")
    print(f"      Class: {summary['class_name']}")
    print(f"      Ascendancy: {summary['ascendancy_name']}")

    # Step 2: Define constraints
    print("\n🔒 Step 2: Setting up constraints...")

    constraints = create_standard_constraints(
        level=95,  # Level 95 character = max 116 points
        gem_requirements=[
            {'str': 155, 'dex': 0, 'int': 0},   # Level 20 Melee gem
            {'str': 0, 'dex': 155, 'int': 0},   # Level 20 Bow gem
        ],
        min_jewel_sockets=2,  # Need at least 2 jewel sockets
    )

    print(f"   ✅ Constraints configured:")
    print(f"      Max points: 116 (level 95)")
    print(f"      Min STR: 155 (for gems)")
    print(f"      Min DEX: 155 (for gems)")
    print(f"      Min jewel sockets: 2")

    # Validate current build
    if constraints.validate(build_xml):
        print(f"   ✅ Current build satisfies all constraints")
    else:
        violations = constraints.get_violations(build_xml)
        print(f"   ⚠️  Current build violates constraints:")
        for violation in violations:
            print(f"      - {violation}")

    # Step 3: Run optimization
    print("\n🚀 Step 3: Optimizing with constraints...")

    optimizer = GreedyTreeOptimizer(
        max_iterations=50,
        optimize_masteries=True,
    )

    result = optimizer.optimize(
        build_xml,
        objective='dps',
        allow_point_increase=True,  # Can add points (within budget)
    )

    print(f"   ✅ Optimization complete")

    # Validate optimized build
    if constraints.validate(result.optimized_xml):
        print(f"   ✅ Optimized build satisfies all constraints")
    else:
        violations = constraints.get_violations(result.optimized_xml)
        print(f"   ⚠️  Optimized build violates constraints:")
        for violation in violations:
            print(f"      - {violation}")

    # Step 4: Evaluate extended objectives
    print("\n📊 Step 4: Evaluating ALL objectives...")

    calculator = RelativeCalculator()
    base_eval = calculator.evaluate_modification(build_xml, result.optimized_xml)

    extended_score = evaluate_extended_objectives(
        build_xml,
        result.optimized_xml,
        base_eval
    )

    print("\n   " + "="*76)
    print("   COMPREHENSIVE OBJECTIVE ANALYSIS")
    print("   " + "="*76)

    # Core objectives
    print(f"\n   🎯 Core Objectives:")
    print(f"      DPS:  {extended_score.dps_percent:+7.2f}%  {OBJECTIVE_DESCRIPTIONS['dps']}")
    print(f"      Life: {extended_score.life_percent:+7.2f}%  {OBJECTIVE_DESCRIPTIONS['life']}")
    print(f"      EHP:  {extended_score.ehp_percent:+7.2f}%  {OBJECTIVE_DESCRIPTIONS['ehp']}")

    # Extended objectives
    print(f"\n   🔧 Extended Objectives:")

    if extended_score.mana_percent is not None:
        print(f"      Mana: {extended_score.mana_percent:+7.2f}%  {OBJECTIVE_DESCRIPTIONS['mana']}")
    else:
        print(f"      Mana: N/A      (not calculated)")

    if extended_score.es_percent is not None:
        print(f"      ES:   {extended_score.es_percent:+7.2f}%  {OBJECTIVE_DESCRIPTIONS['es']}")
    else:
        print(f"      ES:   N/A      (not calculated)")

    if extended_score.block_percent is not None:
        print(f"      Block:{extended_score.block_percent:+7.2f}%  {OBJECTIVE_DESCRIPTIONS['block']}")
    else:
        print(f"      Block: N/A      (not calculated)")

    if extended_score.clear_speed_percent is not None:
        print(f"      Speed:{extended_score.clear_speed_percent:+7.2f}%  {OBJECTIVE_DESCRIPTIONS['clear_speed']}")
    else:
        print(f"      Speed: N/A      (not calculated)")

    # Step 5: Analysis
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)

    # Find best and worst objectives
    objectives = extended_score.to_dict()
    valid_objectives = {k: v for k, v in objectives.items() if v is not None}

    if valid_objectives:
        best_obj = max(valid_objectives.items(), key=lambda x: x[1])
        worst_obj = min(valid_objectives.items(), key=lambda x: x[1])

        print(f"\n   📈 Best improvement: {best_obj[0].upper()} ({best_obj[1]:+.2f}%)")
        print(f"      → {OBJECTIVE_DESCRIPTIONS[best_obj[0]]}")

        print(f"\n   📉 Worst improvement: {worst_obj[0].upper()} ({worst_obj[1]:+.2f}%)")
        print(f"      → {OBJECTIVE_DESCRIPTIONS[worst_obj[0]]}")

        # Trade-off analysis
        if best_obj[1] > 5.0 and worst_obj[1] < -2.0:
            print(f"\n   ⚠️  Trade-off Alert:")
            print(f"      Gained {best_obj[1]:+.2f}% {best_obj[0].upper()}")
            print(f"      Lost {abs(worst_obj[1]):.2f}% {worst_obj[0].upper()}")
            print(f"      → Consider if trade-off is worth it")

    # Step 6: Specialized build recommendations
    print("\n" + "="*80)
    print("SPECIALIZED BUILD RECOMMENDATIONS")
    print("="*80)

    print(f"\n   Based on your improvements, this build is good for:")

    recommendations = []

    if extended_score.dps_percent > 5.0:
        recommendations.append("   ✅ High DPS → Bossing, single target")

    if extended_score.life_percent > 3.0 or extended_score.ehp_percent > 3.0:
        recommendations.append("   ✅ Good survivability → HC viable")

    if extended_score.mana_percent and extended_score.mana_percent > 5.0:
        recommendations.append("   ✅ High mana → MoM builds, mana-stacking")

    if extended_score.es_percent and extended_score.es_percent > 5.0:
        recommendations.append("   ✅ High ES → CI/LL builds, ES-based")

    if extended_score.block_percent and extended_score.block_percent > 3.0:
        recommendations.append("   ✅ Good block → Block builds, Gladiator")

    if extended_score.clear_speed_percent and extended_score.clear_speed_percent > 3.0:
        recommendations.append("   ✅ Fast clear → Mapping, farming")

    if recommendations:
        for rec in recommendations:
            print(rec)
    else:
        print("   → General purpose build (balanced across objectives)")

    # Step 7: Save result
    print(f"\n💾 Step 7: Saving optimized build...")

    optimized_code = encode_pob_code(result.optimized_xml)
    with open('optimized_build_advanced.txt', 'w') as f:
        f.write(optimized_code)

    print(f"   ✅ Saved to: optimized_build_advanced.txt")

    print("\n" + "="*80)
    print("✅ ADVANCED OPTIMIZATION COMPLETE!")
    print("="*80)
    print("\n📂 Output:")
    print("   - optimized_build_advanced.txt (PoB import code)")
    print("\n💡 Key Features Used:")
    print("   ✅ Extended objectives (7 total)")
    print("   ✅ Constraint validation (points, attributes, jewels)")
    print("   ✅ Comprehensive analysis")
    print("   ✅ Specialized recommendations")
    print("\n")

if __name__ == "__main__":
    main()

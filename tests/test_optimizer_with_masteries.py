"""
Test tree optimizer with mastery optimization enabled.

Demonstrates:
1. Optimizer loading mastery database
2. Mastery selections being optimized during tree optimization
3. Comparison of mastery changes vs node changes
"""

import logging
from src.optimizer.tree_optimizer import GreedyTreeOptimizer
from src.pob.codec import decode_pob_code
from src.pob.modifier import get_passive_tree_summary
from src.pob.mastery_optimizer import get_mastery_database

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def test_optimizer_with_masteries():
    """Test optimizer with mastery optimization enabled."""
    print("=" * 70)
    print("Tree Optimizer with Mastery Optimization Test")
    print("=" * 70)

    # Load build
    print("\n📂 Loading build...")
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    build_xml = decode_pob_code(code)
    original_summary = get_passive_tree_summary(build_xml)

    print(f"✓ Build loaded: {original_summary['class_name']} {original_summary['ascendancy_name']}")
    print(f"  {original_summary['total_nodes']} nodes allocated")
    print(f"  {len(original_summary['mastery_effects'])} mastery effects selected")

    # Show current masteries
    if original_summary['mastery_effects']:
        print("\n📊 Current mastery selections:")
        mastery_db = get_mastery_database()
        for node_id, effect_id in list(original_summary['mastery_effects'].items())[:3]:
            mastery = mastery_db.get_mastery(node_id)
            effect = mastery_db.get_effect(effect_id)
            if mastery and effect:
                print(f"  {mastery.name}: {effect.stats[0][:60]}...")

    # Create optimizer WITH mastery optimization
    print("\n🔧 Creating optimizer with mastery optimization...")
    optimizer = GreedyTreeOptimizer(
        max_iterations=10,
        min_improvement=0.1,
        optimize_masteries=True
    )

    # Run optimization
    print("\n🚀 Running optimization (objective: DPS)...")
    print("-" * 70)
    result = optimizer.optimize(
        build_xml,
        objective='dps',
        allow_point_increase=False  # Only reallocate existing points
    )

    # Show results
    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULTS")
    print("=" * 70)

    optimized_summary = get_passive_tree_summary(result.optimized_xml)

    print(f"\n📈 Improvements:")
    print(f"  DPS:  {result.get_improvement('dps'):+.2f}%")
    print(f"  Life: {result.get_improvement('life'):+.2f}%")
    print(f"  EHP:  {result.get_improvement('ehp'):+.2f}%")

    print(f"\n🔄 Changes applied: {result.iterations} modifications")

    # Show modification history
    if result.modifications_applied:
        print("\n📝 Modification history:")
        for mod in result.modifications_applied[:5]:
            print(f"  {mod['iteration']}. {mod['modification']}: "
                  f"{mod['improvement_pct']:+.2f}% improvement")

    # Compare masteries
    print("\n🎯 Mastery changes:")
    original_masteries = original_summary['mastery_effects']
    optimized_masteries = optimized_summary['mastery_effects']

    mastery_changes = 0
    for node_id in set(original_masteries.keys()) | set(optimized_masteries.keys()):
        orig_effect = original_masteries.get(node_id)
        opt_effect = optimized_masteries.get(node_id)

        if orig_effect != opt_effect:
            mastery_changes += 1
            mastery = mastery_db.get_mastery(node_id)

            if mastery:
                print(f"\n  {mastery.name} ({node_id}):")

                if orig_effect:
                    effect = mastery_db.get_effect(orig_effect)
                    if effect:
                        print(f"    Before: {effect.stats[0][:50]}...")
                else:
                    print(f"    Before: (none)")

                if opt_effect:
                    effect = mastery_db.get_effect(opt_effect)
                    if effect:
                        print(f"    After:  {effect.stats[0][:50]}...")
                else:
                    print(f"    After:  (none)")

    if mastery_changes == 0:
        print("  No mastery changes made (current selections are optimal!)")
    else:
        print(f"\n  Total mastery changes: {mastery_changes}")

    print("\n" + "=" * 70)
    print("✅ Test complete!")
    print("=" * 70)


def test_mastery_only_optimization():
    """Test mastery-only optimization (no node changes)."""
    print("\n\n")
    print("=" * 70)
    print("Mastery-Only Optimization Test")
    print("=" * 70)

    # Load build
    print("\n📂 Loading build...")
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    build_xml = decode_pob_code(code)

    # Create optimizer
    print("\n🔧 Creating optimizer...")
    optimizer = GreedyTreeOptimizer(
        max_iterations=1,  # Only 1 iteration for mastery-only
        optimize_masteries=True
    )

    # The first candidate should be "Optimize mastery selections"
    print("\n🚀 Running single iteration...")
    result = optimizer.optimize(
        build_xml,
        objective='dps',
        allow_point_increase=False
    )

    print("\n📊 Results:")
    print(f"  Improvements made: {result.iterations}")
    if result.iterations > 0:
        first_mod = result.modifications_applied[0]
        if "mastery" in first_mod['modification'].lower():
            print(f"  ✓ First modification was mastery optimization!")
            print(f"    Improvement: {first_mod['improvement_pct']:+.2f}%")
        else:
            print(f"  First modification: {first_mod['modification']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Run tests
    test_optimizer_with_masteries()
    test_mastery_only_optimization()

    print("\n✨ All tests complete!")

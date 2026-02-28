"""
Test mastery optimizer functionality.

Tests:
1. Mastery database loading from PoB data
2. Heuristic scoring for different objectives
3. Mastery effect selection
"""

import pytest
from src.pob.mastery_optimizer import (
    load_mastery_database,
    MasteryOptimizer,
    MasteryEffect,
)
from src.pob.modifier import get_passive_tree_summary
from src.pob.codec import decode_pob_code


def test_load_mastery_database():
    """Test loading mastery database from PathOfBuilding."""
    db = load_mastery_database()

    # Should have loaded some masteries
    assert len(db.masteries) > 0, "No masteries loaded from tree data"

    print(f"\nLoaded {len(db.masteries)} mastery nodes")
    print(f"Total effects: {len(db.effect_lookup)}")

    # Show first few masteries
    for i, (node_id, mastery) in enumerate(list(db.masteries.items())[:5]):
        print(f"\n{mastery}")
        for effect in mastery.available_effects[:3]:
            print(f"  - {effect}")


def test_mastery_effect_scoring():
    """Test heuristic scoring of mastery effects."""
    db = load_mastery_database()
    optimizer = MasteryOptimizer(db)

    # Create test effects
    dps_effect = MasteryEffect(
        effect_id=1,
        stats=["20% increased Damage", "10% Penetration"]
    )

    life_effect = MasteryEffect(
        effect_id=2,
        stats=["+50 to maximum Life", "5% Life Regeneration"]
    )

    defense_effect = MasteryEffect(
        effect_id=3,
        stats=["+1% to maximum Resistances", "10% reduced Damage taken"]
    )

    # Test DPS objective
    dps_score = optimizer._score_effect(dps_effect, 'dps')
    life_score_dps = optimizer._score_effect(life_effect, 'dps')
    assert dps_score > life_score_dps, "DPS effect should score higher for DPS objective"

    # Test Life objective
    life_score = optimizer._score_effect(life_effect, 'life')
    dps_score_life = optimizer._score_effect(dps_effect, 'life')
    assert life_score > dps_score_life, "Life effect should score higher for Life objective"

    # Test Defense objective
    defense_score = optimizer._score_effect(defense_effect, 'ehp')
    dps_score_ehp = optimizer._score_effect(dps_effect, 'ehp')
    assert defense_score > dps_score_ehp, "Defense effect should score higher for EHP objective"

    print(f"\nScoring test:")
    print(f"DPS effect for DPS: {dps_score:.2f}")
    print(f"Life effect for Life: {life_score:.2f}")
    print(f"Defense effect for EHP: {defense_score:.2f}")


def test_real_build_mastery_selection():
    """Test mastery selection on a real build."""
    # Load build
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    summary = get_passive_tree_summary(xml)

    allocated_nodes = summary['allocated_nodes']
    current_masteries = summary['mastery_effects']

    print(f"\nBuild has {len(current_masteries)} mastery selections")
    print(f"Mastery nodes: {list(current_masteries.keys())}")

    # Load database and optimizer
    db = load_mastery_database()
    optimizer = MasteryOptimizer(db)

    # Test selecting masteries for DPS
    dps_selections = optimizer.select_best_mastery_effects(
        allocated_nodes=allocated_nodes,
        current_mastery_effects=current_masteries,
        objective='dps'
    )

    print(f"\nDPS-optimized selections: {len(dps_selections)} masteries")

    # Compare with current selections
    for node_id in current_masteries:
        current_effect_id = current_masteries[node_id]
        dps_effect_id = dps_selections.get(node_id)

        current_effect = db.get_effect(current_effect_id)
        dps_effect = db.get_effect(dps_effect_id) if dps_effect_id else None

        print(f"\nMastery {node_id}:")
        if current_effect:
            print(f"  Current: {current_effect.stats[0]}")
        if dps_effect and dps_effect_id != current_effect_id:
            print(f"  DPS Opt: {dps_effect.stats[0]} (different!)")
        elif dps_effect:
            print(f"  DPS Opt: Same as current")


def test_mastery_node_identification():
    """Test identifying mastery nodes in a build."""
    with open('examples/build1', 'r') as f:
        code = f.read().strip()

    xml = decode_pob_code(code)
    summary = get_passive_tree_summary(xml)

    db = load_mastery_database()

    # Check which allocated nodes are masteries
    mastery_nodes = [
        node_id for node_id in summary['allocated_nodes']
        if db.is_mastery_node(node_id)
    ]

    print(f"\nAllocated nodes: {len(summary['allocated_nodes'])}")
    print(f"Mastery nodes allocated: {len(mastery_nodes)}")

    # Should match the masteryEffects count
    assert len(mastery_nodes) >= len(summary['mastery_effects']), \
        "More mastery effects selected than mastery nodes allocated"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

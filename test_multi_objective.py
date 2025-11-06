#!/usr/bin/env python3
"""
Test multi-objective optimization components (no calculator needed).
"""

import logging
from src.optimizer.multi_objective_optimizer import (
    MultiObjectiveScore,
    ParetoIndividual,
    ParetoFrontier,
    calculate_pareto_ranks,
    calculate_crowding_distances,
    get_pareto_frontier,
    format_pareto_frontier,
)

# Setup logging
logging.basicConfig(level=logging.INFO)


def test_dominance():
    """Test Pareto dominance."""
    print("\n" + "="*80)
    print("Testing Pareto Dominance")
    print("="*80)

    # Create some scores
    score_a = MultiObjectiveScore(
        dps_percent=5.0,
        life_percent=3.0,
        ehp_percent=4.0,
        evaluation=None
    )

    score_b = MultiObjectiveScore(
        dps_percent=4.0,
        life_percent=2.0,
        ehp_percent=3.0,
        evaluation=None
    )

    score_c = MultiObjectiveScore(
        dps_percent=6.0,
        life_percent=1.0,
        ehp_percent=2.0,
        evaluation=None
    )

    print(f"\nScore A: {score_a}")
    print(f"Score B: {score_b}")
    print(f"Score C: {score_c}")

    # Test dominance
    print(f"\nDominance Tests:")
    print(f"  A dominates B? {score_a.dominates(score_b)} (Expected: True)")
    print(f"  B dominates A? {score_b.dominates(score_a)} (Expected: False)")
    print(f"  A dominates C? {score_a.dominates(score_c)} (Expected: False)")
    print(f"  C dominates A? {score_c.dominates(score_a)} (Expected: False)")

    assert score_a.dominates(score_b), "A should dominate B"
    assert not score_b.dominates(score_a), "B should not dominate A"
    assert not score_a.dominates(score_c), "A and C are non-dominated"
    assert not score_c.dominates(score_a), "C and A are non-dominated"

    print(f"\n✅ Pareto dominance working correctly!")


def test_pareto_frontier():
    """Test Pareto frontier extraction."""
    print("\n" + "="*80)
    print("Testing Pareto Frontier Extraction")
    print("="*80)

    # Create population with various scores
    individuals = []

    # Solution A: High DPS, low Life/EHP
    individuals.append(ParetoIndividual(
        xml="<xml>A</xml>",
        score=MultiObjectiveScore(10.0, 2.0, 3.0, None)
    ))

    # Solution B: Balanced
    individuals.append(ParetoIndividual(
        xml="<xml>B</xml>",
        score=MultiObjectiveScore(7.0, 5.0, 6.0, None)
    ))

    # Solution C: Low DPS, high Life/EHP
    individuals.append(ParetoIndividual(
        xml="<xml>C</xml>",
        score=MultiObjectiveScore(3.0, 9.0, 8.0, None)
    ))

    # Solution D: Dominated by B (worse in all)
    individuals.append(ParetoIndividual(
        xml="<xml>D</xml>",
        score=MultiObjectiveScore(5.0, 3.0, 4.0, None)
    ))

    # Solution E: Another non-dominated
    individuals.append(ParetoIndividual(
        xml="<xml>E</xml>",
        score=MultiObjectiveScore(8.0, 7.0, 5.0, None)
    ))

    print(f"\nPopulation:")
    for i, ind in enumerate(individuals, 1):
        print(f"  {chr(64+i)}: {ind.score}")

    # Extract frontier
    frontier = get_pareto_frontier(individuals)

    print(f"\n✅ Pareto frontier extracted: {frontier.size()} solutions")

    # Expected frontier: A, B, C, E (D is dominated by B)
    print(f"\nExpected frontier size: 4 (A, B, C, E)")
    print(f"Actual frontier size: {frontier.size()}")

    assert frontier.size() == 4, f"Expected 4 solutions, got {frontier.size()}"

    # Check that D is not in frontier
    frontier_scores = [ind.score for ind in frontier.individuals]
    d_score = individuals[3].score

    assert d_score not in frontier_scores, "D should not be in frontier (dominated by B)"

    print(f"✅ Dominated solution (D) correctly excluded!")


def test_extreme_points():
    """Test extreme point extraction."""
    print("\n" + "="*80)
    print("Testing Extreme Points")
    print("="*80)

    # Create frontier
    individuals = [
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(10.0, 2.0, 3.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(7.0, 5.0, 6.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(3.0, 9.0, 8.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(5.0, 4.0, 10.0, None)),
    ]

    frontier = ParetoFrontier(individuals)

    extremes = frontier.get_extreme_points()

    print(f"\nExtreme points:")
    print(f"  Max DPS:  {extremes['max_dps'].score}")
    print(f"  Max Life: {extremes['max_life'].score}")
    print(f"  Max EHP:  {extremes['max_ehp'].score}")

    assert extremes['max_dps'].score.dps_percent == 10.0
    assert extremes['max_life'].score.life_percent == 9.0
    assert extremes['max_ehp'].score.ehp_percent == 10.0

    print(f"\n✅ Extreme points correctly identified!")


def test_balanced_solution():
    """Test balanced solution selection."""
    print("\n" + "="*80)
    print("Testing Balanced Solution")
    print("="*80)

    # Create frontier with various solutions
    individuals = [
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(10.0, 2.0, 3.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(5.0, 5.0, 5.0, None)),  # Most balanced!
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(3.0, 9.0, 2.0, None)),
    ]

    frontier = ParetoFrontier(individuals)

    balanced = frontier.get_balanced_solution()

    print(f"\nSolutions:")
    for i, ind in enumerate(individuals, 1):
        print(f"  {i}: {ind.score}")

    print(f"\nBalanced solution: {balanced.score}")

    # The (5, 5, 5) solution should be selected
    assert balanced.score.dps_percent == 5.0
    assert balanced.score.life_percent == 5.0
    assert balanced.score.ehp_percent == 5.0

    print(f"✅ Balanced solution correctly identified!")


def test_crowding_distance():
    """Test crowding distance calculation."""
    print("\n" + "="*80)
    print("Testing Crowding Distance")
    print("="*80)

    # Create front with 4 solutions
    individuals = [
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(10.0, 2.0, 3.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(7.0, 5.0, 6.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(5.0, 7.0, 7.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(3.0, 9.0, 8.0, None)),
    ]

    print(f"\nFront with {len(individuals)} solutions")

    # Calculate crowding distances
    calculate_crowding_distances(individuals)

    print(f"\nCrowding distances:")
    for i, ind in enumerate(individuals, 1):
        print(f"  Solution {i}: distance = {ind.crowding_distance}")

    # Boundary solutions should have infinite distance
    assert individuals[0].crowding_distance == float('inf'), \
        "Boundary solution should have infinite distance"
    assert individuals[-1].crowding_distance == float('inf'), \
        "Boundary solution should have infinite distance"

    print(f"✅ Crowding distances calculated correctly!")


def test_formatting():
    """Test Pareto frontier formatting."""
    print("\n" + "="*80)
    print("Testing Frontier Formatting")
    print("="*80)

    # Create frontier
    individuals = [
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(10.0, 2.0, 3.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(7.0, 5.0, 6.0, None)),
        ParetoIndividual(xml="<xml>", score=MultiObjectiveScore(3.0, 9.0, 8.0, None)),
    ]

    frontier = ParetoFrontier(individuals)

    formatted = format_pareto_frontier(frontier)

    print(formatted)

    assert "Pareto Frontier: 3 Solutions" in formatted
    assert "Max DPS" in formatted
    assert "Max Life" in formatted
    assert "Balanced" in formatted

    print(f"✅ Formatting working correctly!")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("MULTI-OBJECTIVE OPTIMIZATION TEST")
    print("="*80)
    print("\nThese tests verify multi-objective components are working.")

    try:
        test_dominance()
        test_pareto_frontier()
        test_extreme_points()
        test_balanced_solution()
        test_crowding_distance()
        test_formatting()

        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\n✅ Multi-objective optimization core working!")
        print("✅ Pareto dominance implemented")
        print("✅ Frontier extraction working")
        print("✅ Crowding distance calculated")
        print("✅ Formatting working")
        print("\n📝 Next steps:")
        print("   - Integrate with genetic algorithm (NSGA-II)")
        print("   - Test on real builds")
        print("   - Create visualization")
        print("\n" + "="*80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

"""
Unit tests for the constraint system.

Tests PointBudgetConstraint, ConstraintSet, and auto_constraints_from_xml
without any PoB dependency.
"""

import pytest
from src.optimizer.constraints import (
    PointBudgetConstraint,
    ConstraintSet,
    auto_constraints_from_xml,
)


class TestPointBudgetConstraintNodeCount:
    """Tests for fast-path validate_node_count / get_node_count_violation."""

    def test_validate_node_count_within_budget(self):
        constraint = PointBudgetConstraint(min_points=100, max_points=121)
        assert constraint.validate_node_count(110) is True
        assert constraint.validate_node_count(100) is True
        assert constraint.validate_node_count(121) is True

    def test_validate_node_count_over_budget(self):
        constraint = PointBudgetConstraint(max_points=121)
        assert constraint.validate_node_count(122) is False
        assert constraint.validate_node_count(150) is False

    def test_validate_node_count_under_budget(self):
        constraint = PointBudgetConstraint(min_points=100, max_points=121)
        assert constraint.validate_node_count(99) is False
        assert constraint.validate_node_count(50) is False

    def test_validate_node_count_no_limits(self):
        constraint = PointBudgetConstraint()
        assert constraint.validate_node_count(0) is True
        assert constraint.validate_node_count(999) is True

    def test_get_node_count_violation_message(self):
        constraint = PointBudgetConstraint(min_points=100, max_points=121)

        assert constraint.get_node_count_violation(110) is None

        msg = constraint.get_node_count_violation(130)
        assert msg is not None
        assert "130" in msg
        assert "121" in msg

        msg = constraint.get_node_count_violation(90)
        assert msg is not None
        assert "90" in msg
        assert "100" in msg


class TestPointBudgetFromLevel:
    """Tests for PointBudgetConstraint.from_level."""

    def test_from_level_100(self):
        constraint = PointBudgetConstraint.from_level(100)
        assert constraint.max_points == 121  # 100 + 21

    def test_from_level_100_with_offset(self):
        constraint = PointBudgetConstraint.from_level(100, min_offset=-5)
        assert constraint.max_points == 121
        assert constraint.min_points == 116  # 121 - 5

    def test_from_level_50(self):
        constraint = PointBudgetConstraint.from_level(50)
        assert constraint.max_points == 71  # 50 + 21

    def test_from_level_1(self):
        constraint = PointBudgetConstraint.from_level(1)
        assert constraint.max_points == 22  # 1 + 21


class TestConstraintSetDelegation:
    """Tests for ConstraintSet.validate_node_count and get_fitness_penalty."""

    def test_constraint_set_delegates(self):
        cs = ConstraintSet(
            point_budget=PointBudgetConstraint(max_points=121)
        )
        assert cs.validate_node_count(120) is True
        assert cs.validate_node_count(122) is False

    def test_constraint_set_no_constraints(self):
        cs = ConstraintSet()
        assert cs.validate_node_count(0) is True
        assert cs.validate_node_count(999) is True

    def test_fitness_penalty_no_violation(self):
        cs = ConstraintSet(
            point_budget=PointBudgetConstraint(max_points=121)
        )
        assert cs.get_fitness_penalty(121) == 0.0
        assert cs.get_fitness_penalty(100) == 0.0

    def test_fitness_penalty_over_budget(self):
        cs = ConstraintSet(
            point_budget=PointBudgetConstraint(max_points=121)
        )
        assert cs.get_fitness_penalty(122) == -100.0
        assert cs.get_fitness_penalty(124) == -300.0
        assert cs.get_fitness_penalty(131) == -1000.0

    def test_fitness_penalty_no_constraints(self):
        cs = ConstraintSet()
        assert cs.get_fitness_penalty(999) == 0.0


class TestAutoConstraintsFromXml:
    """Tests for auto_constraints_from_xml factory."""

    def test_auto_from_xml(self):
        xml = '<PathOfBuilding><Build level="95" ascendClassName="Slayer"></Build></PathOfBuilding>'
        cs = auto_constraints_from_xml(xml)
        assert cs is not None
        assert cs.point_budget is not None
        assert cs.point_budget.max_points == 116  # 95 + 21
        assert cs.point_budget.min_points == 111  # 116 - 5
        assert cs.attributes is None
        assert cs.jewel_sockets is None

    def test_auto_from_xml_low_level(self):
        xml = '<PathOfBuilding><Build level="50" className="Ranger"></Build></PathOfBuilding>'
        cs = auto_constraints_from_xml(xml)
        assert cs is not None
        assert cs.point_budget.max_points == 71  # 50 + 21

    def test_auto_from_xml_level_100(self):
        xml = '<PathOfBuilding><Build level="100" className="Witch"></Build></PathOfBuilding>'
        cs = auto_constraints_from_xml(xml)
        assert cs is not None
        assert cs.point_budget.max_points == 121

    def test_auto_from_xml_no_level(self):
        xml = '<PathOfBuilding><Build className="Witch"></Build></PathOfBuilding>'
        cs = auto_constraints_from_xml(xml)
        assert cs is None

    def test_auto_from_xml_invalid_level(self):
        xml = '<PathOfBuilding><Build level="200" className="Witch"></Build></PathOfBuilding>'
        cs = auto_constraints_from_xml(xml)
        assert cs is None

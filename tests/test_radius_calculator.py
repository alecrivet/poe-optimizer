#!/usr/bin/env python3
"""
Tests for radius calculator and tree position functionality.

Tests cover:
- Tree position loading and parsing
- Distance calculations
- Radius-based node filtering
- Thread of Hope ring calculations
"""

import pytest
import math

from src.pob.tree_positions import (
    NodePosition,
    GroupData,
    TreePositionLoader,
)
from src.pob.jewel.radius_calculator import RadiusCalculator


class TestNodePosition:
    """Test NodePosition dataclass."""

    def test_distance_to_same_position(self):
        """Test distance to same position is 0."""
        pos1 = NodePosition(node_id=1, x=100.0, y=200.0, group=1, orbit=0, orbit_index=0)
        pos2 = NodePosition(node_id=2, x=100.0, y=200.0, group=1, orbit=0, orbit_index=0)
        assert pos1.distance_to(pos2) == 0.0

    def test_distance_to_horizontal(self):
        """Test horizontal distance calculation."""
        pos1 = NodePosition(node_id=1, x=0.0, y=0.0, group=1, orbit=0, orbit_index=0)
        pos2 = NodePosition(node_id=2, x=100.0, y=0.0, group=1, orbit=0, orbit_index=0)
        assert pos1.distance_to(pos2) == 100.0

    def test_distance_to_vertical(self):
        """Test vertical distance calculation."""
        pos1 = NodePosition(node_id=1, x=0.0, y=0.0, group=1, orbit=0, orbit_index=0)
        pos2 = NodePosition(node_id=2, x=0.0, y=100.0, group=1, orbit=0, orbit_index=0)
        assert pos1.distance_to(pos2) == 100.0

    def test_distance_to_diagonal(self):
        """Test diagonal distance calculation (Pythagorean)."""
        pos1 = NodePosition(node_id=1, x=0.0, y=0.0, group=1, orbit=0, orbit_index=0)
        pos2 = NodePosition(node_id=2, x=3.0, y=4.0, group=1, orbit=0, orbit_index=0)
        assert pos1.distance_to(pos2) == 5.0


class TestRadiusCalculator:
    """Test RadiusCalculator functionality."""

    @pytest.fixture
    def sample_positions(self):
        """Create sample node positions for testing."""
        return {
            1: NodePosition(node_id=1, x=0.0, y=0.0, group=1, orbit=0, orbit_index=0),
            2: NodePosition(node_id=2, x=500.0, y=0.0, group=1, orbit=1, orbit_index=0),
            3: NodePosition(node_id=3, x=1000.0, y=0.0, group=1, orbit=1, orbit_index=1),
            4: NodePosition(node_id=4, x=1500.0, y=0.0, group=2, orbit=0, orbit_index=0),
            5: NodePosition(node_id=5, x=2000.0, y=0.0, group=2, orbit=1, orbit_index=0),
            6: NodePosition(node_id=6, x=0.0, y=700.0, group=3, orbit=0, orbit_index=0),
            7: NodePosition(node_id=7, x=0.0, y=1100.0, group=3, orbit=1, orbit_index=0),
            8: NodePosition(node_id=8, x=0.0, y=1600.0, group=4, orbit=0, orbit_index=0),
        }

    @pytest.fixture
    def calculator(self, sample_positions):
        """Create RadiusCalculator with sample positions."""
        return RadiusCalculator(sample_positions)

    def test_distance_calculation(self, calculator):
        """Test basic distance calculation between nodes."""
        dist = calculator.distance(1, 2)
        assert dist == 500.0

    def test_distance_symmetric(self, calculator):
        """Test that distance is symmetric."""
        dist_1_2 = calculator.distance(1, 2)
        dist_2_1 = calculator.distance(2, 1)
        assert dist_1_2 == dist_2_1

    def test_distance_caching(self, calculator):
        """Test that distance results are cached."""
        dist1 = calculator.distance(1, 2)
        cache_key = (1, 2)
        assert cache_key in calculator._distance_cache
        dist2 = calculator.distance(1, 2)
        assert dist1 == dist2

    def test_distance_missing_node(self, calculator):
        """Test distance with missing node returns infinity."""
        dist = calculator.distance(1, 999)
        assert dist == float("inf")

    def test_get_nodes_in_small_radius(self, calculator):
        """Test getting nodes in small radius (800)."""
        nodes = calculator.get_nodes_in_radius(1, RadiusCalculator.SMALL_RADIUS)
        assert 2 in nodes  # 500 < 800
        assert 6 in nodes  # 700 < 800
        assert 3 not in nodes  # 1000 > 800
        assert 7 not in nodes  # 1100 > 800

    def test_get_nodes_in_medium_radius(self, calculator):
        """Test getting nodes in medium radius (1200)."""
        nodes = calculator.get_nodes_in_radius(1, RadiusCalculator.MEDIUM_RADIUS)
        assert 2 in nodes  # 500 < 1200
        assert 3 in nodes  # 1000 < 1200
        assert 6 in nodes  # 700 < 1200
        assert 7 in nodes  # 1100 < 1200
        assert 4 not in nodes  # 1500 > 1200

    def test_get_nodes_in_large_radius(self, calculator):
        """Test getting nodes in large radius (1800)."""
        nodes = calculator.get_nodes_in_radius(1, RadiusCalculator.LARGE_RADIUS)
        assert 2 in nodes  # 500 < 1800
        assert 3 in nodes  # 1000 < 1800
        assert 4 in nodes  # 1500 < 1800
        assert 6 in nodes  # 700 < 1800
        assert 7 in nodes  # 1100 < 1800
        assert 8 in nodes  # 1600 < 1800
        assert 5 not in nodes  # 2000 > 1800

    def test_get_nodes_in_radius_excludes_center(self, calculator):
        """Test that center node is excluded from results."""
        nodes = calculator.get_nodes_in_radius(1, 10000)
        assert 1 not in nodes

    def test_get_nodes_in_radius_missing_center(self, calculator):
        """Test radius calculation with missing center node."""
        nodes = calculator.get_nodes_in_radius(999, 1000)
        assert len(nodes) == 0

    def test_get_nodes_in_ring(self, calculator):
        """Test getting nodes in a ring (donut shape)."""
        nodes = calculator.get_nodes_in_ring(1, 600, 1200)
        assert 2 not in nodes  # 500 < 600 (too close)
        assert 6 in nodes      # 700 in [600, 1200]
        assert 3 in nodes      # 1000 in [600, 1200]
        assert 7 in nodes      # 1100 in [600, 1200]
        assert 4 not in nodes  # 1500 > 1200 (too far)

    def test_get_nodes_in_ring_empty(self, calculator):
        """Test ring with no nodes."""
        nodes = calculator.get_nodes_in_ring(5, 5000, 6000)
        assert len(nodes) == 0

    def test_get_thread_of_hope_nodes_small(self, calculator):
        """Test Thread of Hope small ring."""
        nodes = calculator.get_thread_of_hope_nodes(1, "Small")
        assert isinstance(nodes, set)

    def test_get_thread_of_hope_nodes_invalid_size(self, calculator):
        """Test Thread of Hope with invalid ring size."""
        nodes = calculator.get_thread_of_hope_nodes(1, "Invalid")
        assert len(nodes) == 0

    def test_precompute_socket_radii(self, calculator):
        """Test precomputing radii for multiple sockets."""
        socket_ids = {1, 3}
        result = calculator.precompute_socket_radii(socket_ids)
        assert 1 in result
        assert 3 in result
        assert "small" in result[1]
        assert "medium" in result[1]
        assert "large" in result[1]
        assert "thread_small" in result[1]

    def test_get_closest_socket(self, calculator):
        """Test finding closest socket to a node."""
        socket_ids = {2, 4, 6}
        closest = calculator.get_closest_socket(1, socket_ids)
        assert closest is not None
        socket_id, distance = closest
        assert socket_id == 2  # Closest is node 2 at distance 500

    def test_get_closest_socket_missing_node(self, calculator):
        """Test closest socket with missing target node."""
        result = calculator.get_closest_socket(999, {1, 2, 3})
        assert result is None


class TestTreePositionLoader:
    """Test TreePositionLoader functionality."""

    def test_default_orbit_configuration(self):
        """Test that default orbit configuration is set."""
        loader = TreePositionLoader()
        assert loader._skills_per_orbit == [1, 6, 16, 16, 40, 72, 72]
        assert loader._orbit_radii == [0, 82, 162, 335, 493, 662, 846]

    def test_calculate_node_position_center(self):
        """Test position calculation for center node (orbit 0)."""
        loader = TreePositionLoader()
        loader._groups = {
            1: GroupData(group_id=1, x=100.0, y=200.0, orbits=[0], node_ids=[])
        }
        x, y = loader._calculate_node_position(1, 0, 0)
        assert x == 100.0
        assert y == 200.0

    def test_calculate_node_position_orbit1(self):
        """Test position calculation for orbit 1 nodes."""
        loader = TreePositionLoader()
        loader._groups = {
            1: GroupData(group_id=1, x=0.0, y=0.0, orbits=[0, 1], node_ids=[])
        }
        x, y = loader._calculate_node_position(1, 1, 0)
        assert x is not None
        assert y is not None
        assert abs(x - 0.0) < 0.01
        assert abs(y - (-82.0)) < 0.01

    def test_calculate_node_position_missing_group(self):
        """Test position calculation with missing group."""
        loader = TreePositionLoader()
        loader._groups = {}
        x, y = loader._calculate_node_position(999, 0, 0)
        assert x is None
        assert y is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_positions(self):
        """Test RadiusCalculator with empty positions."""
        calc = RadiusCalculator({})
        nodes = calc.get_nodes_in_radius(1, 1000)
        assert len(nodes) == 0

    def test_single_node(self):
        """Test with single node (should find no nodes in radius)."""
        positions = {
            1: NodePosition(node_id=1, x=0.0, y=0.0, group=1, orbit=0, orbit_index=0)
        }
        calc = RadiusCalculator(positions)
        nodes = calc.get_nodes_in_radius(1, 1000)
        assert len(nodes) == 0

    def test_negative_coordinates(self):
        """Test with negative coordinates."""
        positions = {
            1: NodePosition(node_id=1, x=-500.0, y=-500.0, group=1, orbit=0, orbit_index=0),
            2: NodePosition(node_id=2, x=0.0, y=0.0, group=1, orbit=0, orbit_index=0),
        }
        calc = RadiusCalculator(positions)
        dist = calc.distance(1, 2)
        expected = math.sqrt(500**2 + 500**2)
        assert abs(dist - expected) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Tests for cluster optimization functionality (Stream E)

This module tests:
- ClusterNode and ClusterSubgraph data structures
- ClusterSubgraphBuilder for constructing subgraphs
- ClusterNotableOptimizer for finding optimal allocations
- JewelRegistry integration with cluster optimization
"""

import pytest
from src.pob.jewel.cluster import (
    ClusterJewel,
    ClusterJewelSize,
    CLUSTER_NODE_MIN_ID,
    decode_cluster_node_id,
)
from src.pob.jewel.cluster_subgraph import (
    ClusterNode,
    ClusterSubgraph,
    ClusterSubgraphBuilder,
    encode_cluster_node_id,
    get_cluster_nodes_for_jewel,
)
from src.pob.jewel.cluster_optimizer import (
    ClusterAllocation,
    ClusterNotableOptimizer,
    NotableEvaluation,
)
from src.pob.jewel.registry import JewelRegistry
from src.pob.jewel.base import JewelCategory


class TestClusterNode:
    """Test ClusterNode data structure"""

    def test_cluster_node_creation(self):
        """Test basic ClusterNode creation"""
        node = ClusterNode(
            node_id=65537,
            name="Test Notable",
            is_notable=True,
            is_socket=False,
            stats=["10% increased Damage"],
            connections={65536, 65538}
        )

        assert node.node_id == 65537
        assert node.name == "Test Notable"
        assert node.is_notable is True
        assert node.is_socket is False
        assert "10% increased Damage" in node.stats
        assert 65536 in node.connections
        assert 65538 in node.connections

    def test_cluster_node_hash(self):
        """Test ClusterNode hashing for set operations"""
        node1 = ClusterNode(node_id=65537, name="Node 1")
        node2 = ClusterNode(node_id=65537, name="Node 1 Copy")
        node3 = ClusterNode(node_id=65538, name="Node 2")

        # Same ID should hash the same
        assert hash(node1) == hash(node2)

        # Can be used in sets
        node_set = {node1, node2, node3}
        assert len(node_set) == 2  # node1 and node2 are equal

    def test_cluster_node_equality(self):
        """Test ClusterNode equality comparison"""
        node1 = ClusterNode(node_id=65537, name="Node 1")
        node2 = ClusterNode(node_id=65537, name="Different Name")
        node3 = ClusterNode(node_id=65538, name="Node 1")

        assert node1 == node2  # Same ID
        assert node1 != node3  # Different ID
        assert node1 != "not a node"  # Different type


class TestEncodeClusterNodeId:
    """Test cluster node ID encoding/decoding"""

    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding are inverse operations"""
        test_cases = [
            (0, 0, 0, 0),
            (5, 2, 1, 0),
            (11, 2, 5, 2),
            (3, 1, 2, 1),
        ]

        for node_idx, size_idx, large_idx, medium_idx in test_cases:
            encoded = encode_cluster_node_id(node_idx, size_idx, large_idx, medium_idx)
            decoded = decode_cluster_node_id(encoded)

            assert decoded['node_index'] == node_idx
            assert decoded['size_index'] == size_idx
            assert decoded['large_socket_index'] == large_idx
            assert decoded['medium_socket_index'] == medium_idx

    def test_encoded_ids_are_cluster_nodes(self):
        """Test that encoded IDs are valid cluster node IDs"""
        encoded = encode_cluster_node_id(5, 2, 1, 0)
        assert encoded >= CLUSTER_NODE_MIN_ID

    def test_minimum_encoded_id(self):
        """Test minimum possible encoded ID"""
        encoded = encode_cluster_node_id(0, 0, 0, 0)
        assert encoded == CLUSTER_NODE_MIN_ID


class TestClusterSubgraph:
    """Test ClusterSubgraph functionality"""

    def create_test_subgraph(self) -> ClusterSubgraph:
        """Create a test subgraph for testing"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.MEDIUM,
            socket_node_id=65536,
        )

        # Create a simple linear structure: socket -> node1 -> node2(notable) -> node3
        socket = ClusterNode(node_id=65536, name="Socket", connections={65537})
        node1 = ClusterNode(node_id=65537, name="Small 1", connections={65536, 65538})
        node2 = ClusterNode(node_id=65538, name="Notable 1", is_notable=True, connections={65537, 65539})
        node3 = ClusterNode(node_id=65539, name="Small 2", connections={65538})

        return ClusterSubgraph(
            jewel=jewel,
            socket_node=65536,
            nodes={
                65536: socket,
                65537: node1,
                65538: node2,
                65539: node3,
            },
            notables=[65538],
            small_passives=[65537, 65539],
            nested_sockets=[],
        )

    def test_get_paths_to_notable(self):
        """Test finding paths from socket to notable"""
        subgraph = self.create_test_subgraph()

        paths = subgraph.get_paths_to_notable(65538)

        assert len(paths) == 1
        assert paths[0] == [65536, 65537, 65538]

    def test_get_paths_to_nonexistent_notable(self):
        """Test finding paths to a node that doesn't exist"""
        subgraph = self.create_test_subgraph()

        paths = subgraph.get_paths_to_notable(99999)

        assert len(paths) == 0

    def test_get_minimum_allocation_single_notable(self):
        """Test minimum allocation for a single notable"""
        subgraph = self.create_test_subgraph()

        allocation = subgraph.get_minimum_allocation({65538})

        assert 65536 in allocation  # Socket
        assert 65537 in allocation  # Path node
        assert 65538 in allocation  # Notable
        assert 65539 not in allocation  # Beyond notable

    def test_get_minimum_allocation_empty(self):
        """Test minimum allocation with no notables"""
        subgraph = self.create_test_subgraph()

        allocation = subgraph.get_minimum_allocation(set())

        assert allocation == {65536}  # Just the socket

    def test_get_allocation_cost(self):
        """Test calculating point cost for allocation"""
        subgraph = self.create_test_subgraph()

        # Cost to reach notable at 65538: need 65537 (small) + 65538 (notable) = 2 points
        cost = subgraph.get_allocation_cost({65538})

        assert cost == 2

    def test_is_valid_allocation_connected(self):
        """Test validation of connected allocation"""
        subgraph = self.create_test_subgraph()

        # Valid: socket -> small -> notable
        valid = subgraph.is_valid_allocation({65536, 65537, 65538})
        assert valid is True

    def test_is_valid_allocation_disconnected(self):
        """Test validation of disconnected allocation"""
        subgraph = self.create_test_subgraph()

        # Invalid: notable without path from socket
        invalid = subgraph.is_valid_allocation({65536, 65538})
        assert invalid is False

    def test_is_valid_allocation_no_socket(self):
        """Test allocation without socket is invalid"""
        subgraph = self.create_test_subgraph()

        invalid = subgraph.is_valid_allocation({65537, 65538})
        assert invalid is False

    def test_get_allocated_notables(self):
        """Test getting allocated notables from a node set"""
        subgraph = self.create_test_subgraph()

        allocated = subgraph.get_allocated_notables({65536, 65537, 65538})

        assert 65538 in allocated
        assert len(allocated) == 1

    def test_get_unallocated_notables(self):
        """Test getting unallocated notables"""
        subgraph = self.create_test_subgraph()

        unallocated = subgraph.get_unallocated_notables({65536, 65537})

        assert 65538 in unallocated


class TestClusterSubgraphBuilder:
    """Test ClusterSubgraphBuilder"""

    def test_build_from_jewel_basic(self):
        """Test building subgraph from jewel and allocated nodes"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.LARGE,
            socket_node_id=65536,
            notables=["Test Notable"],
        )

        # Create node IDs for a large cluster with notable at position 4
        node_ids = {
            encode_cluster_node_id(0, 2),  # First small
            encode_cluster_node_id(1, 2),  # Second small
            encode_cluster_node_id(4, 2),  # Notable position
        }

        builder = ClusterSubgraphBuilder()
        subgraph = builder.build_from_jewel(jewel, node_ids)

        assert subgraph.socket_node == 65536
        assert len(subgraph.nodes) > 0
        assert len(subgraph.notables) > 0

    def test_build_from_jewel_empty_allocated(self):
        """Test building subgraph with no allocated nodes"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.MEDIUM,
            socket_node_id=65536,
        )

        builder = ClusterSubgraphBuilder()
        subgraph = builder.build_from_jewel(jewel, set())

        assert subgraph.socket_node == 65536
        # Only socket node should be present
        assert 65536 in subgraph.nodes

    def test_is_notable_position_large(self):
        """Test notable position detection for large clusters"""
        builder = ClusterSubgraphBuilder()

        assert builder._is_notable_position(4, ClusterJewelSize.LARGE) is True
        assert builder._is_notable_position(6, ClusterJewelSize.LARGE) is True
        assert builder._is_notable_position(10, ClusterJewelSize.LARGE) is True
        assert builder._is_notable_position(0, ClusterJewelSize.LARGE) is False
        assert builder._is_notable_position(3, ClusterJewelSize.LARGE) is False

    def test_is_notable_position_medium(self):
        """Test notable position detection for medium clusters"""
        builder = ClusterSubgraphBuilder()

        assert builder._is_notable_position(2, ClusterJewelSize.MEDIUM) is True
        assert builder._is_notable_position(4, ClusterJewelSize.MEDIUM) is True
        assert builder._is_notable_position(0, ClusterJewelSize.MEDIUM) is False

    def test_is_socket_position_large(self):
        """Test socket position detection for large clusters"""
        builder = ClusterSubgraphBuilder()

        assert builder._is_socket_position(2, ClusterJewelSize.LARGE) is True
        assert builder._is_socket_position(8, ClusterJewelSize.LARGE) is True
        assert builder._is_socket_position(4, ClusterJewelSize.LARGE) is False

    def test_is_socket_position_small(self):
        """Test small clusters have no sockets"""
        builder = ClusterSubgraphBuilder()

        assert builder._is_socket_position(0, ClusterJewelSize.SMALL) is False
        assert builder._is_socket_position(1, ClusterJewelSize.SMALL) is False
        assert builder._is_socket_position(2, ClusterJewelSize.SMALL) is False


class TestClusterAllocation:
    """Test ClusterAllocation data structure"""

    def test_allocation_all_allocated(self):
        """Test getting all allocated nodes"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.MEDIUM,
            socket_node_id=65536,
        )

        subgraph = ClusterSubgraph(
            jewel=jewel,
            socket_node=65536,
            nodes={
                65536: ClusterNode(node_id=65536, name="Socket"),
                65537: ClusterNode(node_id=65537, name="Small"),
                65538: ClusterNode(node_id=65538, name="Notable", is_notable=True),
            },
            notables=[65538],
            small_passives=[65537],
        )

        allocation = ClusterAllocation(
            subgraph=subgraph,
            allocated_notables={65538},
            allocated_small={65537},
            total_points=2,
            value_score=15.0,
        )

        all_nodes = allocation.all_allocated

        assert 65536 in all_nodes  # Socket
        assert 65537 in all_nodes  # Small
        assert 65538 in all_nodes  # Notable

    def test_allocation_notable_names(self):
        """Test getting notable names from allocation"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.MEDIUM,
            socket_node_id=65536,
        )

        subgraph = ClusterSubgraph(
            jewel=jewel,
            socket_node=65536,
            nodes={
                65536: ClusterNode(node_id=65536, name="Socket"),
                65538: ClusterNode(node_id=65538, name="Fuel the Fight", is_notable=True),
            },
            notables=[65538],
        )

        allocation = ClusterAllocation(
            subgraph=subgraph,
            allocated_notables={65538},
            total_points=1,
        )

        names = allocation.get_notable_names()

        assert "Fuel the Fight" in names


class TestNotableEvaluation:
    """Test NotableEvaluation sorting"""

    def test_notable_evaluation_sorting(self):
        """Test that evaluations sort by efficiency descending"""
        eval1 = NotableEvaluation(
            notable_id=1,
            notable_name="Low Efficiency",
            value_gained=5.0,
            point_cost=5,
            efficiency=1.0,
        )
        eval2 = NotableEvaluation(
            notable_id=2,
            notable_name="High Efficiency",
            value_gained=10.0,
            point_cost=2,
            efficiency=5.0,
        )
        eval3 = NotableEvaluation(
            notable_id=3,
            notable_name="Medium Efficiency",
            value_gained=6.0,
            point_cost=2,
            efficiency=3.0,
        )

        sorted_evals = sorted([eval1, eval2, eval3])

        # Should be ordered by efficiency descending
        assert sorted_evals[0].efficiency == 5.0
        assert sorted_evals[1].efficiency == 3.0
        assert sorted_evals[2].efficiency == 1.0


class TestClusterNotableOptimizer:
    """Test ClusterNotableOptimizer"""

    def create_test_subgraph(self) -> ClusterSubgraph:
        """Create a test subgraph with multiple notables"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.MEDIUM,
            socket_node_id=65536,
        )

        # Create structure with two notables
        # socket -> small1 -> notable1
        #                  -> small2 -> notable2
        socket = ClusterNode(node_id=65536, name="Socket", connections={65537})
        small1 = ClusterNode(node_id=65537, name="Small 1", connections={65536, 65538, 65539})
        notable1 = ClusterNode(node_id=65538, name="Notable 1", is_notable=True, connections={65537})
        small2 = ClusterNode(node_id=65539, name="Small 2", connections={65537, 65540})
        notable2 = ClusterNode(node_id=65540, name="Notable 2", is_notable=True, connections={65539})

        return ClusterSubgraph(
            jewel=jewel,
            socket_node=65536,
            nodes={
                65536: socket,
                65537: small1,
                65538: notable1,
                65539: small2,
                65540: notable2,
            },
            notables=[65538, 65540],
            small_passives=[65537, 65539],
            nested_sockets=[],
        )

    def test_optimizer_without_calculator(self):
        """Test optimizer using heuristic scoring"""
        optimizer = ClusterNotableOptimizer(calculator=None)
        subgraph = self.create_test_subgraph()

        # Mock XML (not actually used without calculator)
        base_xml = "<PathOfBuilding></PathOfBuilding>"

        allocation = optimizer.optimize_allocation(
            subgraph, base_xml, objective="dps"
        )

        assert allocation is not None
        assert isinstance(allocation, ClusterAllocation)

    def test_optimizer_respects_point_limit(self):
        """Test that optimizer respects max_points constraint"""
        optimizer = ClusterNotableOptimizer(calculator=None)
        subgraph = self.create_test_subgraph()
        base_xml = "<PathOfBuilding></PathOfBuilding>"

        # With very low point limit, should get fewer nodes
        allocation = optimizer.optimize_allocation(
            subgraph, base_xml, objective="dps", max_points=1
        )

        assert allocation.total_points <= 1

    def test_evaluate_notable_heuristic(self):
        """Test notable evaluation with heuristic scoring"""
        optimizer = ClusterNotableOptimizer(calculator=None)
        subgraph = self.create_test_subgraph()
        base_xml = "<PathOfBuilding></PathOfBuilding>"

        value = optimizer.evaluate_notable(
            subgraph,
            notable_id=65538,
            current_allocation={65536},
            base_xml=base_xml,
            objective="dps"
        )

        # Heuristic gives 10.0 for notables
        assert value == 10.0

    def test_empty_subgraph_optimization(self):
        """Test optimizing a subgraph with no notables"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.SMALL,
            socket_node_id=65536,
        )

        subgraph = ClusterSubgraph(
            jewel=jewel,
            socket_node=65536,
            nodes={65536: ClusterNode(node_id=65536, name="Socket")},
            notables=[],
            small_passives=[],
        )

        optimizer = ClusterNotableOptimizer()
        allocation = optimizer.optimize_allocation(
            subgraph, "<xml/>", "dps"
        )

        assert len(allocation.allocated_notables) == 0
        assert allocation.total_points == 0


class TestJewelRegistryClusterIntegration:
    """Test JewelRegistry cluster optimization integration"""

    def test_get_protected_nodes_default(self):
        """Test default protected nodes behavior"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Medium Cluster Jewel
Adds 4 Passive Skills
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        registry = JewelRegistry.from_build_xml(xml)

        # With cluster nodes allocated
        allocated = {65536, 65537, 65538}
        protected = registry.get_protected_nodes(allocated)

        # Default: all cluster nodes are protected
        assert 65536 in protected
        assert 65537 in protected
        assert 65538 in protected

    def test_get_protected_nodes_allow_cluster_optimization(self):
        """Test protected nodes with cluster optimization enabled"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Medium Cluster Jewel
Adds 4 Passive Skills
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        registry = JewelRegistry.from_build_xml(xml)

        allocated = {65536, 65537, 65538}
        protected = registry.get_protected_nodes(
            allocated,
            allow_cluster_optimization=True
        )

        # With optimization: only socket entry point is protected
        assert 65536 in protected
        # Other cluster nodes should NOT be protected
        assert 65537 not in protected
        assert 65538 not in protected

    def test_get_cluster_subgraphs(self):
        """Test getting cluster subgraphs from registry"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="26725" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        registry = JewelRegistry.from_build_xml(xml)

        # Simulate some allocated cluster nodes
        allocated = {26725, 65537, 65538}

        subgraphs = registry.get_cluster_subgraphs(allocated)

        assert len(subgraphs) == 1
        assert subgraphs[0].socket_node == 26725


class TestGetClusterNodesForJewel:
    """Test get_cluster_nodes_for_jewel function"""

    def test_outer_socket_jewel(self):
        """Test getting nodes for jewel in outer socket"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.LARGE,
            socket_node_id=26725,  # Outer socket (< 65536)
        )

        allocated = {26725, 65537, 65538, 100}  # Mix of cluster and regular nodes

        cluster_nodes = get_cluster_nodes_for_jewel(jewel, allocated)

        assert 65537 in cluster_nodes
        assert 65538 in cluster_nodes
        assert 100 not in cluster_nodes  # Regular node
        assert 26725 not in cluster_nodes  # Not a cluster node ID

    def test_no_socket(self):
        """Test jewel with no socket assigned"""
        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            size=ClusterJewelSize.MEDIUM,
            socket_node_id=None,
        )

        allocated = {65537, 65538}

        cluster_nodes = get_cluster_nodes_for_jewel(jewel, allocated)

        assert len(cluster_nodes) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

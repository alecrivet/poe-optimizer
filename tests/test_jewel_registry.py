#!/usr/bin/env python3
"""
Tests for JewelRegistry - unified jewel handling and protected nodes
"""

import pytest
from pathlib import Path
from src.pob.jewel.registry import JewelRegistry
from src.pob.jewel.timeless import TimelessJewel
from src.pob.jewel.cluster import ClusterJewel
from src.pob.jewel.unique import UniqueJewel


# Sample XML with various jewel types
TIMELESS_JEWEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Items>
        <Item id="1">Prismatic Jewel
Glorious Vanity
Timeless Jewel
Limited to: 1
Historic
Passives in radius are Conquered by the Vaal
Bathed in the blood of 123456 sacrificed in the name of Doryani
Corrupts your Soul
</Item>
    </Items>
    <Sockets>
        <Socket nodeId="26725" itemId="1"/>
    </Sockets>
</PathOfBuilding>
"""

CLUSTER_JEWEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Items>
        <Item id="2">
            Medium Cluster Jewel
            Item Level: 75
            Adds 4 Passive Skills
            Added Small Passive Skills grant: 10% increased Damage
            1 Added Passive Skill is Martial Prowess
            1 Added Passive Skill is Fuel the Fight
        </Item>
    </Items>
    <Tree>
        <Spec>
            <Node nodeId="65537" active="true" ascendancyName="" isJewelSocket="false" isMultipleChoiceOption="false"/>
            <Node nodeId="65538" active="true" ascendancyName="" isJewelSocket="false" isMultipleChoiceOption="false"/>
        </Spec>
    </Tree>
    <Sockets>
        <Socket nodeId="65536" itemId="2"/>
    </Sockets>
</PathOfBuilding>
"""

UNIQUE_JEWEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Items>
        <Item id="3">Crimson Jewel
Fragility
Limited to: 1
-1 to Maximum Endurance Charges
+25 to Strength
</Item>
    </Items>
    <Sockets>
        <Socket nodeId="12345" itemId="3"/>
    </Sockets>
</PathOfBuilding>
"""

MIXED_JEWELS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Items>
        <Item id="1">Prismatic Jewel
Glorious Vanity
Timeless Jewel
Bathed in the blood of 100 sacrificed in the name of Xibaqua
</Item>
        <Item id="2">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
        <Item id="3">Crimson Jewel
Fragility
-1 to Maximum Endurance Charges
</Item>
    </Items>
    <Tree>
        <Spec>
            <Node nodeId="2001" active="true"/>
            <Node nodeId="2002" active="true"/>
        </Spec>
    </Tree>
    <Sockets>
        <Socket nodeId="1000" itemId="1"/>
        <Socket nodeId="2000" itemId="2"/>
        <Socket nodeId="3000" itemId="3"/>
    </Sockets>
</PathOfBuilding>
"""


class TestJewelRegistry:
    """Test JewelRegistry functionality"""

    def test_empty_registry(self):
        """Test creating empty registry"""
        registry = JewelRegistry()
        assert registry.total_count == 0
        assert registry.get_protected_nodes({1, 2, 3}) == set()

    def test_parse_timeless_jewel(self):
        """Test parsing timeless jewel from XML"""
        registry = JewelRegistry.from_build_xml(TIMELESS_JEWEL_XML)

        assert len(registry.timeless_jewels) == 1
        jewel = registry.timeless_jewels[0]
        assert isinstance(jewel, TimelessJewel)
        assert jewel.jewel_type == "Glorious Vanity"
        assert jewel.variant == "Doryani"
        assert jewel.seed == 123456
        assert jewel.socket_node_id == 26725

    def test_parse_cluster_jewel(self):
        """Test parsing cluster jewel from XML"""
        registry = JewelRegistry.from_build_xml(CLUSTER_JEWEL_XML)

        assert len(registry.cluster_jewels) == 1
        jewel = registry.cluster_jewels[0]
        assert isinstance(jewel, ClusterJewel)
        assert jewel.size.value == "Medium"
        assert jewel.socket_node_id == 65536

    def test_parse_unique_jewel(self):
        """Test parsing unique jewel from XML"""
        registry = JewelRegistry.from_build_xml(UNIQUE_JEWEL_XML)

        assert len(registry.unique_jewels) == 1
        jewel = registry.unique_jewels[0]
        assert isinstance(jewel, UniqueJewel)
        assert jewel.name == "Fragility"
        assert jewel.socket_node_id == 12345

    def test_parse_mixed_jewels(self):
        """Test parsing multiple jewel types"""
        registry = JewelRegistry.from_build_xml(MIXED_JEWELS_XML)

        assert registry.total_count == 3

        # Check jewel types
        jewel_types = [type(j).__name__ for j in registry.all_jewels]
        assert "TimelessJewel" in jewel_types
        assert "ClusterJewel" in jewel_types
        assert "UniqueJewel" in jewel_types

    def test_protected_nodes_timeless(self):
        """Test that timeless jewel protects its socket"""
        registry = JewelRegistry.from_build_xml(TIMELESS_JEWEL_XML)

        allocated_nodes = {26725, 1000, 2000}
        protected = registry.get_protected_nodes(allocated_nodes)

        assert 26725 in protected
        assert len(protected) == 1

    def test_protected_nodes_cluster(self):
        """Test that cluster jewel protects socket and subgraph"""
        registry = JewelRegistry.from_build_xml(CLUSTER_JEWEL_XML)

        # Cluster socket is 65536, subgraph is 65537-65538
        allocated_nodes = {65536, 65537, 65538, 1000}
        protected = registry.get_protected_nodes(allocated_nodes)

        # Should protect socket and all cluster nodes
        assert 65536 in protected
        assert 65537 in protected
        assert 65538 in protected
        assert 1000 not in protected

    def test_protected_nodes_unique(self):
        """Test that unique jewel protects its socket"""
        registry = JewelRegistry.from_build_xml(UNIQUE_JEWEL_XML)

        allocated_nodes = {12345, 5000}
        protected = registry.get_protected_nodes(allocated_nodes)

        assert 12345 in protected
        assert len(protected) == 1

    def test_protected_nodes_mixed(self):
        """Test protected nodes from mixed jewels"""
        registry = JewelRegistry.from_build_xml(MIXED_JEWELS_XML)

        allocated_nodes = {1000, 2000, 2001, 2002, 3000, 5000}
        protected = registry.get_protected_nodes(allocated_nodes)

        # Timeless socket
        assert 1000 in protected
        # Cluster socket and nodes
        assert 2000 in protected
        assert 2001 in protected
        assert 2002 in protected
        # Unique socket
        assert 3000 in protected
        # Regular node should not be protected
        assert 5000 not in protected

    def test_no_jewels_in_xml(self):
        """Test handling XML with no jewels"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items></Items>
        </PathOfBuilding>
        """
        registry = JewelRegistry.from_build_xml(xml)

        assert registry.total_count == 0
        assert registry.get_protected_nodes({1, 2, 3}) == set()

    def test_jewel_without_socket(self):
        """Test handling jewel that isn't socketed"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">
                    Crimson Jewel
                    Fragility
                    Unique
                </Item>
            </Items>
        </PathOfBuilding>
        """
        registry = JewelRegistry.from_build_xml(xml)

        # Should still parse but have no socket
        assert len(registry.unique_jewels) == 1
        assert registry.unique_jewels[0].socket_node_id is None

    def test_protected_nodes_empty_allocated(self):
        """Test protected nodes with empty allocated set"""
        registry = JewelRegistry.from_build_xml(MIXED_JEWELS_XML)
        protected = registry.get_protected_nodes(set())

        # No nodes allocated means no nodes protected
        assert len(protected) == 0

    def test_cluster_jewel_id_detection(self):
        """Test that cluster nodes (ID >= 65536) are detected"""
        from src.pob.jewel.cluster import is_cluster_node_id

        assert is_cluster_node_id(65536) is True
        assert is_cluster_node_id(65537) is True
        assert is_cluster_node_id(100000) is True
        assert is_cluster_node_id(65535) is False
        assert is_cluster_node_id(1000) is False
        assert is_cluster_node_id(0) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

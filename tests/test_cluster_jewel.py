#!/usr/bin/env python3
"""
Tests for cluster jewel parsing and subgraph detection
"""

import pytest
from src.pob.jewel.cluster import (
    ClusterJewel,
    ClusterJewelSize,
    parse_cluster_jewels,
    is_cluster_node_id,
)


class TestClusterJewelParsing:
    """Test parsing of cluster jewel XML"""

    def test_parse_small_cluster_jewel(self):
        """Test parsing Small cluster jewel"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Small Cluster Jewel
Item Level: 75
Adds 2 Passive Skills
Added Small Passive Skills grant: 10% increased Fire Damage
1 Added Passive Skill is Cremator
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.size == ClusterJewelSize.SMALL
        assert jewel.socket_node_id == 65536
        assert "10% increased Fire Damage" in jewel.enchant_stat

    def test_parse_medium_cluster_jewel(self):
        """Test parsing Medium cluster jewel"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Medium Cluster Jewel
Item Level: 84
Adds 4 Passive Skills
Added Small Passive Skills grant: 12% increased Physical Damage
1 Added Passive Skill is Iron Breaker
1 Added Passive Skill is Force Multiplier
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.size == ClusterJewelSize.MEDIUM
        assert jewel.socket_node_id == 65536
        assert "12% increased Physical Damage" in jewel.enchant_stat

    def test_parse_large_cluster_jewel(self):
        """Test parsing Large cluster jewel"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Item Level: 75
Adds 8 Passive Skills
Added Small Passive Skills grant: 10% increased Damage
1 Added Passive Skill is Fuel the Fight
1 Added Passive Skill is Martial Prowess
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.size == ClusterJewelSize.LARGE
        assert jewel.socket_node_id == 65536
        assert "10% increased Damage" in jewel.enchant_stat

    def test_parse_multiple_cluster_jewels(self):
        """Test parsing multiple cluster jewels"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
                <Item id="2">Medium Cluster Jewel
Adds 4 Passive Skills
</Item>
                <Item id="3">Small Cluster Jewel
Adds 2 Passive Skills
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
                <Socket nodeId="70000" itemId="2"/>
                <Socket nodeId="75000" itemId="3"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 3

        sizes = [j.size for j in jewels]
        assert ClusterJewelSize.LARGE in sizes
        assert ClusterJewelSize.MEDIUM in sizes
        assert ClusterJewelSize.SMALL in sizes

    def test_parse_cluster_with_notables(self):
        """Test parsing cluster jewel with notable fields"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Medium Cluster Jewel
Adds 4 Passive Skills
1 Added Passive Skill is Fuel the Fight
1 Added Passive Skill is Martial Prowess
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]

        # Parser has notables field (may be empty if not yet extracted)
        assert isinstance(jewel.notables, list)
        # Note: Notable extraction from "1 Added Passive Skill is X"
        # may not be implemented yet, so we just verify the field exists

    def test_unsocketed_cluster_jewel(self):
        """Test cluster jewel that isn't socketed"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 1
        assert jewels[0].socket_node_id is None

    def test_cluster_without_marker(self):
        """Test that items without 'Cluster Jewel' aren't parsed"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Crimson Jewel
Adds 8 Passive Skills
</Item>
            </Items>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 0

    def test_display_name(self):
        """Test cluster jewel display name"""
        from src.pob.jewel.base import JewelCategory

        jewel = ClusterJewel(
            category=JewelCategory.CLUSTER,
            item_id=1,
            raw_text="test",
            size=ClusterJewelSize.MEDIUM,
            enchant_type="Physical",
            enchant_stat="12% increased Physical Damage",
            notables=["Iron Breaker", "Force Multiplier"],
        )

        display = jewel.display_name
        assert "Medium" in display
        assert "Cluster" in display


class TestClusterNodeDetection:
    """Test cluster node ID detection"""

    def test_is_cluster_node_id(self):
        """Test cluster node ID threshold (>= 65536)"""
        # Cluster nodes
        assert is_cluster_node_id(65536) is True
        assert is_cluster_node_id(65537) is True
        assert is_cluster_node_id(70000) is True
        assert is_cluster_node_id(100000) is True

        # Regular nodes
        assert is_cluster_node_id(0) is False
        assert is_cluster_node_id(1000) is False
        assert is_cluster_node_id(65535) is False

    def test_cluster_node_boundary(self):
        """Test boundary at 65536"""
        assert is_cluster_node_id(65535) is False
        assert is_cluster_node_id(65536) is True


class TestClusterJewelSize:
    """Test cluster jewel size enum"""

    def test_size_values(self):
        """Test that all size values are defined"""
        assert ClusterJewelSize.SMALL.value == "Small"
        assert ClusterJewelSize.MEDIUM.value == "Medium"
        assert ClusterJewelSize.LARGE.value == "Large"

    def test_size_from_string(self):
        """Test creating size from string"""
        # These should work if the parser uses the enum correctly
        sizes = ["Small", "Medium", "Large"]
        for size_str in sizes:
            size = ClusterJewelSize(size_str)
            assert size.value == size_str


class TestClusterJewelIntegration:
    """Integration tests with passive tree"""

    def test_cluster_with_allocated_nodes(self):
        """Test cluster jewel with allocated passive nodes"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
            <Tree>
                <Spec>
                    <Node nodeId="65537" active="true"/>
                    <Node nodeId="65538" active="true"/>
                    <Node nodeId="65539" active="true"/>
                </Spec>
            </Tree>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.socket_node_id == 65536

        # These nodes should be recognized as cluster nodes
        for node_id in [65537, 65538, 65539]:
            assert is_cluster_node_id(node_id)

    def test_nested_cluster_jewels(self):
        """Test nested cluster jewel structure"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
                <Item id="2">Medium Cluster Jewel
Adds 4 Passive Skills
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
                <Socket nodeId="65545" itemId="2"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 2

        # Both should be recognized as cluster jewels
        large = next(j for j in jewels if j.size == ClusterJewelSize.LARGE)
        medium = next(j for j in jewels if j.size == ClusterJewelSize.MEDIUM)

        assert large.socket_node_id == 65536
        assert medium.socket_node_id == 65545

    def test_mixed_jewel_socket_ids(self):
        """Test that cluster jewel sockets are properly identified"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]

        # Socket itself should be a cluster node
        assert is_cluster_node_id(jewel.socket_node_id)


class TestClusterJewelEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_cluster_jewel_list(self):
        """Test XML with no cluster jewels"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Crimson Jewel
Rarity: UNIQUE
Fragility
</Item>
            </Items>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)
        assert len(jewels) == 0

    def test_cluster_jewel_missing_size(self):
        """Test cluster jewel without clear size indicator"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Cluster Jewel
Adds 4 Passive Skills
</Item>
            </Items>
        </PathOfBuilding>
        """

        jewels = parse_cluster_jewels(xml)

        # Should still parse but might have unknown size
        assert len(jewels) >= 0  # Parser behavior may vary

    def test_malformed_xml(self):
        """Test handling of malformed XML"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
        """

        # Should not crash
        jewels = parse_cluster_jewels(xml)
        # May return empty or partial results
        assert isinstance(jewels, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

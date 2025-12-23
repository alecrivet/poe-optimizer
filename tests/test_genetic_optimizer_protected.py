#!/usr/bin/env python3
"""
Tests for genetic optimizer with protected nodes (jewel sockets, cluster nodes)
"""

import pytest
from pathlib import Path
from src.optimizer.genetic_optimizer import GeneticTreeOptimizer
from src.pob.jewel.registry import JewelRegistry


# Load the real build fixture
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "builds"
CYCLONE_BUILD_XML = (FIXTURES_DIR / "cyclone_slayer.xml").read_text()


class TestProtectedNodesBasics:
    """Test basic protected node functionality"""

    def test_protected_nodes_initialization(self):
        """Test that protected_nodes set is initialized"""
        optimizer = GeneticTreeOptimizer(
            population_size=10,
            generations=5,
            mutation_rate=0.1,
        )

        assert hasattr(optimizer, "protected_nodes")
        assert isinstance(optimizer.protected_nodes, set)
        assert len(optimizer.protected_nodes) == 0

    def test_protected_nodes_from_jewel_registry(self):
        """Test extracting protected nodes from jewel registry"""
        # XML with various jewel types
        xml = """<?xml version="1.0" encoding="UTF-8"?>
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
            </Items>
            <Tree>
                <Spec>
                    <Node nodeId="65537" active="true"/>
                    <Node nodeId="65538" active="true"/>
                </Spec>
            </Tree>
            <Sockets>
                <Socket nodeId="1000" itemId="1"/>
                <Socket nodeId="65536" itemId="2"/>
            </Sockets>
        </PathOfBuilding>
        """

        registry = JewelRegistry.from_build_xml(xml)
        allocated_nodes = {1000, 65536, 65537, 65538, 5000}
        protected = registry.get_protected_nodes(allocated_nodes)

        # Should protect jewel sockets and cluster nodes
        assert 1000 in protected  # Timeless socket
        assert 65536 in protected  # Cluster socket
        assert 65537 in protected  # Cluster node
        assert 65538 in protected  # Cluster node
        assert 5000 not in protected  # Regular node


class TestGeneticOptimizerWithProtection:
    """Test genetic optimizer respects protected nodes"""

    def test_mutation_respects_protected_nodes(self):
        """Test that mutation doesn't remove protected nodes"""
        from src.optimizer.genetic_optimizer import Individual

        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
            <Tree activeSpec="1">
                <Spec nodes="65536,65537,65538,1000,2000">
                    <Sockets>
                        <Socket nodeId="65536" itemId="1"/>
                    </Sockets>
                </Spec>
            </Tree>
        </PathOfBuilding>
        """

        optimizer = GeneticTreeOptimizer(population_size=5, generations=3)

        # Set protected nodes manually for testing
        optimizer.protected_nodes = {65536, 65537, 65538}

        # Create an individual with the XML
        individual = Individual(xml=xml, generation=0)

        # Simulate mutations multiple times
        for _ in range(10):
            mutated = optimizer._mutate(individual, objective='dps')
            mutated_nodes = mutated.get_allocated_nodes()

            # Protected nodes must still be present
            assert 65536 in mutated_nodes, "Cluster socket was removed!"
            assert 65537 in mutated_nodes, "Cluster node 65537 was removed!"
            assert 65538 in mutated_nodes, "Cluster node 65538 was removed!"

    def test_crossover_respects_protected_nodes(self):
        """Test that crossover maintains protected nodes"""
        from src.optimizer.genetic_optimizer import Individual
        from src.pob.modifier import modify_passive_tree_nodes

        optimizer = GeneticTreeOptimizer(population_size=5, generations=3)
        optimizer.protected_nodes = {65536, 65537, 65538}

        # Create base XML with protected nodes and some regular nodes
        xml_base = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
            <Tree activeSpec="1">
                <Spec nodes="65536,65537,65538,1000">
                    <Sockets>
                        <Socket nodeId="65536" itemId="1"/>
                    </Sockets>
                </Spec>
            </Tree>
        </PathOfBuilding>
        """

        # Create two parent individuals with protected nodes and different regular nodes
        parent1 = Individual(xml=xml_base, generation=0, fitness=1.0)
        parent2 = Individual(xml=xml_base, generation=0, fitness=1.0)

        # Do crossover multiple times
        for _ in range(10):
            child = optimizer._crossover(parent1, parent2, generation=1)
            child_nodes = child.get_allocated_nodes()

            # Protected nodes must be in child
            assert 65536 in child_nodes, "Protected node 65536 missing from child"
            assert 65537 in child_nodes, "Protected node 65537 missing from child"
            assert 65538 in child_nodes, "Protected node 65538 missing from child"

    def test_population_init_includes_protected_nodes(self):
        """Test that initial population includes protected nodes"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
            <Tree activeSpec="1">
                <Spec nodes="65536,65537,65538,1000">
                    <Sockets>
                        <Socket nodeId="65536" itemId="1"/>
                    </Sockets>
                </Spec>
            </Tree>
        </PathOfBuilding>
        """

        optimizer = GeneticTreeOptimizer(population_size=5, generations=3)
        optimizer.protected_nodes = {65536, 65537, 65538}

        original_nodes = {65536, 65537, 65538, 1000}

        # Generate initial population
        population = optimizer._initialize_population(xml, original_nodes, 'dps')

        # Every individual should have protected nodes
        for individual in population.individuals:
            individual_nodes = individual.get_allocated_nodes()
            assert 65536 in individual_nodes, "Protected node 65536 missing"
            assert 65537 in individual_nodes, "Protected node 65537 missing"
            assert 65538 in individual_nodes, "Protected node 65538 missing"


class TestRealBuildProtection:
    """Test protection with real Cyclone build"""

    def test_real_build_has_jewels(self):
        """Test that real build fixture has jewels"""
        registry = JewelRegistry.from_build_xml(CYCLONE_BUILD_XML)

        # Build should have some jewels
        total = registry.total_count
        assert total > 0, f"Build should have jewels, found {total}"

    def test_real_build_protected_nodes(self):
        """Test protected node extraction from real build"""
        from src.pob.modifier import get_passive_tree_summary

        # Get allocated nodes using the same parser the optimizer uses
        summary = get_passive_tree_summary(CYCLONE_BUILD_XML)
        allocated_nodes = set(summary['allocated_nodes'])

        # Get protected nodes
        registry = JewelRegistry.from_build_xml(CYCLONE_BUILD_XML)
        protected = registry.get_protected_nodes(allocated_nodes)

        # Should have some protected nodes (jewel sockets at minimum)
        assert len(protected) > 0, "Real build should have protected nodes"

        # All protected nodes should be allocated (this is a requirement of get_protected_nodes)
        for node_id in protected:
            assert node_id in allocated_nodes, \
                f"Protected node {node_id} not in allocated nodes"


class TestClusterNodeProtection:
    """Test protection of cluster jewel nodes"""

    def test_cluster_nodes_are_protected(self):
        """Test that cluster nodes (ID >= 65536) are protected when allocated"""
        from src.pob.jewel.cluster import is_cluster_node_id

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

        registry = JewelRegistry.from_build_xml(xml)
        allocated_nodes = {65536, 65537, 65538, 65539, 1000}
        protected = registry.get_protected_nodes(allocated_nodes)

        # All cluster nodes should be protected
        for node_id in [65536, 65537, 65538, 65539]:
            assert is_cluster_node_id(node_id)
            assert node_id in protected, \
                f"Cluster node {node_id} should be protected"

        # Regular node shouldn't be protected
        assert 1000 not in protected

    def test_unallocated_cluster_nodes_not_protected(self):
        """Test that unallocated cluster nodes are not protected"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
            <Tree>
                <Spec>
                    <Node nodeId="65537" active="false"/>
                </Spec>
            </Tree>
            <Sockets>
                <Socket nodeId="65536" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        registry = JewelRegistry.from_build_xml(xml)

        # Only socket allocated, not the cluster passive
        allocated_nodes = {65536}
        protected = registry.get_protected_nodes(allocated_nodes)

        # Socket is protected
        assert 65536 in protected

        # Unallocated cluster node is not protected
        assert 65537 not in protected


class TestTimelessJewelProtection:
    """Test protection of timeless jewel sockets"""

    def test_timeless_socket_protected(self):
        """Test that timeless jewel socket is protected"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Prismatic Jewel
Glorious Vanity
Timeless Jewel
Bathed in the blood of 5000 sacrificed in the name of Doryani
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="26725" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        registry = JewelRegistry.from_build_xml(xml)
        allocated_nodes = {26725, 1000, 2000}
        protected = registry.get_protected_nodes(allocated_nodes)

        # Timeless socket must be protected
        assert 26725 in protected
        assert len(protected) == 1  # Only the socket


class TestUniqueJewelProtection:
    """Test protection of unique jewel sockets"""

    def test_unique_socket_protected(self):
        """Test that unique jewel socket is protected"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Rarity: UNIQUE
Fragility
Crimson Jewel
-1 to Maximum Endurance Charges
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="12345" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        registry = JewelRegistry.from_build_xml(xml)
        allocated_nodes = {12345, 5000}
        protected = registry.get_protected_nodes(allocated_nodes)

        # Unique jewel socket must be protected
        assert 12345 in protected


class TestEdgeCases:
    """Test edge cases for protected nodes"""

    def test_empty_protected_set(self):
        """Test optimizer with no protected nodes"""
        from src.optimizer.genetic_optimizer import Individual

        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Tree>
                <Spec>
                    <Node nodeId="1000" active="true"/>
                    <Node nodeId="2000" active="true"/>
                </Spec>
            </Tree>
        </PathOfBuilding>
        """

        optimizer = GeneticTreeOptimizer(population_size=5, generations=3)
        optimizer.protected_nodes = set()

        individual = Individual(xml=xml, generation=0)
        mutated = optimizer._mutate(individual, objective='dps')

        # Should still work, just no protection
        assert isinstance(mutated, Individual)

    def test_all_nodes_protected(self):
        """Test when all nodes are protected"""
        from src.optimizer.genetic_optimizer import Individual

        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Large Cluster Jewel
Adds 8 Passive Skills
</Item>
            </Items>
            <Tree activeSpec="1">
                <Spec nodes="65536,65537,65538,1000">
                    <Sockets>
                        <Socket nodeId="65536" itemId="1"/>
                    </Sockets>
                </Spec>
            </Tree>
        </PathOfBuilding>
        """

        optimizer = GeneticTreeOptimizer(population_size=5, generations=3)
        optimizer.protected_nodes = {65536, 65537, 65538, 1000}

        individual = Individual(xml=xml, generation=0)

        # Mutation should preserve all nodes (or add new ones)
        mutated = optimizer._mutate(individual, objective='dps')
        mutated_nodes = mutated.get_allocated_nodes()

        # All protected nodes should be preserved
        assert 65536 in mutated_nodes
        assert 65537 in mutated_nodes
        assert 65538 in mutated_nodes
        assert 1000 in mutated_nodes

    def test_no_jewels_no_protection(self):
        """Test build with no jewels has no protected nodes"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items></Items>
            <Tree>
                <Spec>
                    <Node nodeId="1000" active="true"/>
                </Spec>
            </Tree>
        </PathOfBuilding>
        """

        registry = JewelRegistry.from_build_xml(xml)
        allocated_nodes = {1000, 2000}
        protected = registry.get_protected_nodes(allocated_nodes)

        assert len(protected) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Jewel Support Module

This module provides comprehensive support for Path of Exile jewels:
- Timeless Jewels: Transform passive nodes based on seed
- Cluster Jewels: Dynamically add nodes to the tree
- Unique Jewels: Special jewels with unique effects

Usage:
    from src.pob.jewel import JewelRegistry

    registry = JewelRegistry.from_build_xml(build_xml)
    protected_nodes = registry.get_protected_nodes()
    constraints = registry.get_jewel_constraints()
"""

from .base import JewelCategory, JewelSocket, BaseJewel
from .timeless import TimelessJewel, parse_timeless_jewels, get_timeless_jewel_modifiers
from .cluster import ClusterJewel, parse_cluster_jewels
from .unique import UniqueJewel, parse_unique_jewels
from .registry import JewelRegistry
from .cluster_subgraph import ClusterNode, ClusterSubgraph, ClusterSubgraphBuilder
from .cluster_optimizer import ClusterAllocation, ClusterNotableOptimizer

# Timeless jewel data and value calculation
from .timeless_data import (
    TimelessJewelDataLoader,
    TimelessNodeMod,
    TimelessTransformation,
    LegionPassive,
    get_default_loader,
)
from .timeless_value import (
    TimelessValueCalculator,
    TimelessSocketAnalysis,
    create_value_calculator,
)

__all__ = [
    # Base classes
    "JewelCategory",
    "JewelSocket",
    "BaseJewel",
    # Jewel types
    "TimelessJewel",
    "ClusterJewel",
    "UniqueJewel",
    # Parsing functions
    "parse_timeless_jewels",
    "parse_cluster_jewels",
    "parse_unique_jewels",
    "get_timeless_jewel_modifiers",
    # Registry
    "JewelRegistry",
    # Cluster subgraph modeling
    "ClusterNode",
    "ClusterSubgraph",
    "ClusterSubgraphBuilder",
    # Cluster optimization
    "ClusterAllocation",
    "ClusterNotableOptimizer",
    # Timeless jewel data
    "TimelessJewelDataLoader",
    "TimelessNodeMod",
    "TimelessTransformation",
    "LegionPassive",
    "get_default_loader",
    # Timeless jewel value calculation
    "TimelessValueCalculator",
    "TimelessSocketAnalysis",
    "create_value_calculator",
]

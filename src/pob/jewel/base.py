"""
Base Classes for Jewel Support

Provides common data structures and interfaces for all jewel types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from ..tree_parser import PassiveTreeGraph


class JewelCategory(Enum):
    """Categories of jewels in Path of Exile."""

    UNIQUE = "unique"  # Named unique jewels (178 types)
    TIMELESS = "timeless"  # Legion timeless jewels (5 types)
    CLUSTER = "cluster"  # Delirium cluster jewels (3 sizes)
    ABYSS = "abyss"  # Abyss jewels (4 types) - future
    RARE = "rare"  # Rare jewels - future


class JewelRadius(Enum):
    """Jewel radius sizes for affecting passive nodes."""

    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"

    @property
    def node_distance(self) -> int:
        """Approximate node distance for radius calculations."""
        return {
            JewelRadius.SMALL: 800,
            JewelRadius.MEDIUM: 1200,
            JewelRadius.LARGE: 1800,
        }[self]


@dataclass
class JewelSocket:
    """Represents a jewel socket on the passive tree."""

    node_id: int
    position_x: float = 0.0
    position_y: float = 0.0
    radius: Optional[JewelRadius] = JewelRadius.LARGE
    is_cluster_socket: bool = False
    is_abyss_socket: bool = False

    def get_nodes_in_radius(self, all_nodes: dict) -> Set[int]:
        """Get node IDs within this socket's radius."""
        if not self.radius:
            return set()

        in_radius = set()
        max_distance_sq = self.radius.node_distance ** 2

        for node_id, node in all_nodes.items():
            if hasattr(node, "x") and hasattr(node, "y"):
                dx = node.x - self.position_x
                dy = node.y - self.position_y
                if dx * dx + dy * dy <= max_distance_sq:
                    in_radius.add(node_id)

        return in_radius


@dataclass
class BaseJewel(ABC):
    """
    Abstract base class for all jewel types.

    All jewels share:
    - An item ID (from PoB XML)
    - An optional socket node ID (where socketed)
    - A category enum

    Subclasses must implement get_affected_nodes() to return
    which passive nodes are affected by this jewel.
    """

    category: JewelCategory
    item_id: int
    socket_node_id: Optional[int] = None
    raw_text: str = ""  # Original item text from XML

    @abstractmethod
    def get_affected_nodes(self, tree: "PassiveTreeGraph") -> Set[int]:
        """
        Return node IDs affected by this jewel.

        For radius jewels: nodes within radius
        For cluster jewels: generated subgraph nodes
        For simple jewels: empty set

        Args:
            tree: The passive tree graph

        Returns:
            Set of affected node IDs
        """
        pass

    @property
    def is_socketed(self) -> bool:
        """Check if jewel is socketed in the tree."""
        return self.socket_node_id is not None

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the jewel."""
        pass


@dataclass
class JewelModifier:
    """Represents a modifier applied by a jewel to a node."""

    node_id: int
    modifier_text: str
    modifier_value: Optional[float] = None
    is_replacement: bool = False  # True if replaces existing mod


# Jewel socket node IDs from the passive tree
# These are the outer jewel sockets that can hold cluster jewels
OUTER_JEWEL_SOCKETS = {
    2491, 6230, 7960, 12613, 26725, 33631,
    33989, 36634, 41263, 46519, 54127,
    60735, 61419, 61834,
}

def get_jewel_base_type(item_text: str) -> Optional[str]:
    """
    Extract the base type from jewel item text.

    Args:
        item_text: Raw item text from PoB XML

    Returns:
        Base type like "Cobalt Jewel", "Timeless Jewel", etc.
    """
    base_types = [
        "Cobalt Jewel",
        "Crimson Jewel",
        "Viridian Jewel",
        "Prismatic Jewel",
        "Timeless Jewel",
        "Small Cluster Jewel",
        "Medium Cluster Jewel",
        "Large Cluster Jewel",
        "Murderous Eye Jewel",
        "Searching Eye Jewel",
        "Hypnotic Eye Jewel",
        "Ghastly Eye Jewel",
    ]

    for base_type in base_types:
        if base_type in item_text:
            return base_type

    return None


def is_timeless_jewel(item_text: str) -> bool:
    """Check if item text describes a timeless jewel."""
    timeless_names = [
        "Glorious Vanity",
        "Lethal Pride",
        "Elegant Hubris",
        "Militant Faith",
        "Brutal Restraint",
    ]
    return any(name in item_text for name in timeless_names)


def is_cluster_jewel(item_text: str) -> bool:
    """Check if item text describes a cluster jewel."""
    return any(
        size in item_text
        for size in ["Small Cluster Jewel", "Medium Cluster Jewel", "Large Cluster Jewel"]
    )

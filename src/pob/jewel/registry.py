"""
Jewel Registry

Central registry for all jewels in a PoB build. Provides:
- Unified parsing of all jewel types
- Protected node calculation
- Constraint generation for optimizer
"""

from dataclasses import dataclass, field
from typing import List, Set, Optional, Iterator, TYPE_CHECKING

from .base import BaseJewel, JewelCategory
from .timeless import TimelessJewel, parse_timeless_jewels
from .cluster import ClusterJewel, parse_cluster_jewels, is_cluster_node_id
from .unique import UniqueJewel, parse_unique_jewels

if TYPE_CHECKING:
    from ..tree_parser import PassiveTreeGraph


@dataclass
class JewelConstraint:
    """Base class for jewel-related optimizer constraints."""

    socket_node_id: int
    description: str = ""


@dataclass
class TimelessJewelConstraint(JewelConstraint):
    """
    Constraint for timeless jewels.

    Timeless jewels transform nodes in their radius, so we should
    be careful about removing too many nodes from the radius.
    """

    min_affected_nodes: int = 3  # Keep at least N nodes in radius
    preserve_socket: bool = True  # Don't deallocate the socket


@dataclass
class ClusterJewelConstraint(JewelConstraint):
    """
    Constraint for cluster jewels.

    Cluster jewel nodes should be treated as immutable to avoid
    corrupting the subgraph structure.
    """

    preserve_subgraph: bool = True  # Don't touch cluster nodes
    generated_nodes: List[int] = field(default_factory=list)


@dataclass
class JewelRegistry:
    """
    Central registry for all jewels in a build.

    Usage:
        registry = JewelRegistry.from_build_xml(build_xml)
        protected = registry.get_protected_nodes()
        constraints = registry.get_jewel_constraints()
    """

    unique_jewels: List[UniqueJewel] = field(default_factory=list)
    timeless_jewels: List[TimelessJewel] = field(default_factory=list)
    cluster_jewels: List[ClusterJewel] = field(default_factory=list)

    @classmethod
    def from_build_xml(cls, build_xml: str) -> "JewelRegistry":
        """
        Parse all jewels from PoB build XML.

        Args:
            build_xml: Full PoB build XML string

        Returns:
            JewelRegistry with all parsed jewels
        """
        registry = cls()

        # Parse each jewel type
        registry.unique_jewels = parse_unique_jewels(build_xml)
        registry.timeless_jewels = parse_timeless_jewels(build_xml)
        registry.cluster_jewels = parse_cluster_jewels(build_xml)

        return registry

    @property
    def all_jewels(self) -> Iterator[BaseJewel]:
        """Iterate over all jewels in the registry."""
        yield from self.unique_jewels
        yield from self.timeless_jewels
        yield from self.cluster_jewels

    @property
    def total_count(self) -> int:
        """Total number of jewels."""
        return len(self.unique_jewels) + len(self.timeless_jewels) + len(self.cluster_jewels)

    @property
    def socketed_count(self) -> int:
        """Number of socketed jewels."""
        return sum(1 for j in self.all_jewels if j.is_socketed)

    def get_protected_nodes(self, allocated_nodes: Optional[Set[int]] = None) -> Set[int]:
        """
        Return all nodes that should not be modified by the optimizer.

        Protected nodes include:
        - All jewel socket nodes
        - All cluster jewel generated nodes
        - Optionally, nodes from allocated_nodes that are cluster nodes

        Args:
            allocated_nodes: Set of allocated node IDs (optional)

        Returns:
            Set of protected node IDs
        """
        protected = set()

        # Protect all jewel socket nodes
        for jewel in self.all_jewels:
            if jewel.socket_node_id:
                protected.add(jewel.socket_node_id)

        # Protect all cluster jewel generated nodes
        for cluster in self.cluster_jewels:
            protected.update(cluster.generated_nodes)

        # Also protect any cluster nodes from allocated_nodes
        if allocated_nodes:
            for node_id in allocated_nodes:
                if is_cluster_node_id(node_id):
                    protected.add(node_id)

        return protected

    def get_jewel_constraints(self) -> List[JewelConstraint]:
        """
        Generate optimizer constraints from jewels.

        Returns:
            List of JewelConstraint objects for the optimizer
        """
        constraints = []

        # Timeless jewel constraints
        for tj in self.timeless_jewels:
            if tj.socket_node_id:
                constraints.append(
                    TimelessJewelConstraint(
                        socket_node_id=tj.socket_node_id,
                        description=f"Timeless: {tj.display_name}",
                        min_affected_nodes=3,
                        preserve_socket=True,
                    )
                )

        # Cluster jewel constraints
        for cj in self.cluster_jewels:
            if cj.socket_node_id:
                constraints.append(
                    ClusterJewelConstraint(
                        socket_node_id=cj.socket_node_id,
                        description=f"Cluster: {cj.display_name}",
                        preserve_subgraph=True,
                        generated_nodes=list(cj.generated_nodes),
                    )
                )

        return constraints

    def get_jewel_at_socket(self, socket_node_id: int) -> Optional[BaseJewel]:
        """Get the jewel socketed at a specific node."""
        for jewel in self.all_jewels:
            if jewel.socket_node_id == socket_node_id:
                return jewel
        return None

    def has_timeless_jewels(self) -> bool:
        """Check if build has any timeless jewels."""
        return len(self.timeless_jewels) > 0

    def has_cluster_jewels(self) -> bool:
        """Check if build has any cluster jewels."""
        return len(self.cluster_jewels) > 0

    def get_summary(self) -> str:
        """Get a summary of jewels in the registry."""
        lines = [f"Jewel Registry: {self.total_count} jewels ({self.socketed_count} socketed)"]

        if self.timeless_jewels:
            lines.append(f"  Timeless: {len(self.timeless_jewels)}")
            for tj in self.timeless_jewels:
                lines.append(f"    - {tj.display_name}")

        if self.cluster_jewels:
            lines.append(f"  Cluster: {len(self.cluster_jewels)}")
            for cj in self.cluster_jewels:
                lines.append(f"    - {cj.display_name}")

        if self.unique_jewels:
            lines.append(f"  Unique: {len(self.unique_jewels)}")
            for uj in self.unique_jewels[:5]:  # Limit display
                lines.append(f"    - {uj.display_name}")
            if len(self.unique_jewels) > 5:
                lines.append(f"    ... and {len(self.unique_jewels) - 5} more")

        return "\n".join(lines)


# For testing
if __name__ == "__main__":
    # Test with build2.xml
    with open("examples/build2.xml", "r") as f:
        xml = f.read()

    registry = JewelRegistry.from_build_xml(xml)
    print(registry.get_summary())
    print()
    print(f"Protected nodes: {registry.get_protected_nodes()}")
    print()
    print(f"Constraints: {len(registry.get_jewel_constraints())}")

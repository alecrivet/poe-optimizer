"""
Constraint Handling for Tree Optimization

Implements various constraints that builds must satisfy:
- Point budget (min/max points allocated)
- Attribute requirements (STR/DEX/INT for gems)
- Jewel socket requirements (min jewel sockets)
"""

import logging
import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from ..pob.modifier import get_passive_tree_summary
from ..pob.xml_parser import parse_pob_stats as parse_pob_xml

logger = logging.getLogger(__name__)


@dataclass
class PointBudgetConstraint:
    """
    Constraint on total points allocated.

    Attributes:
        min_points: Minimum points required (optional)
        max_points: Maximum points allowed (based on character level)
    """
    min_points: Optional[int] = None
    max_points: Optional[int] = None

    def validate(self, xml: str) -> bool:
        """Check if build satisfies point budget."""
        summary = get_passive_tree_summary(xml)
        total_points = len(summary['allocated_nodes'])

        if self.min_points is not None and total_points < self.min_points:
            return False
        if self.max_points is not None and total_points > self.max_points:
            return False

        return True

    def get_violation_message(self, xml: str) -> Optional[str]:
        """Get human-readable violation message."""
        summary = get_passive_tree_summary(xml)
        total_points = len(summary['allocated_nodes'])

        if self.min_points is not None and total_points < self.min_points:
            return f"Too few points: {total_points} < {self.min_points}"
        if self.max_points is not None and total_points > self.max_points:
            return f"Too many points: {total_points} > {self.max_points}"

        return None

    def validate_node_count(self, count: int) -> bool:
        """Check if a node count satisfies the point budget (no XML parsing)."""
        if self.min_points is not None and count < self.min_points:
            return False
        if self.max_points is not None and count > self.max_points:
            return False
        return True

    def get_node_count_violation(self, count: int) -> Optional[str]:
        """Get violation message for a node count (no XML parsing)."""
        if self.min_points is not None and count < self.min_points:
            return f"Too few points: {count} < {self.min_points}"
        if self.max_points is not None and count > self.max_points:
            return f"Too many points: {count} > {self.max_points}"
        return None

    @staticmethod
    def from_level(level: int, min_offset: int = 0) -> 'PointBudgetConstraint':
        """
        Create constraint from character level.

        Character starts with ~20 points and gets 1 per level after 1.
        Also gets points from quests.

        Args:
            level: Character level (1-100)
            min_offset: Minimum points below max (e.g., -5 = allow 5 fewer)

        Returns:
            PointBudgetConstraint
        """
        # Formula: base (20) + levels (level - 1) + quests (22)
        # But typically simplified to: level + 21
        max_points = level + 21

        min_points = max_points + min_offset if min_offset < 0 else None

        return PointBudgetConstraint(
            min_points=min_points,
            max_points=max_points
        )


@dataclass
class AttributeConstraint:
    """
    Constraint on character attributes.

    Ensures character meets attribute requirements for gems.

    Attributes:
        min_str: Minimum strength required
        min_dex: Minimum dexterity required
        min_int: Minimum intelligence required
    """
    min_str: int = 0
    min_dex: int = 0
    min_int: int = 0

    def validate(self, xml: str) -> bool:
        """Check if build satisfies attribute requirements."""
        try:
            stats = parse_pob_xml(xml)

            str_value = stats.get('Str', 0)
            dex_value = stats.get('Dex', 0)
            int_value = stats.get('Int', 0)

            if str_value < self.min_str:
                return False
            if dex_value < self.min_dex:
                return False
            if int_value < self.min_int:
                return False

            return True
        except Exception as e:
            logger.debug(f"Could not validate attribute constraint: {e}")
            return True  # Default to allowing if we can't check

    def get_violation_message(self, xml: str) -> Optional[str]:
        """Get human-readable violation message."""
        try:
            stats = parse_pob_xml(xml)

            str_value = stats.get('Str', 0)
            dex_value = stats.get('Dex', 0)
            int_value = stats.get('Int', 0)

            violations = []

            if str_value < self.min_str:
                violations.append(f"STR: {str_value} < {self.min_str}")
            if dex_value < self.min_dex:
                violations.append(f"DEX: {dex_value} < {self.min_dex}")
            if int_value < self.min_int:
                violations.append(f"INT: {int_value} < {self.min_int}")

            if violations:
                return "Attribute requirements not met: " + ", ".join(violations)

            return None
        except Exception as e:
            logger.debug(f"Could not get attribute violation message: {e}")
            return None

    @staticmethod
    def from_gems(gem_requirements: List[Dict[str, int]]) -> 'AttributeConstraint':
        """
        Create constraint from gem requirements.

        Args:
            gem_requirements: List of dicts with keys 'str', 'dex', 'int'
                             Example: [{'str': 155, 'dex': 0, 'int': 0}]

        Returns:
            AttributeConstraint with max of all gem requirements
        """
        max_str = max((gem.get('str', 0) for gem in gem_requirements), default=0)
        max_dex = max((gem.get('dex', 0) for gem in gem_requirements), default=0)
        max_int = max((gem.get('int', 0) for gem in gem_requirements), default=0)

        return AttributeConstraint(
            min_str=max_str,
            min_dex=max_dex,
            min_int=max_int
        )


@dataclass
class JewelSocketConstraint:
    """
    Constraint on jewel sockets allocated.

    Important for cluster jewel builds.

    Attributes:
        min_sockets: Minimum jewel sockets required
        max_sockets: Maximum jewel sockets allowed (optional)
    """
    min_sockets: int = 0
    max_sockets: Optional[int] = None

    def validate(self, xml: str, tree_parser=None) -> bool:
        """Check if build satisfies jewel socket requirements."""
        summary = get_passive_tree_summary(xml)
        allocated_nodes = set(summary['allocated_nodes'])

        # Count jewel sockets
        jewel_count = 0

        if tree_parser:
            for node_id in allocated_nodes:
                node = tree_parser.get_node(node_id)
                if node and node.node_type == 'jewel':
                    jewel_count += 1
        else:
            # Fallback: assume we can't check without tree parser
            logger.debug("No tree parser provided, cannot validate jewel sockets")
            return True

        if jewel_count < self.min_sockets:
            return False
        if self.max_sockets is not None and jewel_count > self.max_sockets:
            return False

        return True

    def get_violation_message(self, xml: str, tree_parser=None) -> Optional[str]:
        """Get human-readable violation message."""
        summary = get_passive_tree_summary(xml)
        allocated_nodes = set(summary['allocated_nodes'])

        jewel_count = 0
        if tree_parser:
            for node_id in allocated_nodes:
                node = tree_parser.get_node(node_id)
                if node and node.node_type == 'jewel':
                    jewel_count += 1

        if jewel_count < self.min_sockets:
            return f"Not enough jewel sockets: {jewel_count} < {self.min_sockets}"
        if self.max_sockets is not None and jewel_count > self.max_sockets:
            return f"Too many jewel sockets: {jewel_count} > {self.max_sockets}"

        return None


@dataclass
class ConstraintSet:
    """
    Collection of all constraints.

    Attributes:
        point_budget: Point budget constraint
        attributes: Attribute constraints
        jewel_sockets: Jewel socket constraint
    """
    point_budget: Optional[PointBudgetConstraint] = None
    attributes: Optional[AttributeConstraint] = None
    jewel_sockets: Optional[JewelSocketConstraint] = None

    def validate_node_count(self, count: int) -> bool:
        """Check node count against point budget (no XML parsing)."""
        if self.point_budget:
            return self.point_budget.validate_node_count(count)
        return True

    def get_fitness_penalty(self, node_count: int) -> float:
        """
        Get fitness penalty for constraint violations.

        Returns 0.0 if within budget, -100 * excess_points if over budget.
        Used by genetic optimizer as a soft constraint.
        """
        if self.point_budget and self.point_budget.max_points is not None:
            excess = node_count - self.point_budget.max_points
            if excess > 0:
                return -100.0 * excess
        return 0.0

    def validate(self, xml: str, tree_parser=None) -> bool:
        """Check if build satisfies all constraints."""
        if self.point_budget and not self.point_budget.validate(xml):
            return False

        if self.attributes and not self.attributes.validate(xml):
            return False

        if self.jewel_sockets and not self.jewel_sockets.validate(xml, tree_parser):
            return False

        return True

    def get_violations(self, xml: str, tree_parser=None) -> List[str]:
        """Get list of constraint violations."""
        violations = []

        if self.point_budget:
            msg = self.point_budget.get_violation_message(xml)
            if msg:
                violations.append(msg)

        if self.attributes:
            msg = self.attributes.get_violation_message(xml)
            if msg:
                violations.append(msg)

        if self.jewel_sockets:
            msg = self.jewel_sockets.get_violation_message(xml, tree_parser)
            if msg:
                violations.append(msg)

        return violations

    def __repr__(self) -> str:
        parts = []

        if self.point_budget:
            parts.append(f"Points: {self.point_budget.min_points}-{self.point_budget.max_points}")

        if self.attributes and (self.attributes.min_str or self.attributes.min_dex or self.attributes.min_int):
            attr_parts = []
            if self.attributes.min_str:
                attr_parts.append(f"STR>={self.attributes.min_str}")
            if self.attributes.min_dex:
                attr_parts.append(f"DEX>={self.attributes.min_dex}")
            if self.attributes.min_int:
                attr_parts.append(f"INT>={self.attributes.min_int}")
            parts.append(f"Attributes: {', '.join(attr_parts)}")

        if self.jewel_sockets and self.jewel_sockets.min_sockets:
            parts.append(f"Jewel Sockets: >= {self.jewel_sockets.min_sockets}")

        if not parts:
            return "ConstraintSet(no constraints)"

        return f"ConstraintSet({'; '.join(parts)})"


def create_standard_constraints(
    level: int = 95,
    gem_requirements: Optional[List[Dict[str, int]]] = None,
    min_jewel_sockets: int = 0,
) -> ConstraintSet:
    """
    Create standard constraint set for a build.

    Args:
        level: Character level (determines max points)
        gem_requirements: List of gem attribute requirements
        min_jewel_sockets: Minimum jewel sockets required

    Returns:
        ConstraintSet with standard constraints
    """
    constraints = ConstraintSet(
        point_budget=PointBudgetConstraint.from_level(level, min_offset=-5),
    )

    if gem_requirements:
        constraints.attributes = AttributeConstraint.from_gems(gem_requirements)

    if min_jewel_sockets > 0:
        constraints.jewel_sockets = JewelSocketConstraint(min_sockets=min_jewel_sockets)

    return constraints


def auto_constraints_from_xml(xml: str) -> Optional[ConstraintSet]:
    """
    Auto-create constraints by extracting character level from build XML.

    Parses <Build level="X"> to determine point budget. Does NOT create
    AttributeConstraint (reads stale XML stats) or JewelSocketConstraint
    (requires tree_parser).

    Args:
        xml: PoB build XML string

    Returns:
        ConstraintSet with point budget, or None if level cannot be determined
    """
    match = re.search(r'<Build\s[^>]*level="(\d+)"', xml)
    if not match:
        logger.debug("Could not extract character level from build XML")
        return None

    level = int(match.group(1))
    if level < 1 or level > 100:
        logger.warning(f"Invalid character level: {level}")
        return None

    logger.info(f"Auto-detected character level {level}, max points = {level + 21}")
    return ConstraintSet(
        point_budget=PointBudgetConstraint.from_level(level, min_offset=-5)
    )

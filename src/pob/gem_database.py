"""
Gem Database - Parse PoB Gems.lua into a queryable database.

Parses PathOfBuilding/src/Data/Gems.lua to extract gem metadata
including support gem classification, awakened status, and tag info.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GemClassification(str, Enum):
    """Classification of support gems by their behavior."""
    PURE_SUPPORT = "pure_support"           # Normal supports (Brutality, etc.)
    DAMAGE_DEALING_SUPPORT = "damage_dealing"  # Grants own active skill (Shockwave, etc.)
    TRIGGER_SUPPORT = "trigger"             # Triggers other skills (CoC, CwC, etc.)


@dataclass
class GemInfo:
    """Metadata for a single gem parsed from Gems.lua."""
    name: str
    game_id: str           # XML gemId (e.g., "Metadata/Items/Gems/SupportGemBrutality")
    variant_id: str        # XML variantId (e.g., "SupportBrutality")
    granted_effect_id: str  # XML skillId (e.g., "SupportBrutality")
    is_support: bool
    is_awakened: bool
    tags: List[str]
    max_level: int         # 20 for normal, 5 for awakened
    classification: GemClassification = GemClassification.PURE_SUPPORT
    secondary_granted_effect_id: Optional[str] = None


class GemDatabase:
    """Queryable database of gems parsed from PoB data."""

    def __init__(self, gems: Dict[str, GemInfo]):
        self._gems = gems  # keyed by name
        self._by_game_id: Dict[str, GemInfo] = {}
        for gem in gems.values():
            self._by_game_id[gem.game_id] = gem

    @classmethod
    def from_pob_data(cls, pob_path: Optional[str] = None) -> "GemDatabase":
        """
        Parse Gems.lua and build a GemDatabase.

        Args:
            pob_path: Path to PathOfBuilding directory.
                      Defaults to ./PathOfBuilding relative to project root.

        Returns:
            GemDatabase instance
        """
        if pob_path is None:
            # Try common locations
            candidates = [
                os.path.join(os.path.dirname(__file__), "..", "..", "PathOfBuilding"),
                "PathOfBuilding",
            ]
            for candidate in candidates:
                gems_path = os.path.join(candidate, "src", "Data", "Gems.lua")
                if os.path.exists(gems_path):
                    pob_path = candidate
                    break
            if pob_path is None:
                raise FileNotFoundError(
                    "PathOfBuilding directory not found. "
                    "Pass pob_path explicitly or ensure PathOfBuilding/ exists."
                )

        gems_path = os.path.join(pob_path, "src", "Data", "Gems.lua")
        if not os.path.exists(gems_path):
            raise FileNotFoundError(f"Gems.lua not found at: {gems_path}")

        logger.info(f"Parsing gems from: {gems_path}")
        gems = _parse_gems_lua(gems_path)
        logger.info(f"Loaded {len(gems)} gems ({sum(1 for g in gems.values() if g.is_support)} supports)")
        return cls(gems)

    def get_all_supports(self) -> List[GemInfo]:
        """Get all support gems (including awakened)."""
        return [g for g in self._gems.values() if g.is_support]

    def get_damage_dealing_supports(self) -> List[GemInfo]:
        """Get support gems that deal their own damage (e.g. Shockwave)."""
        return [
            g for g in self._gems.values()
            if g.is_support and g.classification == GemClassification.DAMAGE_DEALING_SUPPORT
        ]

    def is_damage_dealing(self, name: str) -> bool:
        """Check if a gem name is a damage-dealing support."""
        gem = self._gems.get(name)
        return (
            gem is not None
            and gem.is_support
            and gem.classification == GemClassification.DAMAGE_DEALING_SUPPORT
        )

    def get_support_by_name(self, name: str) -> Optional[GemInfo]:
        """Look up a support gem by its display name."""
        gem = self._gems.get(name)
        if gem and gem.is_support:
            return gem
        return None

    def get_gem_by_name(self, name: str) -> Optional[GemInfo]:
        """Look up any gem by its display name."""
        return self._gems.get(name)

    def get_gem_by_game_id(self, game_id: str) -> Optional[GemInfo]:
        """Look up a gem by its gameId (XML gemId attribute)."""
        return self._by_game_id.get(game_id)

    def __len__(self) -> int:
        return len(self._gems)


def _parse_gems_lua(path: str) -> Dict[str, GemInfo]:
    """
    Parse Gems.lua file using regex to extract gem entries.

    The file has entries like:
        ["Metadata/Items/Gems/SkillGemFireball"] = {
            name = "Fireball",
            gameId = "Metadata/Items/Gems/SkillGemFireball",
            variantId = "Fireball",
            grantedEffectId = "Fireball",
            tags = { intelligence = true, spell = true, ... },
            naturalMaxLevel = 20,
        },
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    gems: Dict[str, GemInfo] = {}

    # Split into gem blocks. Each starts with ["Metadata/..."] = {
    # and ends with the next entry or file end.
    block_pattern = re.compile(
        r'\["Metadata/Items/Gems/[^"]+"\]\s*=\s*\{(.*?)\n\t\}',
        re.DOTALL,
    )

    for match in block_pattern.finditer(content):
        block = match.group(1)

        name = _extract_string(block, "name")
        if not name:
            continue

        game_id = _extract_string(block, "gameId") or ""
        variant_id = _extract_string(block, "variantId") or ""
        granted_effect_id = _extract_string(block, "grantedEffectId") or ""

        # Extract tags block
        tags = _extract_tags(block)

        is_support = "support" in tags
        is_awakened = "awakened" in tags

        # secondaryGrantedEffectId
        secondary_granted_effect_id = _extract_string(block, "secondaryGrantedEffectId")

        # Classify support gems
        classification = GemClassification.PURE_SUPPORT
        if is_support:
            has_trigger = "trigger" in tags
            has_grants_active = "grants_active_skill" in tags
            has_secondary = secondary_granted_effect_id is not None

            if has_grants_active and not has_trigger:
                # Supports that grant their own active skill (Shockwave, Predator)
                classification = GemClassification.DAMAGE_DEALING_SUPPORT
            elif has_trigger:
                # Trigger supports (CoC, CwC, Cast on Death, etc.)
                classification = GemClassification.TRIGGER_SUPPORT
            elif has_secondary and not has_grants_active:
                # Has secondary effect but no active skill tag (Guardian's Blessing)
                classification = GemClassification.PURE_SUPPORT

        # naturalMaxLevel
        max_level_match = re.search(r'naturalMaxLevel\s*=\s*(\d+)', block)
        max_level = int(max_level_match.group(1)) if max_level_match else 20

        gem = GemInfo(
            name=name,
            game_id=game_id,
            variant_id=variant_id,
            granted_effect_id=granted_effect_id,
            is_support=is_support,
            is_awakened=is_awakened,
            tags=tags,
            max_level=max_level,
            classification=classification,
            secondary_granted_effect_id=secondary_granted_effect_id,
        )

        # Use name as key; skip duplicates (first wins)
        if name not in gems:
            gems[name] = gem
        else:
            logger.debug(f"Duplicate gem name '{name}', keeping first")

    return gems


def _extract_string(block: str, field: str) -> Optional[str]:
    """Extract a string field value from a Lua block."""
    match = re.search(rf'{field}\s*=\s*"([^"]*)"', block)
    return match.group(1) if match else None


def _extract_tags(block: str) -> List[str]:
    """Extract tag names from a tags = { ... } block."""
    tags_match = re.search(r'tags\s*=\s*\{(.*?)\}', block, re.DOTALL)
    if not tags_match:
        return []
    tags_block = tags_match.group(1)
    return re.findall(r'(\w+)\s*=\s*true', tags_block)

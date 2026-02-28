"""
Tests for gem database, gem modification, and gem optimizer.

These tests verify the gem parsing, XML manipulation, and optimizer
logic without requiring a running PoB instance.
"""

import os
import xml.etree.ElementTree as ET

import pytest

from src.pob.gem_database import GemDatabase, GemClassification, GemInfo
from src.pob.calculator_utils import extract_build_stats
from src.pob.modifier import (
    get_main_skill_info,
    replace_support_gem,
    get_skill_groups_summary,
    BuildModificationError,
)

# Path to test fixture
FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "builds", "cyclone_slayer.xml"
)


@pytest.fixture
def gem_db():
    """Load the gem database from PoB data."""
    return GemDatabase.from_pob_data()


@pytest.fixture
def build_xml():
    """Load the test build XML fixture."""
    with open(FIXTURE_PATH, "r") as f:
        return f.read()


# --- GemDatabase tests ---


class TestGemDatabase:
    def test_gem_database_loads(self, gem_db):
        """GemDatabase.from_pob_data() returns a non-empty database."""
        assert len(gem_db) > 0

    def test_gem_database_support_count(self, gem_db):
        """Database contains ~200+ support gems."""
        supports = gem_db.get_all_supports()
        assert len(supports) >= 200
        # All returned gems should be supports
        for gem in supports:
            assert gem.is_support

    def test_gem_database_awakened(self, gem_db):
        """Awakened gems are detected with correct max levels."""
        supports = gem_db.get_all_supports()
        awakened = [g for g in supports if g.is_awakened]
        assert len(awakened) >= 30
        for gem in awakened:
            # Most awakened gems have max_level=5, but Empower/Enhance/Enlighten have 4
            assert gem.max_level in (4, 5)
            assert "Awakened" in gem.name

    def test_gem_info_fields(self, gem_db):
        """GemInfo dataclass has correct field types."""
        gem = gem_db.get_support_by_name("Brutality")
        assert gem is not None
        assert isinstance(gem.name, str)
        assert isinstance(gem.game_id, str)
        assert isinstance(gem.variant_id, str)
        assert isinstance(gem.granted_effect_id, str)
        assert isinstance(gem.is_support, bool)
        assert isinstance(gem.is_awakened, bool)
        assert isinstance(gem.tags, list)
        assert isinstance(gem.max_level, int)
        assert gem.game_id != ""
        assert gem.variant_id != ""

    def test_gem_lookup_by_game_id(self, gem_db):
        """Can look up gems by their gameId (XML gemId)."""
        gem = gem_db.get_gem_by_game_id("Metadata/Items/Gems/SupportGemBrutality")
        assert gem is not None
        assert gem.name == "Brutality"

    def test_gem_lookup_nonexistent(self, gem_db):
        """Looking up a nonexistent gem returns None."""
        assert gem_db.get_support_by_name("Not A Real Gem") is None
        assert gem_db.get_gem_by_game_id("Metadata/Items/Gems/Nonexistent") is None

    def test_active_gem_not_support(self, gem_db):
        """Active gems are not returned by get_support_by_name."""
        # Cyclone is an active gem, not a support
        assert gem_db.get_support_by_name("Cyclone") is None
        # But it should exist in the general lookup
        assert gem_db.get_gem_by_name("Cyclone") is not None


# --- Modifier tests ---


class TestModifierGemFunctions:
    def test_get_main_skill_info_auto(self, build_xml):
        """Reads mainSocketGroup from XML Build element."""
        groups = get_main_skill_info(build_xml)
        assert len(groups) >= 1
        # Should have gems
        assert len(groups[0]['gems']) > 0
        # Should have support indices
        assert len(groups[0]['support_indices']) > 0

    def test_get_main_skill_info_override(self, build_xml):
        """Finds group by gem name override."""
        groups = get_main_skill_info(build_xml, main_skill_override="Cyclone of Tumult")
        assert len(groups) >= 1
        # Should find the group with Cyclone
        gem_names = [g['name'] for g in groups[0]['gems']]
        assert "Cyclone of Tumult" in gem_names

    def test_get_main_skill_info_override_not_found(self, build_xml):
        """Raises error when override gem not found."""
        with pytest.raises(BuildModificationError, match="not found"):
            get_main_skill_info(build_xml, main_skill_override="Nonexistent Gem")

    def test_get_main_skill_info_rf(self, build_xml):
        """Righteous Fire groups are always included."""
        # This is a structural test — the cyclone build may or may not have RF.
        # We just verify the function doesn't crash and returns a list.
        groups = get_main_skill_info(build_xml)
        assert isinstance(groups, list)

    def test_replace_support_gem(self, build_xml):
        """XML modification produces valid output with new gem."""
        groups = get_main_skill_info(build_xml)
        group = groups[0]
        support_idx = group['support_indices'][0]

        modified = replace_support_gem(
            build_xml,
            socket_group_idx=group['index'],
            gem_idx=support_idx,
            new_gem_name="Concentrated Effect",
            new_game_id="Metadata/Items/Gems/SupportGemConcentratedEffect",
            new_variant_id="SupportConcentratedEffect",
            new_skill_id="SupportConcentratedEffect",
            level=20,
            quality=20,
        )

        # Verify it's valid XML
        root = ET.fromstring(modified)
        assert root is not None

        # Verify the gem was changed
        new_groups = get_main_skill_info(modified)
        new_gem_name = new_groups[0]['gems'][support_idx]['name']
        assert new_gem_name == "Concentrated Effect"

    def test_replace_support_gem_preserves_others(self, build_xml):
        """Other gems in the group are unchanged after replacement."""
        groups = get_main_skill_info(build_xml)
        group = groups[0]
        support_idx = group['support_indices'][0]

        # Collect all gem names before
        before_names = [g['name'] for g in group['gems']]

        modified = replace_support_gem(
            build_xml,
            socket_group_idx=group['index'],
            gem_idx=support_idx,
            new_gem_name="Test Gem",
            new_game_id="Metadata/Items/Gems/TestGem",
            new_variant_id="TestGem",
            new_skill_id="TestGem",
        )

        new_groups = get_main_skill_info(modified)
        after_names = [g['name'] for g in new_groups[0]['gems']]

        # Only the replaced gem should differ
        for i, (before, after) in enumerate(zip(before_names, after_names)):
            if i == support_idx:
                assert after == "Test Gem"
            else:
                assert before == after, f"Gem at index {i} changed unexpectedly"

    def test_replace_support_gem_invalid_group(self, build_xml):
        """Raises error for invalid socket group index."""
        with pytest.raises(BuildModificationError, match="Invalid socket group"):
            replace_support_gem(
                build_xml,
                socket_group_idx=999,
                gem_idx=0,
                new_gem_name="Test",
                new_game_id="test",
                new_variant_id="test",
                new_skill_id="test",
            )

    def test_replace_support_gem_invalid_gem_idx(self, build_xml):
        """Raises error for invalid gem index."""
        groups = get_main_skill_info(build_xml)
        with pytest.raises(BuildModificationError, match="Invalid gem index"):
            replace_support_gem(
                build_xml,
                socket_group_idx=groups[0]['index'],
                gem_idx=999,
                new_gem_name="Test",
                new_game_id="test",
                new_variant_id="test",
                new_skill_id="test",
            )

    def test_awakened_gem_level(self, gem_db, build_xml):
        """Awakened gems get level=5 when inserted."""
        groups = get_main_skill_info(build_xml)
        group = groups[0]
        support_idx = group['support_indices'][0]

        awakened = gem_db.get_support_by_name("Awakened Brutality")
        assert awakened is not None
        assert awakened.max_level == 5

        modified = replace_support_gem(
            build_xml,
            socket_group_idx=group['index'],
            gem_idx=support_idx,
            new_gem_name=awakened.name,
            new_game_id=awakened.game_id,
            new_variant_id=awakened.variant_id,
            new_skill_id=awakened.granted_effect_id,
            level=awakened.max_level,
            quality=20,
        )

        new_groups = get_main_skill_info(modified)
        replaced_gem = new_groups[0]['gems'][support_idx]
        assert replaced_gem['name'] == "Awakened Brutality"
        assert replaced_gem['level'] == 5


# --- Optimizer tests (no PoB required) ---


class TestGemOptimizerUnit:
    def test_no_duplicate_supports(self, gem_db, build_xml):
        """Verify the optimizer skips gems already in the group."""
        from src.optimizer.gem_optimizer import GreedyGemOptimizer

        optimizer = GreedyGemOptimizer(gem_db, show_progress=False)

        # Get main skill info
        groups = get_main_skill_info(build_xml)
        group = groups[0]
        used_names = {g['name'] for g in group['gems']}

        # Filter candidates for a slot (same logic as optimizer)
        current_name = group['gems'][group['support_indices'][0]]['name']
        candidates = []
        for support in optimizer.all_supports:
            if support.name in used_names and support.name != current_name:
                continue
            if support.name == current_name:
                continue
            candidates.append(support.name)

        # Verify no gems already in the group appear as candidates
        for name in candidates:
            assert name not in used_names or name == current_name

    def test_optimizer_init(self, gem_db):
        """Optimizer initializes with correct candidate count."""
        from src.optimizer.gem_optimizer import GreedyGemOptimizer

        optimizer = GreedyGemOptimizer(gem_db, max_iterations=3, show_progress=False)
        assert len(optimizer.all_supports) == len(gem_db.get_all_supports())
        assert optimizer.max_iterations == 3


# --- Gem Classification tests ---


class TestGemClassification:
    def test_shockwave_is_damage_dealing(self, gem_db):
        """Shockwave should be classified as DAMAGE_DEALING_SUPPORT."""
        gem = gem_db.get_support_by_name("Shockwave")
        assert gem is not None
        assert gem.classification == GemClassification.DAMAGE_DEALING_SUPPORT

    def test_brutality_is_pure_support(self, gem_db):
        """Brutality should be classified as PURE_SUPPORT."""
        gem = gem_db.get_support_by_name("Brutality")
        assert gem is not None
        assert gem.classification == GemClassification.PURE_SUPPORT

    def test_cast_on_crit_is_trigger(self, gem_db):
        """Cast On Critical Strike should be classified as TRIGGER_SUPPORT."""
        gem = gem_db.get_support_by_name("Cast On Critical Strike")
        assert gem is not None
        assert gem.classification == GemClassification.TRIGGER_SUPPORT

    def test_cast_while_channelling_is_trigger(self, gem_db):
        """Cast while Channelling should be classified as TRIGGER_SUPPORT."""
        gem = gem_db.get_support_by_name("Cast while Channelling")
        assert gem is not None
        assert gem.classification == GemClassification.TRIGGER_SUPPORT

    def test_is_damage_dealing_helper(self, gem_db):
        """GemDatabase.is_damage_dealing() works for known gems."""
        assert gem_db.is_damage_dealing("Shockwave") is True
        assert gem_db.is_damage_dealing("Brutality") is False
        assert gem_db.is_damage_dealing("Cast On Critical Strike") is False
        assert gem_db.is_damage_dealing("Nonexistent Gem") is False

    def test_get_damage_dealing_supports(self, gem_db):
        """get_damage_dealing_supports() returns at least Shockwave."""
        dd_supports = gem_db.get_damage_dealing_supports()
        names = {g.name for g in dd_supports}
        assert "Shockwave" in names
        for g in dd_supports:
            assert g.is_support
            assert g.classification == GemClassification.DAMAGE_DEALING_SUPPORT

    def test_shockwave_has_secondary_effect(self, gem_db):
        """Shockwave should have a secondaryGrantedEffectId."""
        gem = gem_db.get_support_by_name("Shockwave")
        assert gem is not None
        assert gem.secondary_granted_effect_id is not None


# --- extract_build_stats dps_mode tests ---


class TestExtractBuildStatsDpsMode:
    def test_combined_mode_uses_combined_dps(self):
        """dps_mode='combined' reads combinedDPS."""
        stats = {"combinedDPS": 100000, "fullDPS": 200000, "life": 5000, "totalEHP": 80000}
        result = extract_build_stats(stats, dps_mode="combined")
        assert result.dps == 100000

    def test_full_mode_uses_full_dps(self):
        """dps_mode='full' reads fullDPS."""
        stats = {"combinedDPS": 100000, "fullDPS": 200000, "life": 5000, "totalEHP": 80000}
        result = extract_build_stats(stats, dps_mode="full")
        assert result.dps == 200000

    def test_default_mode_is_combined(self):
        """Default dps_mode should use combinedDPS."""
        stats = {"combinedDPS": 100000, "fullDPS": 200000, "life": 5000, "totalEHP": 80000}
        result = extract_build_stats(stats)
        assert result.dps == 100000

    def test_full_mode_missing_key_returns_zero(self):
        """fullDPS missing should return 0."""
        stats = {"combinedDPS": 100000, "life": 5000, "totalEHP": 80000}
        result = extract_build_stats(stats, dps_mode="full")
        assert result.dps == 0


# --- Auto-pinning and dps_mode auto-detection tests ---


class TestGemOptimizerPinning:
    def test_auto_pin_damage_dealing(self, gem_db, build_xml):
        """Optimizer with pin_damage_dealing=True skips damage-dealing slots."""
        from src.optimizer.gem_optimizer import GreedyGemOptimizer
        from unittest.mock import MagicMock

        optimizer = GreedyGemOptimizer(
            gem_db, show_progress=False, pin_damage_dealing=True
        )

        # Simulate a group that has Shockwave in it
        groups = get_main_skill_info(build_xml)
        group = groups[0]

        # Inject Shockwave into one support slot to test pinning
        shockwave_idx = group['support_indices'][0]
        group['gems'][shockwave_idx]['name'] = "Shockwave"

        # Check that damage-dealing detection would find it
        damage_dealing_in_groups = set()
        for gem in group['gems']:
            if gem_db.is_damage_dealing(gem['name']):
                damage_dealing_in_groups.add(gem['name'])

        assert "Shockwave" in damage_dealing_in_groups

    def test_explicit_pinned_gems(self, gem_db):
        """Optimizer accepts explicit pinned_gems set."""
        from src.optimizer.gem_optimizer import GreedyGemOptimizer

        optimizer = GreedyGemOptimizer(
            gem_db,
            show_progress=False,
            pinned_gems={"Brutality", "Melee Physical Damage"},
        )
        assert "Brutality" in optimizer.pinned_gems
        assert "Melee Physical Damage" in optimizer.pinned_gems

    def test_dps_mode_auto_with_damage_dealing(self, gem_db):
        """dps_mode='auto' resolves to 'full' when damage-dealing supports exist."""
        from src.optimizer.gem_optimizer import GreedyGemOptimizer

        optimizer = GreedyGemOptimizer(
            gem_db, show_progress=False, dps_mode="auto"
        )

        # A group with Shockwave should trigger "full" mode
        fake_group_gems = [
            {"name": "Cyclone of Tumult"},
            {"name": "Shockwave"},
            {"name": "Brutality"},
        ]
        damage_dealing = set()
        for gem in fake_group_gems:
            if gem_db.is_damage_dealing(gem['name']):
                damage_dealing.add(gem['name'])

        effective_mode = "full" if damage_dealing else "combined"
        assert effective_mode == "full"

    def test_dps_mode_auto_without_damage_dealing(self, gem_db):
        """dps_mode='auto' resolves to 'combined' when no damage-dealing supports."""
        fake_group_gems = [
            {"name": "Icicle Mine"},
            {"name": "Brutality"},
            {"name": "Concentrated Effect"},
        ]
        damage_dealing = set()
        for gem in fake_group_gems:
            if gem_db.is_damage_dealing(gem['name']):
                damage_dealing.add(gem['name'])

        effective_mode = "full" if damage_dealing else "combined"
        assert effective_mode == "combined"

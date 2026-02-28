"""
Tests for BuildContext extraction module.

Tests build context extraction from PoB XML including:
1. Class and ascendancy detection
2. Damage type analysis
3. Defense style detection
4. Keystone detection
5. Keyword weight generation
"""

import pytest
from pathlib import Path

from src.pob.build_context import (
    BuildContext,
    BuildContextExtractor,
    extract_build_context,
    KEYSTONE_NAMES,
)
from src.pob.tree_version import get_latest_tree_version


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "builds"


@pytest.fixture
def cyclone_slayer_xml():
    """Load cyclone slayer build XML fixture."""
    xml_file = FIXTURES_DIR / "cyclone_slayer.xml"
    if not xml_file.exists():
        pytest.skip(f"Test fixture not found: {xml_file}")
    return xml_file.read_text()


class TestBuildContextBasic:
    """Test basic BuildContext functionality."""

    def test_default_context(self):
        """Test default BuildContext values."""
        ctx = BuildContext()

        assert ctx.primary_damage_type == "physical"
        assert ctx.secondary_damage_types == set()
        assert ctx.damage_style == "hit"
        assert ctx.attack_or_spell == "attack"
        assert ctx.defense_style == "life"
        assert ctx.primary_mitigation == "armor"
        assert ctx.character_class == "Unknown"
        assert ctx.ascendancy == "None"
        assert ctx.key_mechanics == set()
        assert ctx.key_keystones == set()

    def test_is_crit_build(self):
        """Test crit build detection."""
        ctx = BuildContext()
        assert ctx.is_crit_build() is True

        ctx_rt = BuildContext(key_keystones={"resolute_technique"})
        assert ctx_rt.is_crit_build() is False

    def test_is_dot_build(self):
        """Test DoT build detection."""
        ctx_hit = BuildContext(damage_style="hit")
        assert ctx_hit.is_dot_build() is False

        ctx_dot = BuildContext(damage_style="dot")
        assert ctx_dot.is_dot_build() is True

    def test_is_minion_build(self):
        """Test minion build detection."""
        ctx_hit = BuildContext(damage_style="hit")
        assert ctx_hit.is_minion_build() is False

        ctx_minion = BuildContext(damage_style="minion")
        assert ctx_minion.is_minion_build() is True

        ctx_mechanic = BuildContext(key_mechanics={"minions"})
        assert ctx_mechanic.is_minion_build() is True


class TestKeywordWeights:
    """Test keyword weight generation."""

    def test_dps_keywords_physical_attack(self):
        """Test DPS keyword weights for physical attack build."""
        ctx = BuildContext(
            primary_damage_type="physical",
            attack_or_spell="attack",
            damage_style="hit",
        )

        weights = ctx.get_relevant_keywords("dps")

        # Primary damage type should be weighted high
        assert weights["physical"] == 1.5
        # Other damage types should be weighted low
        assert weights["fire"] == 0.5
        assert weights["cold"] == 0.5
        # Attack should be weighted high
        assert weights["attack"] == 1.5
        assert weights["spell"] == 0.3
        # DPS keywords should be present
        assert weights["damage"] >= 1.3
        assert weights["critical strike"] >= 1.2

    def test_dps_keywords_fire_spell(self):
        """Test DPS keyword weights for fire spell build."""
        ctx = BuildContext(
            primary_damage_type="fire",
            secondary_damage_types={"lightning"},
            attack_or_spell="spell",
            damage_style="hit",
        )

        weights = ctx.get_relevant_keywords("dps")

        # Primary and secondary damage types
        assert weights["fire"] == 1.5
        assert weights["lightning"] == 1.2
        assert weights["physical"] == 0.5
        # Spell weighted high
        assert weights["spell"] == 1.5
        assert weights["attack"] == 0.3
        assert weights["cast speed"] == 1.3

    def test_life_keywords(self):
        """Test life-focused keyword weights."""
        ctx = BuildContext(defense_style="life")

        weights = ctx.get_relevant_keywords("life")

        assert weights["maximum life"] == 1.5
        assert weights["life"] == 1.5
        assert weights["life regeneration"] >= 1.3

    def test_ehp_keywords(self):
        """Test EHP-focused keyword weights."""
        ctx = BuildContext(
            defense_style="life",
            primary_mitigation="armor",
        )

        weights = ctx.get_relevant_keywords("ehp")

        assert weights["armor"] >= 1.2
        assert weights["armour"] >= 1.2
        assert weights["physical damage reduction"] >= 1.3

    def test_balanced_keywords(self):
        """Test balanced keyword weights."""
        ctx = BuildContext()

        weights = ctx.get_relevant_keywords("balanced")

        # Should have reduced weights for all categories
        assert "damage" in weights
        assert "maximum life" in weights
        assert "armour" in weights

    def test_keystone_adjustments_resolute_technique(self):
        """Test RT keystone disables crit weights."""
        ctx = BuildContext(key_keystones={"resolute_technique"})

        weights = ctx.get_relevant_keywords("dps")

        assert weights["critical"] == 0.1
        assert weights["crit"] == 0.1

    def test_keystone_adjustments_ci(self):
        """Test CI keystone adjusts life/ES weights."""
        ctx = BuildContext(key_keystones={"ci"})

        weights = ctx.get_relevant_keywords("dps")

        assert weights["life"] == 0.1
        assert weights["energy shield"] == 1.5
        assert weights["es"] == 1.5

    def test_keystone_adjustments_acrobatics(self):
        """Test acrobatics adjusts armor/evasion weights."""
        ctx = BuildContext(key_keystones={"acrobatics"})

        weights = ctx.get_relevant_keywords("dps")

        assert weights["evasion"] == 1.3
        assert weights["dodge"] == 1.3
        assert weights["armor"] == 0.5

    def test_dot_build_keywords(self):
        """Test DoT build keyword weights."""
        ctx = BuildContext(
            primary_damage_type="physical",
            damage_style="dot",
        )

        weights = ctx.get_relevant_keywords("dps")

        assert weights["damage over time"] == 1.5
        assert weights["bleed"] == 1.5
        assert weights["bleeding"] == 1.5

    def test_minion_build_keywords(self):
        """Test minion build keyword weights."""
        ctx = BuildContext(damage_style="minion")

        weights = ctx.get_relevant_keywords("dps")

        assert weights["minion"] == 1.5
        assert weights["minions"] == 1.5

    def test_mechanic_keywords(self):
        """Test mechanic-based keyword weights."""
        ctx = BuildContext(key_mechanics={"totems", "brands"})

        weights = ctx.get_relevant_keywords("dps")

        assert weights["totems"] == 1.5
        assert weights["totem"] == 1.5
        assert weights["brands"] == 1.5
        assert weights["brand"] == 1.5


class TestBuildContextExtraction:
    """Test BuildContext extraction from XML."""

    def test_from_build_xml_cyclone_slayer(self, cyclone_slayer_xml):
        """Test extraction from cyclone slayer build."""
        ctx = BuildContext.from_build_xml(cyclone_slayer_xml)

        # Class and ascendancy
        assert ctx.character_class == "Duelist"
        assert ctx.ascendancy == "Slayer"

        # Damage characteristics - Cyclone with Brutality is physical
        assert ctx.primary_damage_type == "physical"
        assert ctx.attack_or_spell == "attack"

        # Defense - build has life, armor, and block
        assert ctx.defense_style == "life"

        # Build has high block
        assert ctx.primary_mitigation == "block"

    def test_convenience_function(self, cyclone_slayer_xml):
        """Test the extract_build_context convenience function."""
        ctx = extract_build_context(cyclone_slayer_xml)

        assert ctx.character_class == "Duelist"
        assert ctx.ascendancy == "Slayer"

    def test_invalid_xml_returns_default(self):
        """Test that invalid XML returns default context."""
        ctx = BuildContext.from_build_xml("not valid xml")

        assert ctx.character_class == "Unknown"
        assert ctx.ascendancy == "None"


class TestBuildContextExtractorMethods:
    """Test individual BuildContextExtractor methods."""

    def test_parse_ascendancy(self, cyclone_slayer_xml):
        """Test ascendancy parsing."""
        import xml.etree.ElementTree as ET

        extractor = BuildContextExtractor()
        root = ET.fromstring(cyclone_slayer_xml)

        char_class, ascendancy = extractor._parse_ascendancy(root)

        assert char_class == "Duelist"
        assert ascendancy == "Slayer"

    def test_analyze_skills(self, cyclone_slayer_xml):
        """Test skill analysis."""
        import xml.etree.ElementTree as ET

        extractor = BuildContextExtractor()
        root = ET.fromstring(cyclone_slayer_xml)

        analysis = extractor._analyze_skills(root)

        # Should detect attack build from Cyclone + support gems
        assert analysis["is_attack"] is True
        # Should detect physical damage from Brutality
        assert "physical" in analysis["damage_types"]
        # Should have found active gems
        assert len(analysis["active_gems"]) > 0

    def test_analyze_defenses(self, cyclone_slayer_xml):
        """Test defense analysis."""
        import xml.etree.ElementTree as ET

        extractor = BuildContextExtractor()
        root = ET.fromstring(cyclone_slayer_xml)

        # Need keystones for defense analysis
        keystones = extractor._analyze_keystones(root)
        defense = extractor._analyze_defenses(root, keystones)

        # Cyclone slayer is a life build with high block
        assert defense["style"] == "life"
        assert defense["mitigation"] == "block"  # 65% block in build

    def test_determine_damage_types_single(self):
        """Test damage type determination with single type."""
        extractor = BuildContextExtractor()

        analysis = {"damage_types": {"physical"}, "is_attack": True}
        primary, secondary = extractor._determine_damage_types(analysis)

        assert primary == "physical"
        assert secondary == set()

    def test_determine_damage_types_multiple(self):
        """Test damage type determination with multiple types."""
        extractor = BuildContextExtractor()

        analysis = {"damage_types": {"fire", "lightning"}, "is_spell": True}
        primary, secondary = extractor._determine_damage_types(analysis)

        # For spells, lightning has priority over fire
        assert primary == "lightning"
        assert secondary == {"fire"}

    def test_determine_attack_or_spell(self):
        """Test attack/spell determination."""
        extractor = BuildContextExtractor()

        assert extractor._determine_attack_or_spell({"is_attack": True, "is_spell": False}) == "attack"
        assert extractor._determine_attack_or_spell({"is_attack": False, "is_spell": True}) == "spell"
        assert extractor._determine_attack_or_spell({"is_attack": True, "is_spell": True}) == "both"
        assert extractor._determine_attack_or_spell({"is_attack": False, "is_spell": False}) == "attack"  # default

    def test_determine_damage_style(self):
        """Test damage style determination."""
        extractor = BuildContextExtractor()

        # Minion style
        assert extractor._determine_damage_style({"is_minion": True}, set()) == "minion"
        assert extractor._determine_damage_style({"is_minion": False}, {"necromantic_aegis"}) == "minion"

        # DoT style
        assert extractor._determine_damage_style({"is_dot": True, "is_minion": False}, set()) == "dot"
        assert extractor._determine_damage_style({"is_dot": False, "is_minion": False}, {"crimson_dance"}) == "dot"

        # Hit style (default)
        assert extractor._determine_damage_style({"is_dot": False, "is_minion": False}, set()) == "hit"


class TestKeystoneLoading:
    """Test keystone ID loading from PathOfBuilding data."""

    def test_keystone_names_defined(self):
        """Test that important keystones are defined."""
        important_keystones = [
            "Resolute Technique",
            "Chaos Inoculation",
            "Mind Over Matter",
            "Acrobatics",
            "Iron Reflexes",
            "Ancestral Bond",
        ]

        for keystone in important_keystones:
            assert keystone in KEYSTONE_NAMES, f"Missing keystone: {keystone}"

    def test_load_keystone_ids(self):
        """Test loading keystone IDs from tree data."""
        extractor = BuildContextExtractor()
        keystone_ids = extractor._load_keystone_ids()

        # Should have loaded some keystones (if PathOfBuilding is present)
        tree_version = get_latest_tree_version()
        if tree_version and Path(f"./PathOfBuilding/src/TreeData/{tree_version}/tree.lua").exists():
            assert len(keystone_ids) > 0
            # Check that values are valid keystone identifiers
            for node_id, keystone_name in keystone_ids.items():
                assert isinstance(node_id, int)
                assert keystone_name in KEYSTONE_NAMES.values()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_skills_section(self):
        """Test build with empty skills section."""
        xml = """<?xml version="1.0"?>
        <PathOfBuilding>
            <Build className="Witch" ascendClassName="Necromancer" level="90"/>
            <Skills/>
            <Tree><Spec nodes=""/></Tree>
        </PathOfBuilding>
        """

        ctx = BuildContext.from_build_xml(xml)

        assert ctx.character_class == "Witch"
        assert ctx.ascendancy == "Necromancer"
        # Default values when no skills
        assert ctx.primary_damage_type == "physical"

    def test_missing_tree_section(self):
        """Test build without tree section."""
        xml = """<?xml version="1.0"?>
        <PathOfBuilding>
            <Build className="Marauder" ascendClassName="Berserker" level="90"/>
            <Skills/>
        </PathOfBuilding>
        """

        ctx = BuildContext.from_build_xml(xml)

        assert ctx.character_class == "Marauder"
        assert ctx.key_keystones == set()

    def test_missing_build_element(self):
        """Test XML without Build element."""
        xml = """<?xml version="1.0"?>
        <PathOfBuilding>
            <Skills/>
        </PathOfBuilding>
        """

        ctx = BuildContext.from_build_xml(xml)

        assert ctx.character_class == "Unknown"
        assert ctx.ascendancy == "None"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

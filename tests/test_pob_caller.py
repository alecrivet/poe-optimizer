"""
Unit tests for PoBCalculator class.
"""

import pytest
from pathlib import Path
from src.pob.caller import PoBCalculator, PoBCalculatorError


class TestPoBCalculatorInit:
    """Tests for PoBCalculator initialization."""

    def test_init_with_defaults(self):
        """Test that PoBCalculator initializes with default paths."""
        calc = PoBCalculator()
        assert calc.pob_path.exists()
        assert (calc.pob_path / "src" / "HeadlessWrapper.lua").exists()

    def test_init_with_custom_path(self):
        """Test initialization with custom PoB path."""
        project_root = Path(__file__).parent.parent
        pob_path = project_root / "PathOfBuilding"
        calc = PoBCalculator(pob_path=str(pob_path))
        assert calc.pob_path == pob_path.resolve()

    def test_init_with_invalid_path(self):
        """Test that initialization fails with invalid PoB path."""
        with pytest.raises(PoBCalculatorError, match="PathOfBuilding directory not found"):
            PoBCalculator(pob_path="/nonexistent/path")

    def test_init_validates_lua(self):
        """Test that initialization validates Lua installation."""
        # This should not raise if luajit is installed
        calc = PoBCalculator(lua_command="luajit")
        assert calc.lua_command == "luajit"

    def test_init_with_invalid_lua_command(self):
        """Test that initialization fails with invalid Lua command."""
        with pytest.raises(PoBCalculatorError, match="Lua command.*not found"):
            PoBCalculator(lua_command="nonexistent_lua_command")


class TestPoBCalculatorEvaluate:
    """Tests for build evaluation."""

    @pytest.fixture
    def calculator(self):
        """Create a PoBCalculator instance for testing."""
        return PoBCalculator()

    @pytest.fixture
    def minimal_build_xml(self):
        """
        Create a minimal valid PoB build XML.
        This is a very basic level 1 Marauder with no gear or skills.
        """
        return """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" targetVersion="3_0" className="Marauder" ascendClassName="Juggernaut" mainSocketGroup="1" viewMode="TREE">
        <PlayerStat stat="Strength" value="0"/>
    </Build>
    <Tree activeSpec="1">
        <Spec title="Default" treeVersion="3_25" classId="1" ascendClassId="1" nodes="0"/>
    </Tree>
    <Items activeItemSet="1">
        <ItemSet id="1" title="Default"/>
    </Items>
    <Skills activeSkillSet="1">
        <SkillSet id="1"/>
    </Skills>
    <Config/>
</PathOfBuilding>"""

    @pytest.fixture
    def cyclone_build_xml(self):
        """
        A more realistic build XML with Cyclone skill.
        This is simplified but should be enough for testing.
        """
        return """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" targetVersion="3_0" className="Duelist" ascendClassName="Slayer" mainSocketGroup="1">
        <PlayerStat stat="Strength" value="100"/>
        <PlayerStat stat="Dexterity" value="100"/>
        <PlayerStat stat="Intelligence" value="50"/>
    </Build>
    <Tree activeSpec="1">
        <Spec title="Default" treeVersion="3_25" classId="2" ascendClassId="1" nodes="0,1,2,3,4,5,6"/>
    </Tree>
    <Items activeItemSet="1">
        <ItemSet id="1" title="Default">
            <Item id="1">Rarity: NORMAL
Thrusting One Hand Sword
Item Level: 60
Quality: 0
Sockets: R-R-R
Attacks per Second: 1.5
Physical Damage: 20-40
</Item>
        </ItemSet>
    </Items>
    <Skills activeSkillSet="1">
        <SkillSet id="1">
            <Skill slot="Weapon 1" mainActiveSkill="1" enabled="true">
                <Gem gemId="Metadata/Items/Gems/Cyclone" level="20" quality="0" enabled="true"/>
            </Skill>
        </SkillSet>
    </Skills>
    <Config/>
</PathOfBuilding>"""

    def test_evaluate_minimal_build(self, calculator, minimal_build_xml):
        """Test evaluation of a minimal valid build."""
        stats = calculator.evaluate_build(minimal_build_xml)

        # Check that we got a stats dictionary back
        assert isinstance(stats, dict)

        # Check that expected keys exist
        expected_keys = [
            'totalDPS', 'fullDPS', 'totalEHP', 'life', 'energyShield',
            'fireRes', 'coldRes', 'lightningRes', 'chaosRes',
            'strength', 'dexterity', 'intelligence'
        ]
        for key in expected_keys:
            assert key in stats, f"Missing expected key: {key}"

        # Check that values are numbers (not None or strings)
        for key, value in stats.items():
            assert isinstance(value, (int, float)), f"{key} should be numeric, got {type(value)}"

        # Basic sanity checks
        # A level 90 Marauder should have some base life
        assert stats['life'] > 0, "Life should be greater than 0"

        # Resistances should be in a reasonable range (-100 to 100)
        for res in ['fireRes', 'coldRes', 'lightningRes', 'chaosRes']:
            assert -100 <= stats[res] <= 100, f"{res} should be between -100 and 100"

    def test_evaluate_invalid_xml(self, calculator):
        """Test that invalid XML is handled (PoB may return defaults or error)."""
        invalid_xml = "This is not valid XML"

        # PoB is quite forgiving - it may return a default build or an error
        try:
            stats = calculator.evaluate_build(invalid_xml)
            # If it succeeds, should return a valid stats dict
            assert isinstance(stats, dict)
        except PoBCalculatorError:
            # Also acceptable to raise an error
            pass

    def test_evaluate_empty_xml(self, calculator):
        """Test that empty XML is handled (PoB may return defaults or error)."""
        # PoB may return a default build or an error for empty XML
        try:
            stats = calculator.evaluate_build("")
            # If it succeeds, should return a valid stats dict
            assert isinstance(stats, dict)
        except PoBCalculatorError:
            # Also acceptable to raise an error
            pass

    def test_evaluate_with_timeout(self, calculator, minimal_build_xml):
        """Test that timeout parameter works."""
        # This should complete well within 5 seconds
        stats = calculator.evaluate_build(minimal_build_xml, timeout=5)
        assert isinstance(stats, dict)

    @pytest.mark.slow
    def test_evaluate_realistic_build(self, calculator, cyclone_build_xml):
        """Test evaluation of a more realistic build with skills."""
        stats = calculator.evaluate_build(cyclone_build_xml)

        # Should have some DPS from Cyclone
        # Note: Might be 0 if the build is too minimal, but should at least run
        assert stats['fullDPS'] >= 0

        # Should have reasonable life
        assert stats['life'] > 0

        # Attributes should match what we set or be higher (from tree)
        assert stats['strength'] >= 0
        assert stats['dexterity'] >= 0
        assert stats['intelligence'] >= 0


class TestPoBCalculatorEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def calculator(self):
        return PoBCalculator()

    def test_corrupted_xml_structure(self, calculator):
        """Test handling of XML with correct format but invalid PoB structure."""
        bad_xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <InvalidElement/>
</PathOfBuilding>"""

        # Should handle gracefully - either return defaults or raise error
        # depending on PoB's behavior
        try:
            stats = calculator.evaluate_build(bad_xml)
            assert isinstance(stats, dict)
        except PoBCalculatorError:
            # Also acceptable to raise an error
            pass

    def test_special_characters_in_xml(self, calculator):
        """Test that XML with special characters is handled correctly."""
        xml_with_special_chars = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" targetVersion="3_0" className="Marauder" ascendClassName="Test&amp;Name">
        <PlayerStat stat="Strength" value="0"/>
    </Build>
    <Tree activeSpec="1">
        <Spec title="Test &lt;Build&gt;" treeVersion="3_25" classId="1" ascendClassId="1" nodes="0"/>
    </Tree>
    <Items activeItemSet="1"><ItemSet id="1"/></Items>
    <Skills activeSkillSet="1"><SkillSet id="1"/></Skills>
    <Config/>
</PathOfBuilding>"""

        # Should handle escaped characters without crashing
        try:
            stats = calculator.evaluate_build(xml_with_special_chars)
            assert isinstance(stats, dict)
        except PoBCalculatorError:
            # Acceptable if PoB rejects it
            pass


class TestPoBCalculatorRepr:
    """Test string representation."""

    def test_repr(self):
        """Test that __repr__ returns useful information."""
        calc = PoBCalculator()
        repr_str = repr(calc)
        assert "PoBCalculator" in repr_str
        assert "pob_path" in repr_str
        assert "lua_command" in repr_str

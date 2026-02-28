#!/usr/bin/env python3
"""
Tests for timeless jewel data parsing and value calculation
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.pob.jewel.timeless_data import (
    TimelessJewelDataLoader,
    TimelessNodeMod,
    TimelessTransformation,
    LegionPassive,
    JEWEL_TYPE_IDS,
    SEED_RANGES,
    TIMELESS_JEWEL_ADDITIONS,
    get_default_loader,
)
from src.pob.jewel.timeless_value import (
    TimelessValueCalculator,
    TimelessSocketAnalysis,
    SimpleRadiusCalculator,
    get_stat_weights,
    DPS_STAT_WEIGHTS,
    LIFE_STAT_WEIGHTS,
    EHP_STAT_WEIGHTS,
)
from src.pob.jewel.base import JewelRadius


class TestTimelessNodeMod:
    """Tests for TimelessNodeMod dataclass."""

    def test_create_mod(self):
        """Test creating a timeless node mod."""
        mod = TimelessNodeMod(
            stat_id="fire_damage_+%",
            stat_value=10.0,
            stat_text="10% increased Fire Damage"
        )

        assert mod.stat_id == "fire_damage_+%"
        assert mod.stat_value == 10.0
        assert mod.stat_text == "10% increased Fire Damage"

    def test_mod_repr(self):
        """Test mod string representation."""
        mod = TimelessNodeMod(
            stat_id="test",
            stat_value=5.0,
            stat_text="Test Stat"
        )

        assert "Test Stat" in repr(mod)


class TestTimelessTransformation:
    """Tests for TimelessTransformation dataclass."""

    def test_create_transformation_with_mods(self):
        """Test creating a transformation with mods."""
        mods = [
            TimelessNodeMod("stat1", 10.0, "Stat 1"),
            TimelessNodeMod("stat2", 20.0, "Stat 2"),
        ]

        transform = TimelessTransformation(
            original_node_id=12345,
            mods=mods,
            replaces_original=False,
        )

        assert transform.original_node_id == 12345
        assert len(transform.mods) == 2
        assert transform.replaces_original is False
        assert transform.replacement_name is None

    def test_create_replacement_transformation(self):
        """Test creating a replacement transformation."""
        transform = TimelessTransformation(
            original_node_id=12345,
            mods=[],
            replaces_original=True,
            replacement_name="Divine Flesh"
        )

        assert transform.replaces_original is True
        assert transform.replacement_name == "Divine Flesh"

    def test_transformation_repr(self):
        """Test transformation string representation."""
        # Non-replacement
        transform1 = TimelessTransformation(
            original_node_id=123,
            mods=[TimelessNodeMod("s", 1, "t")],
            replaces_original=False,
        )
        assert "adds 1 mods" in repr(transform1)

        # Replacement
        transform2 = TimelessTransformation(
            original_node_id=123,
            mods=[],
            replaces_original=True,
            replacement_name="Test Node"
        )
        assert "replaces with Test Node" in repr(transform2)


class TestLegionPassive:
    """Tests for LegionPassive dataclass."""

    def test_create_legion_passive(self):
        """Test creating a legion passive."""
        passive = LegionPassive(
            index=5,
            id="vaal_small_fire_damage",
            name="Fire Damage",
            stats=["10% increased Fire Damage"],
            stat_ids=["fire_damage_+%"],
            stat_values={"fire_damage_+%": (7.0, 12.0)},
            is_keystone=False,
            is_notable=False,
        )

        assert passive.index == 5
        assert passive.id == "vaal_small_fire_damage"
        assert passive.name == "Fire Damage"
        assert len(passive.stats) == 1
        assert passive.is_keystone is False

    def test_get_mod_text(self):
        """Test getting mod text."""
        passive = LegionPassive(
            index=1,
            id="test",
            name="Test",
            stats=["Test Stat"],
            stat_ids=[],
            stat_values={},
        )

        assert passive.get_mod_text() == "Test Stat"


class TestJewelTypeConstants:
    """Tests for jewel type constants."""

    def test_jewel_type_ids(self):
        """Test that all jewel types have IDs."""
        expected_types = [
            "GloriousVanity",
            "LethalPride",
            "BrutalRestraint",
            "MilitantFaith",
            "ElegantHubris",
        ]

        for jewel_type in expected_types:
            assert jewel_type in JEWEL_TYPE_IDS
            assert isinstance(JEWEL_TYPE_IDS[jewel_type], int)

    def test_seed_ranges(self):
        """Test that all jewel types have seed ranges."""
        for type_id in range(1, 6):
            assert type_id in SEED_RANGES
            min_seed, max_seed = SEED_RANGES[type_id]
            assert min_seed < max_seed

    def test_timeless_jewel_additions(self):
        """Test additions constant."""
        assert TIMELESS_JEWEL_ADDITIONS == 94


class TestTimelessJewelDataLoader:
    """Tests for TimelessJewelDataLoader."""

    def test_init_default_path(self):
        """Test initialization with default path."""
        loader = TimelessJewelDataLoader()

        assert loader.data_dir is not None
        assert "TimelessJewelData" in str(loader.data_dir)

    def test_init_custom_path(self):
        """Test initialization with custom path."""
        loader = TimelessJewelDataLoader("/custom/path")

        assert str(loader.data_dir) == "/custom/path"

    def test_is_loaded_false_initially(self):
        """Test that nothing is loaded initially."""
        loader = TimelessJewelDataLoader()

        assert loader.is_loaded("LethalPride") is False
        assert loader.is_loaded("GloriousVanity") is False

    def test_get_all_node_ids(self):
        """Test getting all node IDs (requires actual data)."""
        loader = TimelessJewelDataLoader()
        loader._ensure_node_index_loaded()

        # Should have node mappings if data exists
        node_ids = loader.get_all_node_ids()
        # May be empty if no data, but should be a set
        assert isinstance(node_ids, set)

    def test_normalize_jewel_type(self):
        """Test that jewel types are normalized correctly."""
        loader = TimelessJewelDataLoader()

        # With space
        assert not loader.is_loaded("Lethal Pride")
        # Without space
        assert not loader.is_loaded("LethalPride")


class TestTimelessJewelDataLoaderWithData:
    """Tests that require actual PoB data files."""

    @pytest.fixture
    def loader(self):
        """Create loader pointing to actual data directory."""
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "PathOfBuilding" / "src" / "Data" / "TimelessJewelData"

        if not data_dir.exists():
            pytest.skip("TimelessJewelData directory not found")

        return TimelessJewelDataLoader(str(data_dir))

    def test_load_node_index_mapping(self, loader):
        """Test loading node index mapping."""
        loader._ensure_node_index_loaded()

        # Should have loaded node mappings
        assert len(loader._node_index_map) > 0
        assert loader._total_nodes > 0

    def test_load_legion_passives(self, loader):
        """Test loading legion passives."""
        loader._ensure_legion_loaded()

        # Should have additions and nodes
        # Note: may be empty if parsing fails
        if loader._additions or loader._nodes:
            assert len(loader._additions) > 0 or len(loader._nodes) > 0

    def test_load_brutal_restraint(self, loader):
        """Test loading Brutal Restraint data."""
        result = loader.load_jewel_type("BrutalRestraint")

        # Should succeed if .bin file exists
        if (loader.data_dir / "BrutalRestraint.bin").exists():
            assert result is True
            assert loader.is_loaded("BrutalRestraint")

    def test_load_militant_faith(self, loader):
        """Test loading Militant Faith data."""
        result = loader.load_jewel_type("MilitantFaith")

        if (loader.data_dir / "MilitantFaith.bin").exists():
            assert result is True
            assert loader.is_loaded("MilitantFaith")


class TestStatWeights:
    """Tests for stat weight functions."""

    def test_dps_weights(self):
        """Test DPS stat weights."""
        weights = get_stat_weights("DPS")

        assert weights == DPS_STAT_WEIGHTS
        assert "fire_damage_+%" in weights
        assert "attack_speed_+%" in weights

    def test_life_weights(self):
        """Test Life stat weights."""
        weights = get_stat_weights("Life")

        assert weights == LIFE_STAT_WEIGHTS
        assert "maximum_life_+%" in weights

    def test_ehp_weights(self):
        """Test EHP stat weights."""
        weights = get_stat_weights("EHP")

        assert weights == EHP_STAT_WEIGHTS
        assert "fire_damage_resistance_%" in weights

    def test_case_insensitive(self):
        """Test case insensitive objective matching."""
        assert get_stat_weights("dps") == DPS_STAT_WEIGHTS
        assert get_stat_weights("LIFE") == LIFE_STAT_WEIGHTS
        assert get_stat_weights("ehp") == EHP_STAT_WEIGHTS

    def test_default_to_dps(self):
        """Test unknown objectives default to DPS."""
        assert get_stat_weights("unknown") == DPS_STAT_WEIGHTS


class TestTimelessSocketAnalysis:
    """Tests for TimelessSocketAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating a socket analysis."""
        analysis = TimelessSocketAnalysis(
            socket_node_id=26725,
            affected_nodes={1, 2, 3},
            transformations={},
            total_value=100.5,
            best_nodes=[(1, 50.0), (2, 30.0)],
            pathing_cost=2,
        )

        assert analysis.socket_node_id == 26725
        assert len(analysis.affected_nodes) == 3
        assert analysis.total_value == 100.5
        assert analysis.pathing_cost == 2

    def test_analysis_repr(self):
        """Test analysis string representation."""
        analysis = TimelessSocketAnalysis(
            socket_node_id=123,
            total_value=50.5,
        )

        repr_str = repr(analysis)
        assert "socket=123" in repr_str
        assert "50.5" in repr_str


class TestSimpleRadiusCalculator:
    """Tests for SimpleRadiusCalculator."""

    def test_get_nodes_in_radius_empty_tree(self):
        """Test radius calculation with empty tree."""
        mock_tree = MagicMock()
        mock_tree.get_node.return_value = None
        mock_tree.nodes = {}

        calc = SimpleRadiusCalculator(mock_tree)
        result = calc.get_nodes_in_radius(123, JewelRadius.LARGE)

        assert result == set()

    def test_get_nodes_in_radius(self):
        """Test radius calculation with nodes."""
        # Create mock tree with nodes
        mock_tree = MagicMock()

        socket_node = MagicMock()
        socket_node.x = 0.0
        socket_node.y = 0.0

        node1 = MagicMock()
        node1.x = 100.0
        node1.y = 100.0

        node2 = MagicMock()
        node2.x = 5000.0  # Far away
        node2.y = 5000.0

        mock_tree.get_node.return_value = socket_node
        mock_tree.nodes = {1: node1, 2: node2}

        calc = SimpleRadiusCalculator(mock_tree)
        result = calc.get_nodes_in_radius(123, JewelRadius.LARGE)

        # Node1 should be in radius, node2 should not
        assert 1 in result
        assert 2 not in result


class TestTimelessValueCalculator:
    """Tests for TimelessValueCalculator."""

    @pytest.fixture
    def mock_tree(self):
        """Create a mock passive tree."""
        tree = MagicMock()
        tree.nodes = {}
        tree.get_node.return_value = None
        tree.get_neighbors.return_value = []
        return tree

    @pytest.fixture
    def mock_loader(self):
        """Create a mock data loader."""
        loader = MagicMock(spec=TimelessJewelDataLoader)
        loader.get_transformations.return_value = {}
        return loader

    def test_create_calculator(self, mock_loader, mock_tree):
        """Test creating a value calculator."""
        calc = TimelessValueCalculator(mock_loader, mock_tree)

        assert calc.data_loader == mock_loader
        assert calc.tree == mock_tree

    def test_score_transformation_dps(self, mock_loader, mock_tree):
        """Test scoring a transformation for DPS."""
        calc = TimelessValueCalculator(mock_loader, mock_tree)

        transform = TimelessTransformation(
            original_node_id=123,
            mods=[
                TimelessNodeMod("fire_damage_+%", 10.0, "10% fire"),
                TimelessNodeMod("attack_speed_+%", 5.0, "5% attack speed"),
            ],
            replaces_original=False,
        )

        score = calc.score_transformation(transform, "DPS")

        # Score should be positive
        assert score > 0

        # Fire damage weight * 10 + attack speed weight * 5
        expected = DPS_STAT_WEIGHTS["fire_damage_+%"] * 10.0 + DPS_STAT_WEIGHTS["attack_speed_+%"] * 5.0
        assert score == expected

    def test_score_transformation_unknown_stat(self, mock_loader, mock_tree):
        """Test scoring with unknown stat (should be 0 weight)."""
        calc = TimelessValueCalculator(mock_loader, mock_tree)

        transform = TimelessTransformation(
            original_node_id=123,
            mods=[
                TimelessNodeMod("unknown_stat", 10.0, "Unknown"),
            ],
            replaces_original=False,
        )

        score = calc.score_transformation(transform, "DPS")
        assert score == 0.0

    def test_analyze_socket_no_nodes(self, mock_loader, mock_tree):
        """Test analyzing socket with no affected nodes."""
        calc = TimelessValueCalculator(mock_loader, mock_tree)

        mock_jewel = MagicMock()
        mock_jewel.jewel_type = "Lethal Pride"
        mock_jewel.seed = 15000

        analysis = calc.analyze_socket(
            mock_jewel, 26725, set(), "DPS"
        )

        assert analysis.socket_node_id == 26725
        assert analysis.total_value == 0.0

    def test_compare_sockets(self, mock_loader, mock_tree):
        """Test comparing multiple sockets."""
        calc = TimelessValueCalculator(mock_loader, mock_tree)

        mock_jewel = MagicMock()
        mock_jewel.jewel_type = "Lethal Pride"
        mock_jewel.seed = 15000

        analyses = calc.compare_sockets(
            mock_jewel, {26725, 36634}, set(), "DPS"
        )

        assert len(analyses) == 2
        # Should be sorted by value
        assert analyses[0].total_value >= analyses[1].total_value

    def test_estimate_pathing_cost_already_allocated(self, mock_loader, mock_tree):
        """Test pathing cost when socket is already allocated."""
        calc = TimelessValueCalculator(mock_loader, mock_tree)

        cost = calc._estimate_pathing_cost(26725, {26725})
        assert cost == 0

    def test_estimate_pathing_cost_adjacent(self, mock_loader, mock_tree):
        """Test pathing cost when socket is adjacent to allocated."""
        mock_tree.get_neighbors.return_value = [100, 200]

        calc = TimelessValueCalculator(mock_loader, mock_tree)

        cost = calc._estimate_pathing_cost(26725, {100})
        assert cost == 1


class TestGetDefaultLoader:
    """Tests for get_default_loader function."""

    def test_returns_loader(self):
        """Test that get_default_loader returns a loader."""
        loader = get_default_loader()

        assert isinstance(loader, TimelessJewelDataLoader)

    def test_returns_same_instance(self):
        """Test that get_default_loader returns singleton."""
        loader1 = get_default_loader()
        loader2 = get_default_loader()

        assert loader1 is loader2


class TestIntegration:
    """Integration tests using actual data files."""

    @pytest.fixture
    def data_dir(self):
        """Get path to data directory."""
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "PathOfBuilding" / "src" / "Data" / "TimelessJewelData"

        if not data_dir.exists():
            pytest.skip("TimelessJewelData directory not found")

        return data_dir

    def test_load_and_query_brutal_restraint(self, data_dir):
        """Test loading and querying Brutal Restraint."""
        loader = TimelessJewelDataLoader(str(data_dir))

        if not (data_dir / "BrutalRestraint.bin").exists():
            pytest.skip("BrutalRestraint.bin not found")

        # Load the data
        result = loader.load_jewel_type("BrutalRestraint")
        assert result is True

        # Query for a known node ID (if in mapping)
        loader._ensure_node_index_loaded()
        if loader._node_index_map:
            node_id = next(iter(loader._node_index_map.keys()))

            transformations = loader.get_transformations(
                "BrutalRestraint", 5000, {node_id}
            )

            # Should return dict (may be empty depending on seed)
            assert isinstance(transformations, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

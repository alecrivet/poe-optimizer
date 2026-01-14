"""Tests for GGG to PoB converter."""

import pytest
import xml.etree.ElementTree as ET

from src.ggg.converter import GGGToPoB, ConversionOptions, CLASS_MAP, ASCENDANCY_MAP
from src.ggg.models import Character, CharacterItems, PassiveTree, Item, ItemSocket


class TestClassMappings:
    """Tests for class and ascendancy mappings."""

    def test_all_classes_mapped(self):
        """Verify all GGG class IDs are mapped."""
        for class_id in range(7):
            assert class_id in CLASS_MAP
            name, pob_id = CLASS_MAP[class_id]
            assert isinstance(name, str)
            assert 1 <= pob_id <= 7

    def test_class_names_correct(self):
        """Verify class names are correct."""
        expected = {
            0: "Scion",
            1: "Marauder",
            2: "Ranger",
            3: "Witch",
            4: "Duelist",
            5: "Templar",
            6: "Shadow",
        }
        for class_id, expected_name in expected.items():
            name, _ = CLASS_MAP[class_id]
            assert name == expected_name

    def test_ascendancy_mappings_exist(self):
        """Verify ascendancy mappings exist for each class."""
        # Each class (except Scion with 1) has 3 ascendancies
        for class_id in range(7):
            max_asc = 1 if class_id == 0 else 3
            for asc_id in range(1, max_asc + 1):
                assert (class_id, asc_id) in ASCENDANCY_MAP


class TestConversionOptions:
    """Tests for ConversionOptions."""

    def test_default_options(self):
        """Test default conversion options."""
        opts = ConversionOptions()
        assert opts.include_items is True
        assert opts.include_passives is True
        assert opts.tree_version == "3_27"
        assert opts.default_gem_level == 20
        assert opts.default_gem_quality == 20

    def test_custom_options(self):
        """Test custom conversion options."""
        opts = ConversionOptions(
            include_items=False,
            include_passives=False,
            tree_version="3_26",
            default_gem_level=21,
        )
        assert opts.include_items is False
        assert opts.tree_version == "3_26"
        assert opts.default_gem_level == 21


class TestGGGToPoB:
    """Tests for GGGToPoB converter."""

    @pytest.fixture
    def basic_character(self):
        """Create a basic character for testing."""
        return Character(
            name="TestWitch",
            class_name="Witch",
            class_id=3,
            ascendancy_class=2,
            ascendancy_name="Elementalist",
            league="Settlers",
            level=90,
            experience=1000000000,
        )

    @pytest.fixture
    def basic_passives(self):
        """Create basic passive data."""
        return PassiveTree(
            hashes=[1000, 2000, 3000, 4000, 5000],
            hashes_ex=[],
            mastery_effects={10000: 20000, 30000: 40000},
            jewel_data={},
        )

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return GGGToPoB()

    def test_basic_conversion(self, converter, basic_character):
        """Test basic character conversion without items/passives."""
        xml_str = converter.convert(basic_character)

        # Parse and verify structure
        root = ET.fromstring(xml_str)
        assert root.tag == "PathOfBuilding"

        # Check Build element
        build = root.find("Build")
        assert build is not None
        assert build.get("level") == "90"
        assert build.get("className") == "Witch"
        assert build.get("ascendClassName") == "Elementalist"

    def test_conversion_with_passives(self, converter, basic_character, basic_passives):
        """Test conversion with passive tree."""
        xml_str = converter.convert(basic_character, passives=basic_passives)

        root = ET.fromstring(xml_str)
        tree = root.find("Tree")
        assert tree is not None

        spec = tree.find("Spec")
        assert spec is not None

        # Check nodes are present
        nodes_str = spec.get("nodes")
        assert nodes_str is not None
        nodes = [int(n) for n in nodes_str.split(",") if n]
        assert len(nodes) == 5

        # Check mastery effects
        mastery_str = spec.get("masteryEffects")
        assert mastery_str is not None
        assert "{10000,20000}" in mastery_str
        assert "{30000,40000}" in mastery_str

    def test_conversion_all_classes(self, converter):
        """Test conversion works for all classes."""
        for class_id in range(7):
            char = Character(
                name=f"Test{class_id}",
                class_name=CLASS_MAP[class_id][0],
                class_id=class_id,
                ascendancy_class=0,
                ascendancy_name="",
                league="Standard",
                level=1,
                experience=0,
            )
            xml_str = converter.convert(char)
            root = ET.fromstring(xml_str)
            build = root.find("Build")
            assert build.get("className") == CLASS_MAP[class_id][0]

    def test_conversion_with_cluster_nodes(self, converter, basic_character):
        """Test conversion with cluster jewel nodes (hashes_ex)."""
        passives = PassiveTree(
            hashes=[1000, 2000],
            hashes_ex=[90000, 90001, 90002],  # Cluster nodes
            mastery_effects={},
            jewel_data={},
        )
        xml_str = converter.convert(basic_character, passives=passives)

        root = ET.fromstring(xml_str)
        spec = root.find("Tree/Spec")
        nodes_str = spec.get("nodes")
        nodes = [int(n) for n in nodes_str.split(",") if n]

        # Should include both regular and cluster nodes
        assert len(nodes) == 5
        assert 90000 in nodes
        assert 90001 in nodes
        assert 90002 in nodes

    def test_includes_notes_section(self, converter, basic_character):
        """Test that Notes section is included."""
        xml_str = converter.convert(basic_character)

        root = ET.fromstring(xml_str)
        notes = root.find("Notes")
        assert notes is not None
        assert "TestWitch" in notes.text
        assert "Settlers" in notes.text

    def test_skills_section_defaults(self, converter, basic_character):
        """Test Skills section has correct defaults."""
        xml_str = converter.convert(basic_character)

        root = ET.fromstring(xml_str)
        skills = root.find("Skills")
        assert skills is not None
        assert skills.get("defaultGemLevel") == "20"
        assert skills.get("defaultGemQuality") == "20"

    def test_items_section_without_items(self, converter, basic_character):
        """Test Items section when no items provided."""
        xml_str = converter.convert(basic_character, items=None)

        root = ET.fromstring(xml_str)
        items = root.find("Items")
        assert items is not None
        assert items.get("activeItemSet") == "1"

    def test_passives_disabled(self, basic_character):
        """Test conversion with passives disabled."""
        options = ConversionOptions(include_passives=False)
        converter = GGGToPoB(options)

        passives = PassiveTree(
            hashes=[1000, 2000, 3000],
            hashes_ex=[],
            mastery_effects={},
            jewel_data={},
        )
        xml_str = converter.convert(basic_character, passives=passives)

        root = ET.fromstring(xml_str)
        spec = root.find("Tree/Spec")
        # Nodes should be empty because include_passives=False
        assert spec.get("nodes") == ""


class TestItemConversion:
    """Tests for item conversion."""

    @pytest.fixture
    def basic_character(self):
        """Create a basic character."""
        return Character(
            name="TestChar",
            class_name="Witch",
            class_id=3,
            ascendancy_class=0,
            ascendancy_name="",
            league="Standard",
            level=90,
            experience=0,
        )

    @pytest.fixture
    def converter(self):
        """Create a converter."""
        return GGGToPoB()

    def test_item_to_xml_unique(self, converter, basic_character):
        """Test converting a unique item."""
        items = CharacterItems(
            character={"name": "TestChar"},
            items=[
                Item(
                    id="unique1",
                    name="Shavronne's Wrappings",
                    type_line="Occultist's Vestment",
                    base_type="Occultist's Vestment",
                    rarity="Unique",
                    ilvl=80,
                    icon="",
                    identified=True,
                    inventory_id="BodyArmour",
                    explicit_mods=[
                        "+100 to maximum Energy Shield",
                        "Lightning Damage does not bypass Energy Shield",
                    ],
                ),
            ],
        )

        xml_str = converter.convert(basic_character, items=items)
        root = ET.fromstring(xml_str)

        items_elem = root.find("Items")
        item = items_elem.find("Item")
        assert item is not None

        item_text = item.text
        assert "Rarity: UNIQUE" in item_text
        assert "Shavronne's Wrappings" in item_text
        assert "Occultist's Vestment" in item_text
        assert "+100 to maximum Energy Shield" in item_text

    def test_item_with_sockets(self, converter, basic_character):
        """Test item socket formatting."""
        items = CharacterItems(
            character={"name": "TestChar"},
            items=[
                Item(
                    id="sock1",
                    name="",
                    type_line="Vaal Regalia",
                    base_type="Vaal Regalia",
                    rarity="Rare",
                    ilvl=86,
                    icon="",
                    identified=True,
                    inventory_id="BodyArmour",
                    sockets=[
                        ItemSocket(group=0, attr="I"),
                        ItemSocket(group=0, attr="I"),
                        ItemSocket(group=0, attr="I"),
                        ItemSocket(group=0, attr="I"),
                        ItemSocket(group=0, attr="I"),
                        ItemSocket(group=0, attr="I"),
                    ],
                ),
            ],
        )

        xml_str = converter.convert(basic_character, items=items)
        root = ET.fromstring(xml_str)

        item = root.find("Items/Item")
        assert "Sockets: B-B-B-B-B-B" in item.text

    def test_item_with_influence(self, converter, basic_character):
        """Test item with influence tags."""
        items = CharacterItems(
            character={"name": "TestChar"},
            items=[
                Item(
                    id="inf1",
                    name="",
                    type_line="Hubris Circlet",
                    base_type="Hubris Circlet",
                    rarity="Rare",
                    ilvl=86,
                    icon="",
                    identified=True,
                    inventory_id="Helm",
                    shaper=True,
                    elder=True,
                    hunter=True,
                ),
            ],
        )

        xml_str = converter.convert(basic_character, items=items)
        root = ET.fromstring(xml_str)

        item = root.find("Items/Item")
        item_text = item.text
        assert "Shaper Item" in item_text
        assert "Elder Item" in item_text
        assert "Hunter Item" in item_text

    def test_item_with_crafted_mods(self, converter, basic_character):
        """Test item with crafted mods marked correctly."""
        items = CharacterItems(
            character={"name": "TestChar"},
            items=[
                Item(
                    id="craft1",
                    name="",
                    type_line="Titanium Spirit Shield",
                    base_type="Titanium Spirit Shield",
                    rarity="Rare",
                    ilvl=84,
                    icon="",
                    identified=True,
                    inventory_id="Offhand",
                    explicit_mods=["+50 to Maximum Life"],
                    crafted_mods=["+20% increased Spell Damage"],
                ),
            ],
        )

        xml_str = converter.convert(basic_character, items=items)
        root = ET.fromstring(xml_str)

        item = root.find("Items/Item")
        item_text = item.text
        assert "+50 to Maximum Life" in item_text
        assert "{crafted}+20% increased Spell Damage" in item_text

    def test_item_slot_mapping(self, converter, basic_character):
        """Test items are assigned to correct PoB slots."""
        items = CharacterItems(
            character={"name": "TestChar"},
            items=[
                Item(
                    id="helm1",
                    name="",
                    type_line="Hubris Circlet",
                    base_type="Hubris Circlet",
                    rarity="Rare",
                    ilvl=84,
                    icon="",
                    identified=True,
                    inventory_id="Helm",
                ),
                Item(
                    id="body1",
                    name="",
                    type_line="Vaal Regalia",
                    base_type="Vaal Regalia",
                    rarity="Rare",
                    ilvl=86,
                    icon="",
                    identified=True,
                    inventory_id="BodyArmour",
                ),
            ],
        )

        xml_str = converter.convert(basic_character, items=items)
        root = ET.fromstring(xml_str)

        item_set = root.find("Items/ItemSet")
        slots = item_set.findall("Slot")

        slot_names = {s.get("name") for s in slots}
        assert "Helmet" in slot_names
        assert "Body Armour" in slot_names

    def test_corrupted_item(self, converter, basic_character):
        """Test corrupted item has Corrupted tag."""
        items = CharacterItems(
            character={"name": "TestChar"},
            items=[
                Item(
                    id="corrupt1",
                    name="Starforge",
                    type_line="Infernal Sword",
                    base_type="Infernal Sword",
                    rarity="Unique",
                    ilvl=83,
                    icon="",
                    identified=True,
                    inventory_id="Weapon",
                    corrupted=True,
                ),
            ],
        )

        xml_str = converter.convert(basic_character, items=items)
        root = ET.fromstring(xml_str)

        item = root.find("Items/Item")
        assert "Corrupted" in item.text

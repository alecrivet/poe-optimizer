"""Tests for GGG API models."""

import pytest
from src.ggg.models import Character, Item, ItemSocket, CharacterItems, PassiveTree


class TestCharacter:
    """Tests for Character model."""

    def test_from_dict_basic(self):
        """Test basic character parsing."""
        data = {
            "name": "TestChar",
            "class": "Witch",
            "classId": 3,
            "ascendancyClass": 2,
            "league": "Settlers",
            "level": 95,
            "experience": 1234567890,
        }
        char = Character.from_dict(data)

        assert char.name == "TestChar"
        assert char.class_name == "Witch"
        assert char.class_id == 3
        assert char.ascendancy_class == 2
        assert char.league == "Settlers"
        assert char.level == 95
        assert char.experience == 1234567890

    def test_from_dict_with_ascendancy_name(self):
        """Test character with ascendancy name in response."""
        data = {
            "name": "AscendChar",
            "class": "Shadow",
            "classId": 6,
            "ascendancyClass": 1,
            "ascendClassName": "Assassin",
            "league": "Standard",
            "level": 100,
        }
        char = Character.from_dict(data)

        assert char.ascendancy_name == "Assassin"
        assert char.ascendancy_class == 1

    def test_from_dict_minimal(self):
        """Test character with minimal required fields."""
        data = {
            "name": "MinChar",
            "class": "Scion",
            "classId": 0,
            "league": "Standard",
            "level": 1,
        }
        char = Character.from_dict(data)

        assert char.name == "MinChar"
        assert char.level == 1
        assert char.ascendancy_class == 0  # Default
        assert char.experience == 0  # Default


class TestItemSocket:
    """Tests for ItemSocket model."""

    def test_direct_construction(self):
        """Test direct socket construction."""
        socket = ItemSocket(group=0, attr="S")

        assert socket.group == 0
        assert socket.attr == "S"

    def test_different_attrs(self):
        """Test different socket attributes."""
        for attr in ["S", "D", "I", "G", "A", "DV"]:
            socket = ItemSocket(group=0, attr=attr)
            assert socket.attr == attr


class TestItem:
    """Tests for Item model."""

    def test_from_dict_basic(self):
        """Test basic item parsing."""
        data = {
            "id": "abc123",
            "name": "The Blood Thorn",
            "typeLine": "Royal Axe",
            "baseType": "Royal Axe",
            "frameType": 3,  # Unique
            "ilvl": 83,
            "identified": True,
            "inventoryId": "Weapon",
            "explicitMods": ["+100% increased Physical Damage"],
        }
        item = Item.from_dict(data)

        assert item.id == "abc123"
        assert item.name == "The Blood Thorn"
        assert item.type_line == "Royal Axe"
        assert item.rarity == "Unique"
        assert item.ilvl == 83
        assert item.inventory_id == "Weapon"
        assert "+100% increased Physical Damage" in item.explicit_mods

    def test_from_dict_with_influence(self):
        """Test item with influence flags."""
        data = {
            "id": "inf123",
            "typeLine": "Hubris Circlet",
            "baseType": "Hubris Circlet",
            "frameType": 2,  # Rare
            "ilvl": 86,
            "identified": True,
            "shaper": True,
            "elder": True,
        }
        item = Item.from_dict(data)

        assert item.shaper is True
        assert item.elder is True
        assert item.crusader is False  # Default
        assert item.hunter is False  # Default

    def test_from_dict_with_sockets(self):
        """Test item with sockets."""
        data = {
            "id": "sock123",
            "typeLine": "Vaal Regalia",
            "baseType": "Vaal Regalia",
            "frameType": 2,
            "ilvl": 84,
            "identified": True,
            "sockets": [
                {"group": 0, "attr": "I"},
                {"group": 0, "attr": "I"},
                {"group": 0, "attr": "I"},
                {"group": 1, "attr": "S"},
            ],
        }
        item = Item.from_dict(data)

        assert len(item.sockets) == 4
        assert item.sockets[0].attr == "I"
        assert item.sockets[0].group == 0
        assert item.sockets[3].group == 1

    def test_from_dict_with_all_mod_types(self):
        """Test item with all mod types."""
        data = {
            "id": "mods123",
            "typeLine": "Titanium Spirit Shield",
            "baseType": "Titanium Spirit Shield",
            "frameType": 2,
            "ilvl": 85,
            "identified": True,
            "implicitMods": ["+5% to all Elemental Resistances"],
            "explicitMods": ["+50 to Maximum Life", "+30% Fire Resistance"],
            "craftedMods": ["+20% Spell Damage"],
            "enchantMods": ["Trigger Socketed Spells when you Focus"],
            "fracturedMods": ["+50 to Maximum Life"],
        }
        item = Item.from_dict(data)

        assert len(item.implicit_mods) == 1
        assert len(item.explicit_mods) == 2
        assert len(item.crafted_mods) == 1
        assert len(item.enchant_mods) == 1
        assert len(item.fractured_mods) == 1


class TestCharacterItems:
    """Tests for CharacterItems model."""

    def test_from_dict(self):
        """Test character items parsing."""
        data = {
            "character": {"name": "TestChar"},
            "items": [
                {
                    "id": "item1",
                    "typeLine": "Hubris Circlet",
                    "baseType": "Hubris Circlet",
                    "frameType": 2,
                    "ilvl": 84,
                    "identified": True,
                    "inventoryId": "Helm",
                },
                {
                    "id": "item2",
                    "typeLine": "Vaal Regalia",
                    "baseType": "Vaal Regalia",
                    "frameType": 2,
                    "ilvl": 86,
                    "identified": True,
                    "inventoryId": "BodyArmour",
                },
            ],
        }
        items = CharacterItems.from_dict(data)

        assert items.character["name"] == "TestChar"
        assert len(items.items) == 2
        assert items.items[0].inventory_id == "Helm"
        assert items.items[1].inventory_id == "BodyArmour"

    def test_from_dict_empty_items(self):
        """Test character with no items."""
        data = {
            "character": {"name": "EmptyChar"},
            "items": [],
        }
        items = CharacterItems.from_dict(data)

        assert items.character["name"] == "EmptyChar"
        assert len(items.items) == 0

    def test_get_item_by_slot(self):
        """Test getting item by slot."""
        data = {
            "character": {"name": "TestChar"},
            "items": [
                {
                    "id": "helm1",
                    "typeLine": "Hubris Circlet",
                    "ilvl": 84,
                    "inventoryId": "Helm",
                },
            ],
        }
        items = CharacterItems.from_dict(data)

        helm = items.get_item_by_slot("Helm")
        assert helm is not None
        assert helm.id == "helm1"

        gloves = items.get_item_by_slot("Gloves")
        assert gloves is None


class TestPassiveTree:
    """Tests for PassiveTree model."""

    def test_from_dict_basic(self):
        """Test basic passive tree parsing."""
        data = {
            "hashes": [1234, 5678, 9012],
            "hashes_ex": [3456],
            "mastery_effects": {
                "12345": 67890,
                "11111": 22222,
            },
        }
        tree = PassiveTree.from_dict(data)

        assert tree.hashes == [1234, 5678, 9012]
        assert tree.hashes_ex == [3456]
        assert len(tree.mastery_effects) == 2
        assert tree.mastery_effects[12345] == 67890
        assert tree.mastery_effects[11111] == 22222

    def test_from_dict_empty(self):
        """Test empty passive tree."""
        data = {}
        tree = PassiveTree.from_dict(data)

        assert tree.hashes == []
        assert tree.hashes_ex == []
        assert tree.mastery_effects == {}

    def test_from_dict_with_jewel_data(self):
        """Test passive tree with jewel data."""
        data = {
            "hashes": [1000, 2000],
            "jewel_data": {
                "26725": {"type": "ExpandedJewelSocketNode"},
            },
        }
        tree = PassiveTree.from_dict(data)

        assert "26725" in tree.jewel_data
        assert tree.jewel_data["26725"]["type"] == "ExpandedJewelSocketNode"

#!/usr/bin/env python3
"""
Tests for timeless jewel parsing and data extraction
"""

import pytest
from src.pob.jewel.timeless import (
    TimelessJewel,
    parse_timeless_jewels,
    TIMELESS_JEWEL_TYPES,
)


class TestTimelessJewelParsing:
    """Test parsing of timeless jewel XML"""

    def test_parse_glorious_vanity(self):
        """Test parsing Glorious Vanity jewel"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Prismatic Jewel
Glorious Vanity
Timeless Jewel
Bathed in the blood of 12345 sacrificed in the name of Doryani
Corrupts your Soul
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="26725" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.jewel_type == "Glorious Vanity"
        assert jewel.seed == 12345
        assert jewel.variant == "Doryani"
        assert jewel.legion == "Vaal"
        assert jewel.socket_node_id == 26725
        assert jewel.keystone_name == "Corrupted Soul"

    def test_parse_lethal_pride(self):
        """Test parsing Lethal Pride jewel"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Crimson Jewel
Lethal Pride
Timeless Jewel
Commanded leadership over 54321 warriors under Kaom
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="12345" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.jewel_type == "Lethal Pride"
        assert jewel.seed == 54321
        assert jewel.variant == "Kaom"
        assert jewel.legion == "Karui"
        assert jewel.keystone_name == "Strength of Blood"

    def test_parse_elegant_hubris(self):
        """Test parsing Elegant Hubris jewel"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Viridian Jewel
Elegant Hubris
Timeless Jewel
Commissioned 99999 coins to commemorate Victario
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="7777" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.jewel_type == "Elegant Hubris"
        assert jewel.seed == 99999
        assert jewel.variant == "Victario"
        assert jewel.legion == "Eternal Empire"
        assert jewel.keystone_name == "Supreme Grandstanding"

    def test_parse_militant_faith(self):
        """Test parsing Militant Faith jewel"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Cobalt Jewel
Militant Faith
Timeless Jewel
11111 inscribed in the name of Dominus
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="4444" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.jewel_type == "Militant Faith"
        assert jewel.seed == 11111
        assert jewel.variant == "Dominus"
        assert jewel.legion == "Templar"
        assert jewel.keystone_name == "Power of Purpose"

    def test_parse_brutal_restraint(self):
        """Test parsing Brutal Restraint jewel"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Viridian Jewel
Brutal Restraint
Timeless Jewel
22222 denoted service of Balbala
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="8888" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        assert len(jewels) == 1
        jewel = jewels[0]
        assert jewel.jewel_type == "Brutal Restraint"
        assert jewel.seed == 22222
        assert jewel.variant == "Balbala"
        assert jewel.legion == "Maraketh"
        assert jewel.keystone_name == "The Traitor"

    def test_parse_multiple_timeless_jewels(self):
        """Test parsing multiple timeless jewels in one build"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Prismatic Jewel
Glorious Vanity
Timeless Jewel
Bathed in the blood of 100 sacrificed in the name of Xibaqua
</Item>
                <Item id="2">Crimson Jewel
Lethal Pride
Timeless Jewel
Commanded leadership over 200 warriors under Akoya
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="1000" itemId="1"/>
                <Socket nodeId="2000" itemId="2"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        assert len(jewels) == 2

        # Check first jewel
        vanity = next(j for j in jewels if j.jewel_type == "Glorious Vanity")
        assert vanity.seed == 100
        assert vanity.variant == "Xibaqua"
        assert vanity.socket_node_id == 1000

        # Check second jewel
        pride = next(j for j in jewels if j.jewel_type == "Lethal Pride")
        assert pride.seed == 200
        assert pride.variant == "Akoya"
        assert pride.socket_node_id == 2000

    def test_parse_without_timeless_jewel_marker(self):
        """Test that jewels without 'Timeless Jewel' text aren't parsed"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Prismatic Jewel
Glorious Vanity
Bathed in the blood of 100 sacrificed in the name of Doryani
</Item>
            </Items>
            <Sockets>
                <Socket nodeId="1000" itemId="1"/>
            </Sockets>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        # Won't parse without "Timeless Jewel" marker
        assert len(jewels) == 0

    def test_parse_invalid_seed(self):
        """Test handling of invalid seed values"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Glorious Vanity
Bathed in the blood of INVALID sacrificed in the name of Doryani
</Item>
            </Items>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        # Should not parse without valid seed
        assert len(jewels) == 0

    def test_parse_missing_variant(self):
        """Test handling when variant is missing"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Glorious Vanity
Bathed in the blood of 12345 sacrificed in the name of
</Item>
            </Items>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        # Should not parse without variant
        assert len(jewels) == 0

    def test_unsocketed_timeless_jewel(self):
        """Test timeless jewel that isn't socketed"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <Item id="1">Prismatic Jewel
Glorious Vanity
Timeless Jewel
Bathed in the blood of 5555 sacrificed in the name of Ahuana
</Item>
            </Items>
        </PathOfBuilding>
        """

        jewels = parse_timeless_jewels(xml)

        assert len(jewels) == 1
        assert jewels[0].socket_node_id is None

    def test_display_name(self):
        """Test display name property"""
        from src.pob.jewel.base import JewelCategory

        jewel = TimelessJewel(
            category=JewelCategory.TIMELESS,
            item_id=1,
            raw_text="test",
            jewel_type="Glorious Vanity",
            seed=12345,
            variant="Doryani",
            variant_id=1,
            legion="Vaal",
        )

        assert jewel.display_name == "Glorious Vanity (Doryani, Seed 12345)"

    def test_all_variants_have_keystones(self):
        """Test that all variant combinations have keystone mappings"""
        from src.pob.jewel.base import JewelCategory

        for jewel_type, info in TIMELESS_JEWEL_TYPES.items():
            for variant_name in info["variants"].keys():
                jewel = TimelessJewel(
                    category=JewelCategory.TIMELESS,
                    item_id=1,
                    raw_text="test",
                    jewel_type=jewel_type,
                    seed=1,
                    variant=variant_name,
                    variant_id=1,
                    legion=info["legion"],
                )

                # Every variant should have a keystone
                assert jewel.keystone_name is not None, \
                    f"{jewel_type} ({variant_name}) missing keystone mapping"


class TestTimelessJewelTypes:
    """Test timeless jewel type definitions"""

    def test_all_types_defined(self):
        """Test that all 5 timeless jewel types are defined"""
        expected_types = [
            "Glorious Vanity",
            "Lethal Pride",
            "Elegant Hubris",
            "Militant Faith",
            "Brutal Restraint",
        ]

        for jewel_type in expected_types:
            assert jewel_type in TIMELESS_JEWEL_TYPES

    def test_each_type_has_3_variants(self):
        """Test that each type has exactly 3 variants"""
        for jewel_type, info in TIMELESS_JEWEL_TYPES.items():
            assert len(info["variants"]) == 3, \
                f"{jewel_type} should have 3 variants, has {len(info['variants'])}"

    def test_variant_ids_are_unique(self):
        """Test that variant IDs are unique within each type"""
        for jewel_type, info in TIMELESS_JEWEL_TYPES.items():
            variant_ids = list(info["variants"].values())
            assert len(variant_ids) == len(set(variant_ids)), \
                f"{jewel_type} has duplicate variant IDs"

    def test_patterns_are_valid_regex(self):
        """Test that all keystone patterns are valid regex"""
        import re

        for jewel_type, info in TIMELESS_JEWEL_TYPES.items():
            pattern = info["keystone_pattern"]

            # Should compile without error
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"{jewel_type} has invalid regex pattern: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

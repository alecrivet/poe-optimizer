"""
Tests for PoB Code Codec (encoder/decoder for Path of Building import codes)
"""

import pytest
from src.pob.codec import (
    decode_pob_code,
    encode_pob_code,
    is_valid_pob_code,
    DecodeError,
    EncodeError,
)


# Test XML from demo
DEMO_BUILD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" targetVersion="3_0" className="Marauder" ascendClassName="Juggernaut">
        <PlayerStat stat="Strength" value="200"/>
        <PlayerStat stat="Dexterity" value="100"/>
        <PlayerStat stat="Intelligence" value="50"/>
    </Build>
    <Tree activeSpec="1">
        <Spec title="Demo Build" treeVersion="3_25" classId="1" ascendClassId="1"
              nodes="0,1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90,100"/>
    </Tree>
    <Items activeItemSet="1">
        <ItemSet id="1" title="Gear"/>
    </Items>
    <Skills activeSkillSet="1">
        <SkillSet id="1"/>
    </Skills>
    <Config/>
</PathOfBuilding>"""


class TestEncodePoB:
    """Tests for encoding XML to PoB codes"""

    def test_encode_basic_xml(self):
        """Test encoding a simple XML string"""
        code = encode_pob_code(DEMO_BUILD_XML)
        assert isinstance(code, str)
        assert len(code) > 0
        # PoB codes typically start with 'e' (base64 of zlib header - can be eN, eJ, etc.)
        assert code.startswith('e')

    def test_encode_with_url_encoding(self):
        """Test encoding with URL encoding enabled"""
        code = encode_pob_code(DEMO_BUILD_XML, url_encode=True)
        assert isinstance(code, str)
        # URL encoded version should not have certain characters
        assert '+' not in code or '%2B' in code
        assert '/' not in code or '%2F' in code

    def test_encode_empty_xml_raises_error(self):
        """Test that encoding empty XML raises an error"""
        with pytest.raises(EncodeError, match="XML cannot be empty"):
            encode_pob_code("")

    def test_encode_none_raises_error(self):
        """Test that encoding None raises an error"""
        with pytest.raises(EncodeError, match="must be a string"):
            encode_pob_code(None)

    def test_encode_non_string_raises_error(self):
        """Test that encoding non-string input raises an error"""
        with pytest.raises(EncodeError, match="must be a string"):
            encode_pob_code(12345)


class TestDecodePob:
    """Tests for decoding PoB codes to XML"""

    def test_decode_valid_code(self):
        """Test decoding a valid PoB code"""
        # First encode our demo XML
        code = encode_pob_code(DEMO_BUILD_XML)
        # Then decode it back
        decoded_xml = decode_pob_code(code)
        assert isinstance(decoded_xml, str)
        assert decoded_xml.strip().startswith('<?xml') or decoded_xml.strip().startswith('<PathOfBuilding')

    def test_decode_url_encoded_code(self):
        """Test decoding a URL-encoded PoB code"""
        # Create a URL-encoded code
        code = encode_pob_code(DEMO_BUILD_XML, url_encode=True)
        # Should decode successfully
        decoded_xml = decode_pob_code(code)
        assert isinstance(decoded_xml, str)
        assert '<PathOfBuilding>' in decoded_xml

    def test_decode_empty_code_raises_error(self):
        """Test that decoding empty code raises an error"""
        with pytest.raises(DecodeError, match="cannot be empty"):
            decode_pob_code("")

    def test_decode_none_raises_error(self):
        """Test that decoding None raises an error"""
        with pytest.raises(DecodeError, match="must be a string"):
            decode_pob_code(None)

    def test_decode_invalid_base64_raises_error(self):
        """Test that invalid base64 raises an error"""
        with pytest.raises(DecodeError, match="Invalid base64"):
            decode_pob_code("not-valid-base64!!!")

    def test_decode_valid_base64_invalid_zlib_raises_error(self):
        """Test that valid base64 but invalid zlib raises an error"""
        import base64
        # Create valid base64 that's not valid zlib
        invalid_compressed = base64.b64encode(b"not compressed data").decode()
        with pytest.raises(DecodeError, match="Invalid zlib"):
            decode_pob_code(invalid_compressed)

    def test_decode_non_xml_content_raises_error(self):
        """Test that valid encoding of non-XML content raises an error"""
        import base64
        import zlib
        # Encode plain text (not XML)
        plain_text = b"This is not XML"
        compressed = zlib.compress(plain_text)
        code = base64.b64encode(compressed).decode()
        with pytest.raises(DecodeError, match="does not appear to be XML"):
            decode_pob_code(code)


class TestRoundTrip:
    """Tests for round-trip encoding/decoding"""

    def test_roundtrip_preserves_xml(self):
        """Test that encoding then decoding preserves the XML"""
        original_xml = DEMO_BUILD_XML
        # Encode
        code = encode_pob_code(original_xml)
        # Decode
        decoded_xml = decode_pob_code(code)
        # Should match (might have whitespace differences)
        assert decoded_xml.strip() == original_xml.strip()

    def test_roundtrip_with_url_encoding(self):
        """Test round-trip with URL encoding"""
        original_xml = DEMO_BUILD_XML
        # Encode with URL encoding
        code = encode_pob_code(original_xml, url_encode=True)
        # Decode (should handle URL encoding automatically)
        decoded_xml = decode_pob_code(code)
        # Should match
        assert decoded_xml.strip() == original_xml.strip()

    def test_double_roundtrip(self):
        """Test that multiple encode/decode cycles preserve data"""
        xml1 = DEMO_BUILD_XML
        # First round-trip
        code1 = encode_pob_code(xml1)
        xml2 = decode_pob_code(code1)
        # Second round-trip
        code2 = encode_pob_code(xml2)
        xml3 = decode_pob_code(code2)
        # All should match
        assert xml1.strip() == xml2.strip() == xml3.strip()


class TestIsValidPobCode:
    """Tests for PoB code validation"""

    def test_valid_code_returns_true(self):
        """Test that valid code is recognized"""
        code = encode_pob_code(DEMO_BUILD_XML)
        assert is_valid_pob_code(code) is True

    def test_invalid_code_returns_false(self):
        """Test that invalid code returns False"""
        assert is_valid_pob_code("invalid-code") is False
        assert is_valid_pob_code("") is False
        assert is_valid_pob_code("eNnotvalidzlib") is False


class TestRealPoBCodes:
    """Tests with real PoB codes from poe.ninja

    These tests are marked as 'real_builds' and can be run separately.
    Real PoB codes should be added here once obtained from poe.ninja.
    """

    @pytest.mark.skip(reason="No real PoB codes yet - add from poe.ninja")
    def test_decode_real_build_1(self):
        """Test decoding a real PoB code from poe.ninja"""
        # TODO: Add real PoB code here
        real_code = "eN..."  # Replace with actual code
        xml = decode_pob_code(real_code)
        assert '<PathOfBuilding>' in xml
        # Can also test with PoBCalculator
        # from src.pob.caller import PoBCalculator
        # calc = PoBCalculator()
        # stats = calc.evaluate_build(xml)
        # assert stats['life'] > 0

    @pytest.mark.skip(reason="No real PoB codes yet - add from poe.ninja")
    def test_decode_real_build_2(self):
        """Test decoding another real PoB code"""
        real_code = "eN..."  # Replace with actual code
        xml = decode_pob_code(real_code)
        assert '<PathOfBuilding>' in xml

    @pytest.mark.skip(reason="No real PoB codes yet - add from poe.ninja")
    def test_decode_real_build_3(self):
        """Test decoding a third real PoB code"""
        real_code = "eN..."  # Replace with actual code
        xml = decode_pob_code(real_code)
        assert '<PathOfBuilding>' in xml


class TestSpecialCases:
    """Tests for edge cases and special scenarios"""

    def test_encode_xml_with_special_characters(self):
        """Test encoding XML with special characters"""
        xml_with_special = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Note>Special chars: &lt;&gt;&amp; "quotes" 'apostrophes' émojis 🎮</Note>
</PathOfBuilding>"""
        code = encode_pob_code(xml_with_special)
        decoded = decode_pob_code(code)
        assert decoded.strip() == xml_with_special.strip()

    def test_encode_large_xml(self):
        """Test encoding a larger XML structure"""
        # Create a larger XML with more nodes
        large_xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="100" className="Witch"/>
    <Tree activeSpec="1">
        <Spec title="Large Build" nodes="{}"/>
    </Tree>
    <Items activeItemSet="1">
        {}
    </Items>
</PathOfBuilding>""".format(
            ",".join(str(i) for i in range(1000)),  # 1000 passive nodes
            "\n        ".join(f'<Item id="{i}"/>' for i in range(100))  # 100 items
        )
        code = encode_pob_code(large_xml)
        decoded = decode_pob_code(code)
        assert '<PathOfBuilding>' in decoded
        assert 'nodes=' in decoded

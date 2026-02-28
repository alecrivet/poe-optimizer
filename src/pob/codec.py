"""
PoB Code Codec - Encoder and Decoder for Path of Building Import Codes

Path of Building import codes are encoded as follows:
1. Start with XML string
2. Compress with zlib
3. Encode with base64
4. Optionally URL-encode for sharing

This module provides functions to decode PoB import codes to XML and encode XML back to PoB codes.
"""

import base64
import zlib
from urllib.parse import unquote, quote
from typing import Optional


class PoBCodecError(Exception):
    """Base exception for PoB codec errors"""
    pass


class DecodeError(PoBCodecError):
    """Raised when decoding a PoB code fails"""
    pass


class EncodeError(PoBCodecError):
    """Raised when encoding XML to PoB code fails"""
    pass


def decode_pob_code(code: str) -> str:
    """
    Decode a Path of Building import code to XML.

    PoB codes are base64-encoded, zlib-compressed XML strings.
    They may optionally be URL-encoded.

    Args:
        code: The PoB import code to decode (may be URL-encoded)

    Returns:
        The decoded XML string

    Raises:
        DecodeError: If the code is malformed or cannot be decoded

    Examples:
        >>> xml = decode_pob_code("eNpLy...")
        >>> # Use with PoBCalculator
        >>> from pob.caller import PoBCalculator
        >>> calc = PoBCalculator()
        >>> stats = calc.evaluate_build(xml)
    """
    if not isinstance(code, str):
        raise DecodeError(f"PoB code must be a string, got {type(code).__name__}")

    if not code:
        raise DecodeError("PoB code cannot be empty")

    try:
        # Step 1: URL decode if needed (detect if URL-encoded by checking for % signs)
        if '%' in code:
            code = unquote(code)

        # Step 1.5: Convert URL-safe base64 to standard base64
        # PoB codes use URL-safe base64 (- and _ instead of + and /)
        code = code.replace('-', '+').replace('_', '/')

        # Step 2: Base64 decode
        try:
            compressed = base64.b64decode(code, validate=True)
        except Exception as e:
            raise DecodeError(f"Invalid base64 encoding: {e}")

        # Step 3: Zlib decompress
        try:
            xml_bytes = zlib.decompress(compressed)
        except zlib.error as e:
            raise DecodeError(f"Invalid zlib compression: {e}")

        # Step 4: Decode to UTF-8
        try:
            xml = xml_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            raise DecodeError(f"Invalid UTF-8 encoding: {e}")

        # Basic validation that it looks like XML
        if not xml.strip().startswith('<'):
            raise DecodeError("Decoded content does not appear to be XML")

        return xml

    except DecodeError:
        raise
    except Exception as e:
        raise DecodeError(f"Unexpected error decoding PoB code: {e}")


def encode_pob_code(xml: str, url_encode: bool = False) -> str:
    """
    Encode XML to a Path of Building import code.

    Args:
        xml: The XML string to encode
        url_encode: If True, URL-encode the result for safe use in URLs

    Returns:
        The encoded PoB import code

    Raises:
        EncodeError: If the XML cannot be encoded

    Examples:
        >>> xml = "<PathOfBuilding>...</PathOfBuilding>"
        >>> code = encode_pob_code(xml)
        >>> # For use in URLs
        >>> url_safe_code = encode_pob_code(xml, url_encode=True)
    """
    if not isinstance(xml, str):
        raise EncodeError(f"XML must be a string, got {type(xml).__name__}")

    if not xml:
        raise EncodeError("XML cannot be empty")

    try:
        # Step 1: Encode to UTF-8
        xml_bytes = xml.encode('utf-8')

        # Step 2: Zlib compress
        try:
            compressed = zlib.compress(xml_bytes)
        except Exception as e:
            raise EncodeError(f"Compression failed: {e}")

        # Step 3: Base64 encode (using URL-safe base64 to match PoB format)
        try:
            code = base64.b64encode(compressed).decode('ascii')
            # Convert to URL-safe base64 (- and _ instead of + and /)
            code = code.replace('+', '-').replace('/', '_')
        except Exception as e:
            raise EncodeError(f"Base64 encoding failed: {e}")

        # Step 4: Optional URL encoding (for embedding in URLs)
        if url_encode:
            code = quote(code, safe='')

        return code

    except EncodeError:
        raise
    except Exception as e:
        raise EncodeError(f"Unexpected error encoding XML: {e}")


def is_valid_pob_code(code: str) -> bool:
    """
    Check if a string is a valid PoB import code.

    Args:
        code: The string to check

    Returns:
        True if the code can be decoded successfully, False otherwise
    """
    try:
        decode_pob_code(code)
        return True
    except (DecodeError, Exception):
        return False

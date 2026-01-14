"""
GGG API module for Path of Exile character import.

This module provides functionality to:
- Fetch character data from GGG's official API
- Convert GGG JSON format to PoB XML format
- Handle authentication and rate limiting

Usage:
    from src.ggg import GGGClient, GGGToPoB

    # Fetch character data
    client = GGGClient()
    characters = client.get_characters("AccountName")
    passives = client.get_passive_skills("AccountName", "CharacterName")

    # Convert to PoB format
    converter = GGGToPoB()
    xml = converter.convert(characters[0], passives=passives)
"""

from .client import GGGClient, GGGClientConfig, Realm
from .converter import GGGToPoB, ConversionOptions, convert_character_to_pob
from .models import Character, CharacterItems, PassiveTree, Item
from .exceptions import (
    GGGAPIError,
    AuthenticationError,
    RateLimitError,
    CharacterNotFoundError,
    PrivateProfileError,
    ConversionError,
)

__all__ = [
    # Client
    "GGGClient",
    "GGGClientConfig",
    "Realm",
    # Converter
    "GGGToPoB",
    "ConversionOptions",
    "convert_character_to_pob",
    # Models
    "Character",
    "CharacterItems",
    "PassiveTree",
    "Item",
    # Exceptions
    "GGGAPIError",
    "AuthenticationError",
    "RateLimitError",
    "CharacterNotFoundError",
    "PrivateProfileError",
    "ConversionError",
]

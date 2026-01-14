"""
Data models for GGG API responses.

These dataclasses represent the structure of data returned by GGG's
character-window API endpoints.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Character:
    """Character summary from get-characters endpoint."""
    name: str
    league: str
    class_id: int
    class_name: str
    ascendancy_class: int
    ascendancy_name: str
    level: int
    experience: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character":
        return cls(
            name=data["name"],
            league=data["league"],
            class_id=data["classId"],
            class_name=data["class"],
            ascendancy_class=data.get("ascendancyClass", 0),
            ascendancy_name=data.get("ascendClassName", ""),
            level=data["level"],
            experience=data.get("experience", 0),
        )


@dataclass
class ItemSocket:
    """Socket information for an item."""
    group: int
    attr: str  # "S" (str), "D" (dex), "I" (int), "G" (white), "A" (abyss), "DV" (delve)


@dataclass
class ItemProperty:
    """Item property (stat line)."""
    name: str
    values: List[List[Any]]
    display_mode: int
    type: Optional[int] = None


@dataclass
class Item:
    """
    Item from get-items endpoint.

    Represents a single equipped item with all its properties,
    mods, and sockets.
    """
    id: str
    name: str
    type_line: str
    base_type: str
    rarity: str  # "Normal", "Magic", "Rare", "Unique"
    ilvl: int
    icon: str
    inventory_id: str  # "Weapon", "BodyArmour", "Ring", etc.

    # Optional fields
    identified: bool = True
    corrupted: bool = False
    sockets: List[ItemSocket] = field(default_factory=list)
    properties: List[ItemProperty] = field(default_factory=list)
    requirements: List[ItemProperty] = field(default_factory=list)
    implicit_mods: List[str] = field(default_factory=list)
    explicit_mods: List[str] = field(default_factory=list)
    crafted_mods: List[str] = field(default_factory=list)
    enchant_mods: List[str] = field(default_factory=list)
    fractured_mods: List[str] = field(default_factory=list)

    # Influence
    shaper: bool = False
    elder: bool = False
    crusader: bool = False
    redeemer: bool = False
    hunter: bool = False
    warlord: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        sockets = [
            ItemSocket(s["group"], s.get("attr", s.get("sColour", "G")))
            for s in data.get("sockets", [])
        ]

        return cls(
            id=data["id"],
            name=data.get("name", ""),
            type_line=data.get("typeLine", ""),
            base_type=data.get("baseType", data.get("typeLine", "")),
            rarity=cls._rarity_from_frame(data.get("frameType", 0)),
            ilvl=data.get("ilvl", 1),
            icon=data.get("icon", ""),
            inventory_id=data.get("inventoryId", ""),
            identified=data.get("identified", True),
            corrupted=data.get("corrupted", False),
            sockets=sockets,
            implicit_mods=data.get("implicitMods", []),
            explicit_mods=data.get("explicitMods", []),
            crafted_mods=data.get("craftedMods", []),
            enchant_mods=data.get("enchantMods", []),
            fractured_mods=data.get("fracturedMods", []),
            shaper=data.get("shaper", False),
            elder=data.get("elder", False),
            crusader=data.get("crusader", False),
            redeemer=data.get("redeemer", False),
            hunter=data.get("hunter", False),
            warlord=data.get("warlord", False),
        )

    @staticmethod
    def _rarity_from_frame(frame_type: int) -> str:
        """Convert frameType to rarity string."""
        return {
            0: "Normal",
            1: "Magic",
            2: "Rare",
            3: "Unique",
            4: "Gem",
            5: "Currency",
            6: "DivinationCard",
            7: "Quest",
            8: "Prophecy",
            9: "Relic",
        }.get(frame_type, "Normal")


@dataclass
class CharacterItems:
    """All items equipped on a character."""
    items: List[Item]
    character: Dict[str, Any]  # Basic character info returned with items

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterItems":
        items = [Item.from_dict(i) for i in data.get("items", [])]
        return cls(
            items=items,
            character=data.get("character", {}),
        )

    def get_item_by_slot(self, slot: str) -> Optional[Item]:
        """Get item in a specific slot."""
        for item in self.items:
            if item.inventory_id == slot:
                return item
        return None


@dataclass
class PassiveTree:
    """
    Passive skill tree data from get-passive-skills endpoint.

    Contains allocated nodes, masteries, and jewel socket information.
    """
    hashes: List[int]  # Allocated passive node IDs
    hashes_ex: List[int]  # Extended hashes (cluster jewel nodes)
    mastery_effects: Dict[int, int]  # node_id -> effect_id
    jewel_data: Dict[str, Any]  # Jewel socket allocations

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PassiveTree":
        # Parse mastery effects from the API format
        mastery_raw = data.get("mastery_effects", {})
        mastery_effects = {}
        if isinstance(mastery_raw, dict):
            mastery_effects = {int(k): int(v) for k, v in mastery_raw.items()}

        return cls(
            hashes=data.get("hashes", []),
            hashes_ex=data.get("hashes_ex", []),
            mastery_effects=mastery_effects,
            jewel_data=data.get("jewel_data", {}),
        )

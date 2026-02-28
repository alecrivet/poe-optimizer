"""
Timeless Jewel Data Parser

Parses PoB's TimelessJewelData files to provide transformation lookup functionality.
The data comes in two forms:
1. Binary lookup tables (.bin files) - One byte per node/seed combination
2. LegionPassives.lua - Defines the additions and node replacements

Data format (from PoB):
- Jewel types: 1=Glorious Vanity, 2=Lethal Pride, 3=Brutal Restraint, 4=Militant Faith, 5=Elegant Hubris
- Each .bin file contains a lookup table indexed by (nodeIndex, seedOffset)
- The lookup value is an index into the LegionPassives additions/nodes list

For non-GV jewels:
- Values < 94 (timelessJewelAdditions) are addition indices
- Values >= 94 are replacement node indices (subtract 94 to get index)

For GV (Glorious Vanity):
- More complex format with variable-length records per node/seed
- Each record can contain multiple additions or a single replacement
"""

import logging
import re
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# Timeless jewel type IDs (matches PoB)
JEWEL_TYPE_IDS = {
    "GloriousVanity": 1,
    "LethalPride": 2,
    "BrutalRestraint": 3,
    "MilitantFaith": 4,
    "ElegantHubris": 5,
}

# Seed ranges for each jewel type (from PoB Data.lua)
SEED_RANGES = {
    1: (100, 8000),         # Glorious Vanity
    2: (10000, 18000),      # Lethal Pride
    3: (500, 8000),         # Brutal Restraint
    4: (2000, 10000),       # Militant Faith
    5: (100, 8000),         # Elegant Hubris (divided by 20 in storage)
}

# Number of "additions" vs "replacements" in LegionPassives
TIMELESS_JEWEL_ADDITIONS = 94


@dataclass
class TimelessNodeMod:
    """
    Represents a single modifier from a timeless jewel transformation.

    Attributes:
        stat_id: Internal stat ID string (e.g., "fire_damage_+%")
        stat_value: The value for this stat
        stat_text: Human-readable text (e.g., "10% increased Fire Damage")
    """
    stat_id: str
    stat_value: float
    stat_text: str

    def __repr__(self) -> str:
        return f"TimelessNodeMod({self.stat_text!r})"


@dataclass
class TimelessTransformation:
    """
    Represents the transformation applied to a single node by a timeless jewel.

    Attributes:
        original_node_id: The passive tree node ID being transformed
        mods: List of modifiers applied (additions or replacements)
        replaces_original: True if this replaces the original node entirely (Elegant Hubris)
        replacement_name: Name of the replacement node (if applicable)
    """
    original_node_id: int
    mods: List[TimelessNodeMod] = field(default_factory=list)
    replaces_original: bool = False
    replacement_name: Optional[str] = None

    def __repr__(self) -> str:
        if self.replaces_original:
            return f"TimelessTransformation(node={self.original_node_id}, replaces with {self.replacement_name})"
        return f"TimelessTransformation(node={self.original_node_id}, adds {len(self.mods)} mods)"


@dataclass
class LegionPassive:
    """
    A passive from LegionPassives.lua.

    These are either additions (mods added to existing nodes) or
    replacement nodes (entirely new nodes for GV/EH).
    """
    index: int
    id: str
    name: str  # Display name (dn)
    stats: List[str]  # Human readable stat descriptions (sd)
    stat_ids: List[str]  # Internal stat IDs
    stat_values: Dict[str, Tuple[float, float]]  # stat_id -> (min, max)
    is_keystone: bool = False
    is_notable: bool = False

    def get_mod_text(self, value: Optional[float] = None) -> str:
        """Get the stat text, optionally with a specific value."""
        if self.stats:
            return self.stats[0]
        return self.name


class TimelessJewelDataLoader:
    """
    Lazy loader for timeless jewel transformation data.

    This class manages loading and caching of the large timeless jewel
    lookup tables from PoB's data files.

    Usage:
        loader = TimelessJewelDataLoader()
        loader.load_jewel_type("LethalPride")
        transformations = loader.get_transformations("LethalPride", 15000, {26725, 26196})
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize the loader.

        Args:
            data_dir: Path to TimelessJewelData directory.
                     If None, uses PathOfBuilding/src/Data/TimelessJewelData/
        """
        if data_dir is None:
            # Find relative to this file
            module_dir = Path(__file__).parent
            project_root = module_dir.parent.parent.parent
            data_dir = project_root / "PathOfBuilding" / "src" / "Data" / "TimelessJewelData"

        self.data_dir = Path(data_dir)

        # Cached data
        self._lut_cache: Dict[int, bytes] = {}  # jewel_type_id -> raw LUT data
        self._gv_cache: Dict[int, bytes] = {}   # node_index -> decompressed per-node data
        self._gv_sizes: Optional[bytes] = None  # Size table for GV

        # Legion passives (shared across all jewel types)
        self._additions: List[LegionPassive] = []
        self._nodes: List[LegionPassive] = []
        self._node_index_map: Dict[int, Tuple[int, int]] = {}  # node_id -> (index, size)
        self._total_nodes: int = 0
        self._notable_count: int = 450

        self._legion_loaded = False
        self._node_index_loaded = False

    def _ensure_legion_loaded(self):
        """Load LegionPassives.lua if not already loaded."""
        if self._legion_loaded:
            return

        legion_path = self.data_dir / "LegionPassives.lua"
        if not legion_path.exists():
            logger.warning(f"LegionPassives.lua not found at {legion_path}")
            self._legion_loaded = True
            return

        self._parse_legion_passives(legion_path)
        self._legion_loaded = True

    def _ensure_node_index_loaded(self):
        """Load NodeIndexMapping.lua if not already loaded."""
        if self._node_index_loaded:
            return

        mapping_path = self.data_dir / "NodeIndexMapping.lua"
        if not mapping_path.exists():
            logger.warning(f"NodeIndexMapping.lua not found at {mapping_path}")
            self._node_index_loaded = True
            return

        self._parse_node_index_mapping(mapping_path)
        self._node_index_loaded = True

    def _parse_node_index_mapping(self, path: Path):
        """Parse NodeIndexMapping.lua to get node ID -> index mapping."""
        content = path.read_text()

        # Extract nodeIDList[node_id] = { index = X, size = Y }
        pattern = r'nodeIDList\[(\d+)\]\s*=\s*\{\s*index\s*=\s*(\d+)\s*,\s*size\s*=\s*(\d+)\s*\}'

        for match in re.finditer(pattern, content):
            node_id = int(match.group(1))
            index = int(match.group(2))
            size = int(match.group(3))
            self._node_index_map[node_id] = (index, size)

        # Also get total size and notable count
        size_match = re.search(r'nodeIDList\["size"\]\s*=\s*(\d+)', content)
        notable_match = re.search(r'nodeIDList\["sizeNotable"\]\s*=\s*(\d+)', content)

        if size_match:
            self._total_nodes = int(size_match.group(1))
        else:
            self._total_nodes = len(self._node_index_map)

        if notable_match:
            self._notable_count = int(notable_match.group(1))
        else:
            self._notable_count = 450  # Default from PoB

        logger.debug(f"Loaded {len(self._node_index_map)} node index mappings")

    def _parse_legion_passives(self, path: Path):
        """Parse LegionPassives.lua to get additions and replacement nodes."""
        content = path.read_text()

        # Find the nodes section
        nodes_match = re.search(r'\["nodes"\]\s*=\s*\{', content)
        if not nodes_match:
            logger.warning("Could not find nodes section in LegionPassives.lua")
            return

        # Parse each node entry using a simpler approach
        # We look for patterns like [N] = { ... } where N is a number
        node_pattern = r'\[(\d+)\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'

        for match in re.finditer(node_pattern, content[nodes_match.start():]):
            index = int(match.group(1))
            node_content = match.group(2)

            # Extract fields
            id_match = re.search(r'\["id"\]\s*=\s*"([^"]+)"', node_content)
            dn_match = re.search(r'\["dn"\]\s*=\s*"([^"]+)"', node_content)
            ks_match = re.search(r'\["ks"\]\s*=\s*(true|false)', node_content)
            not_match = re.search(r'\["not"\]\s*=\s*(true|false)', node_content)

            # Extract stat descriptions (sd)
            sd_match = re.search(r'\["sd"\]\s*=\s*\{([^}]*)\}', node_content)
            stats = []
            if sd_match:
                for stat_match in re.finditer(r'\[\d+\]\s*=\s*"([^"]+)"', sd_match.group(1)):
                    stats.append(stat_match.group(1))

            # Extract stat IDs from sortedStats
            sorted_stats_match = re.search(r'\["sortedStats"\]\s*=\s*\{([^}]*)\}', node_content)
            stat_ids = []
            if sorted_stats_match:
                for stat_match in re.finditer(r'\[\d+\]\s*=\s*"([^"]+)"', sorted_stats_match.group(1)):
                    stat_ids.append(stat_match.group(1))

            # Extract stat value ranges (simplified)
            stat_values: Dict[str, Tuple[float, float]] = {}
            stats_section_match = re.search(
                r'\["stats"\]\s*=\s*\{(.*?)\},\s*\["da"\]',
                node_content, re.DOTALL
            )
            if stats_section_match:
                stats_content = stats_section_match.group(1)
                stat_entry_pattern = (
                    r'\["([^"]+)"\]\s*=\s*\{[^}]*'
                    r'\["min"\]\s*=\s*([\d.]+)[^}]*'
                    r'\["max"\]\s*=\s*([\d.]+)'
                )
                for stat_entry in re.finditer(stat_entry_pattern, stats_content, re.DOTALL):
                    stat_id = stat_entry.group(1)
                    min_val = float(stat_entry.group(2))
                    max_val = float(stat_entry.group(3))
                    stat_values[stat_id] = (min_val, max_val)

            passive = LegionPassive(
                index=index,
                id=id_match.group(1) if id_match else f"unknown_{index}",
                name=dn_match.group(1) if dn_match else f"Unknown {index}",
                stats=stats,
                stat_ids=stat_ids,
                stat_values=stat_values,
                is_keystone=ks_match is not None and ks_match.group(1) == "true",
                is_notable=not_match is not None and not_match.group(1) == "true",
            )

            # First 94 entries are additions, rest are replacement nodes
            if index <= TIMELESS_JEWEL_ADDITIONS:
                self._additions.append(passive)
            else:
                self._nodes.append(passive)

        logger.debug(f"Loaded {len(self._additions)} additions and {len(self._nodes)} replacement nodes")

    def _load_bin_file(self, jewel_type: str) -> Optional[bytes]:
        """Load a .bin file, decompressing from .zip if needed."""
        bin_path = self.data_dir / f"{jewel_type}.bin"

        if bin_path.exists() and bin_path.stat().st_size > 0:
            return bin_path.read_bytes()

        # Try to decompress from zip
        zip_path = self.data_dir / f"{jewel_type}.zip"
        if zip_path.exists():
            try:
                compressed = zip_path.read_bytes()
                return self._decompress_zlib(compressed)
            except Exception as e:
                logger.error(f"Failed to decompress {zip_path}: {e}")

        # Handle split files (GloriousVanity)
        part_files = sorted(self.data_dir.glob(f"{jewel_type}.zip.part*"))
        if part_files:
            try:
                compressed = b""
                for part in part_files:
                    compressed += part.read_bytes()
                return self._decompress_zlib(compressed)
            except Exception as e:
                logger.error(f"Failed to decompress split files for {jewel_type}: {e}")

        return None

    def _decompress_zlib(self, data: bytes) -> bytes:
        """Decompress raw zlib/deflate data."""
        for wbits in [-15, 15, -zlib.MAX_WBITS, zlib.MAX_WBITS]:
            try:
                return zlib.decompress(data, wbits)
            except zlib.error:
                continue

        # Last resort
        return zlib.decompress(data)

    def load_jewel_type(self, jewel_type: str) -> bool:
        """
        Lazy load data for a jewel type.

        Args:
            jewel_type: One of 'GloriousVanity', 'LethalPride', 'BrutalRestraint',
                       'MilitantFaith', 'ElegantHubris'

        Returns:
            True if data was loaded successfully
        """
        # Normalize name
        jewel_type = jewel_type.replace(" ", "")

        type_id = JEWEL_TYPE_IDS.get(jewel_type)
        if type_id is None:
            logger.error(f"Unknown jewel type: {jewel_type}")
            return False

        if type_id in self._lut_cache:
            return True

        # Ensure supporting data is loaded
        self._ensure_legion_loaded()
        self._ensure_node_index_loaded()

        # Load the lookup table
        data = self._load_bin_file(jewel_type)
        if data is None:
            logger.warning(f"Could not load data for {jewel_type}")
            return False

        if type_id == 1:  # Glorious Vanity
            # GV has a more complex format with per-node data
            self._load_gv_data(data)
        else:
            self._lut_cache[type_id] = data

        logger.info(f"Loaded timeless jewel data for {jewel_type}")
        return True

    def _load_gv_data(self, data: bytes):
        """Load Glorious Vanity data which has a special format."""
        seed_size = SEED_RANGES[1][1] - SEED_RANGES[1][0] + 1
        size_table_len = self._total_nodes * seed_size

        # First part is the size table
        self._gv_sizes = data[:size_table_len + 1]

        # Rest is per-node data, we'll load on demand
        offset = size_table_len + 1
        for node_id, (index, node_size) in self._node_index_map.items():
            # Store raw data for this node
            self._gv_cache[index] = data[offset:offset + node_size]
            offset += node_size

        # Mark as loaded
        self._lut_cache[1] = b""

    def is_loaded(self, jewel_type: str) -> bool:
        """Check if jewel type data is loaded."""
        jewel_type = jewel_type.replace(" ", "")
        type_id = JEWEL_TYPE_IDS.get(jewel_type)
        return type_id is not None and type_id in self._lut_cache

    def get_transformations(
        self,
        jewel_type: str,
        seed: int,
        node_ids: Set[int]
    ) -> Dict[int, TimelessTransformation]:
        """
        Get transformations for nodes with given seed.

        Args:
            jewel_type: Jewel type name
            seed: The jewel's seed value
            node_ids: Set of passive tree node IDs to check

        Returns:
            Dict mapping node_id -> transformation for that node
        """
        jewel_type_normalized = jewel_type.replace(" ", "")
        type_id = JEWEL_TYPE_IDS.get(jewel_type_normalized)

        if type_id is None or not self.is_loaded(jewel_type_normalized):
            if not self.load_jewel_type(jewel_type_normalized):
                return {}

        transformations = {}

        for node_id in node_ids:
            transform = self._get_single_transformation(type_id, seed, node_id)
            if transform:
                transformations[node_id] = transform

        return transformations

    def _get_single_transformation(
        self,
        type_id: int,
        seed: int,
        node_id: int
    ) -> Optional[TimelessTransformation]:
        """Get transformation for a single node."""
        # Check if node is in the mapping
        if node_id not in self._node_index_map:
            return None

        node_index, _ = self._node_index_map[node_id]

        # Calculate seed offset
        seed_min, seed_max = SEED_RANGES[type_id]

        # Elegant Hubris seeds are divided by 20 in storage
        lookup_seed = seed
        if type_id == 5:
            lookup_seed = seed // 20

        if lookup_seed < seed_min or lookup_seed > seed_max:
            return None

        seed_offset = lookup_seed - seed_min
        seed_size = seed_max - seed_min + 1

        if type_id == 1:  # Glorious Vanity
            return self._get_gv_transformation(node_id, node_index, seed_offset, seed_size)
        else:
            return self._get_simple_transformation(type_id, node_id, node_index, seed_offset, seed_size)

    def _get_simple_transformation(
        self,
        type_id: int,
        node_id: int,
        node_index: int,
        seed_offset: int,
        seed_size: int
    ) -> Optional[TimelessTransformation]:
        """Get transformation for non-GV jewel types."""
        data = self._lut_cache.get(type_id)
        if data is None:
            return None

        # Check if this is a notable (only notables get transformations for non-GV)
        if node_index > self._notable_count:
            # Small nodes just get attribute bonuses, not from LUT
            return self._get_small_node_transformation(type_id, node_id)

        # Calculate byte offset
        byte_index = node_index * seed_size + seed_offset
        if byte_index >= len(data):
            return None

        lut_value = data[byte_index]
        if lut_value == 0:
            return None

        return self._transform_from_lut_value(node_id, lut_value)

    def _get_small_node_transformation(
        self,
        type_id: int,
        node_id: int
    ) -> Optional[TimelessTransformation]:
        """Get transformation for small nodes (attribute bonuses)."""
        if type_id == 2:  # Lethal Pride (Karui)
            return TimelessTransformation(
                original_node_id=node_id,
                mods=[TimelessNodeMod(
                    stat_id="strength",
                    stat_value=4,
                    stat_text="+4 to Strength"
                )],
                replaces_original=False,
            )
        elif type_id == 3:  # Brutal Restraint (Maraketh)
            return TimelessTransformation(
                original_node_id=node_id,
                mods=[TimelessNodeMod(
                    stat_id="dexterity",
                    stat_value=4,
                    stat_text="+4 to Dexterity"
                )],
                replaces_original=False,
            )
        elif type_id == 4:  # Militant Faith (Templar)
            return TimelessTransformation(
                original_node_id=node_id,
                mods=[TimelessNodeMod(
                    stat_id="devotion",
                    stat_value=5,
                    stat_text="+5 to Devotion"
                )],
                replaces_original=False,
            )
        elif type_id == 5:  # Elegant Hubris (Eternal)
            return TimelessTransformation(
                original_node_id=node_id,
                mods=[],
                replaces_original=True,
                replacement_name="Nothing"
            )

        return None

    def _get_gv_transformation(
        self,
        node_id: int,
        node_index: int,
        seed_offset: int,
        seed_size: int
    ) -> Optional[TimelessTransformation]:
        """Get transformation for Glorious Vanity (more complex format)."""
        if node_index not in self._gv_cache:
            return None

        node_data = self._gv_cache[node_index]
        if self._gv_sizes is None:
            return None

        # Parse the per-seed data for this node
        offset = 0
        for s in range(seed_offset):
            size_index = node_index * seed_size + s
            if size_index < len(self._gv_sizes):
                offset += self._gv_sizes[size_index]

        size_index = node_index * seed_size + seed_offset
        if size_index >= len(self._gv_sizes):
            return None

        record_size = self._gv_sizes[size_index]
        if record_size == 0 or offset + record_size > len(node_data):
            return None

        record = node_data[offset:offset + record_size]
        return self._parse_gv_record(node_id, record)

    def _parse_gv_record(
        self,
        node_id: int,
        record: bytes
    ) -> Optional[TimelessTransformation]:
        """Parse a Glorious Vanity record."""
        if len(record) == 0:
            return None

        header_size = len(record)

        if header_size == 2 or header_size == 3:
            replacement_idx = record[0]
            if replacement_idx < TIMELESS_JEWEL_ADDITIONS:
                return self._transform_from_addition(
                    node_id, replacement_idx, record[1] if len(record) > 1 else None
                )
            return self._transform_from_replacement(
                node_id, replacement_idx - TIMELESS_JEWEL_ADDITIONS,
                record[1] if len(record) > 1 else None
            )

        elif header_size == 6 or header_size == 8:
            half = header_size // 2
            additions = []

            for i in range(half):
                add_idx = record[i]
                roll = record[i + half]

                if add_idx < len(self._additions):
                    passive = self._additions[add_idx]
                    if passive.stats:
                        stat_text = passive.stats[0]
                        first_stat = passive.id
                        if passive.stat_values:
                            first_stat = list(passive.stat_values.keys())[0]
                            min_val, _ = passive.stat_values[first_stat]
                            actual_value = roll if roll >= min_val else min_val
                            stat_text = re.sub(r'\([\d.-]+\)', str(int(actual_value)), stat_text)
                            stat_text = re.sub(r'[\d.-]+%', f'{int(actual_value)}%', stat_text, count=1)

                        additions.append(TimelessNodeMod(
                            stat_id=first_stat,
                            stat_value=roll,
                            stat_text=stat_text
                        ))

            if additions:
                return TimelessTransformation(
                    original_node_id=node_id,
                    mods=additions,
                    replaces_original=True,
                    replacement_name="Might of the Vaal" if header_size == 6 else "Legacy of the Vaal"
                )

        return None

    def _transform_from_lut_value(
        self,
        node_id: int,
        value: int
    ) -> Optional[TimelessTransformation]:
        """Create transformation from a single LUT value."""
        if value >= TIMELESS_JEWEL_ADDITIONS:
            return self._transform_from_replacement(node_id, value - TIMELESS_JEWEL_ADDITIONS)
        else:
            return self._transform_from_addition(node_id, value)

    def _transform_from_addition(
        self,
        node_id: int,
        add_index: int,
        roll: Optional[int] = None
    ) -> Optional[TimelessTransformation]:
        """Create transformation from an addition index."""
        if add_index >= len(self._additions):
            return None

        passive = self._additions[add_index]
        mods = []

        for i, stat in enumerate(passive.stats):
            stat_id = passive.stat_ids[i] if i < len(passive.stat_ids) else passive.id
            stat_text = stat

            value: Optional[float] = roll
            if value is None and stat_id in passive.stat_values:
                min_val, max_val = passive.stat_values[stat_id]
                value = (min_val + max_val) / 2

            mods.append(TimelessNodeMod(
                stat_id=stat_id,
                stat_value=value if value is not None else 0,
                stat_text=stat_text
            ))

        return TimelessTransformation(
            original_node_id=node_id,
            mods=mods,
            replaces_original=False,
        )

    def _transform_from_replacement(
        self,
        node_id: int,
        node_index: int,
        roll: Optional[int] = None
    ) -> Optional[TimelessTransformation]:
        """Create transformation from a replacement node index."""
        if node_index >= len(self._nodes):
            return None

        passive = self._nodes[node_index]
        mods = []

        for i, stat in enumerate(passive.stats):
            stat_id = passive.stat_ids[i] if i < len(passive.stat_ids) else passive.id
            stat_text = stat

            value: Optional[float] = roll
            if value is None and stat_id in passive.stat_values:
                min_val, max_val = passive.stat_values[stat_id]
                value = (min_val + max_val) / 2

            mods.append(TimelessNodeMod(
                stat_id=stat_id,
                stat_value=value if value is not None else 0,
                stat_text=stat_text
            ))

        return TimelessTransformation(
            original_node_id=node_id,
            mods=mods,
            replaces_original=True,
            replacement_name=passive.name,
        )

    def get_addition(self, index: int) -> Optional[LegionPassive]:
        """Get an addition passive by index."""
        self._ensure_legion_loaded()
        if 0 <= index < len(self._additions):
            return self._additions[index]
        return None

    def get_replacement_node(self, index: int) -> Optional[LegionPassive]:
        """Get a replacement node by index."""
        self._ensure_legion_loaded()
        if 0 <= index < len(self._nodes):
            return self._nodes[index]
        return None

    def get_all_node_ids(self) -> Set[int]:
        """Get all node IDs that can be transformed."""
        self._ensure_node_index_loaded()
        return set(self._node_index_map.keys())


# Module-level singleton for convenience
_default_loader: Optional[TimelessJewelDataLoader] = None


def get_default_loader() -> TimelessJewelDataLoader:
    """Get the default data loader singleton."""
    global _default_loader
    if _default_loader is None:
        _default_loader = TimelessJewelDataLoader()
    return _default_loader

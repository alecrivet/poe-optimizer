"""
Build Context Extraction for Context-Aware Scoring

This module extracts build characteristics from Path of Building XML to provide
context-aware scoring for masteries, timeless jewels, and other optimizations.

Build context includes:
- Primary and secondary damage types
- Attack vs spell classification
- Defense style (life, ES, hybrid)
- Class and ascendancy
- Key mechanics (totems, minions, etc.)
- Allocated keystones

Usage:
    context = BuildContext.from_build_xml(xml)
    if context.primary_damage_type == 'fire':
        # Weight fire-related mods higher
        keyword_weights = context.get_relevant_keywords('dps')
"""

import re
import xml.etree.ElementTree as ET
import logging
from dataclasses import dataclass, field

from .tree_version import get_latest_tree_version
from typing import Dict, Set, Tuple, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


# Important keystones to detect - maps node name to a simplified identifier
KEYSTONE_NAMES = {
    "Resolute Technique": "resolute_technique",
    "Chaos Inoculation": "ci",
    "Eldritch Battery": "eb",
    "Mind Over Matter": "mom",
    "Acrobatics": "acrobatics",
    "Iron Reflexes": "iron_reflexes",
    "Ancestral Bond": "ancestral_bond",
    "Necromantic Aegis": "necromantic_aegis",
    "Avatar of Fire": "avatar_of_fire",
    "Elemental Equilibrium": "elemental_equilibrium",
    "Point Blank": "point_blank",
    "Vaal Pact": "vaal_pact",
    "Ghost Reaver": "ghost_reaver",
    "Zealot's Oath": "zealots_oath",
    "Pain Attunement": "pain_attunement",
    "Crimson Dance": "crimson_dance",
    "Perfect Agony": "perfect_agony",
    "Elemental Overload": "elemental_overload",
    "Unwavering Stance": "unwavering_stance",
    "Phase Acrobatics": "phase_acrobatics",
    "Arrow Dancing": "arrow_dancing",
    "Runebinder": "runebinder",
    "Glancing Blows": "glancing_blows",
    "Wind Dancer": "wind_dancer",
    "The Agnostic": "the_agnostic",
    "Supreme Ego": "supreme_ego",
    "Mortal Conviction": "mortal_conviction",
    "Blood Magic": "blood_magic",
    "Call to Arms": "call_to_arms",
    "The Impaler": "the_impaler",
    "Precise Technique": "precise_technique",
    "Imbalanced Guard": "imbalanced_guard",
}

# Gem tags that indicate damage types
DAMAGE_TYPE_GEMS = {
    "physical": ["Melee Physical Damage", "Brutality", "Impale", "Chance to Bleed"],
    "fire": ["Combustion", "Immolate", "Fire Penetration", "Burning Damage", "Ignite Proliferation"],
    "cold": ["Hypothermia", "Ice Bite", "Cold Penetration", "Bonechill"],
    "lightning": ["Lightning Penetration", "Innervate", "Added Lightning Damage", "Shock Nova"],
    "chaos": ["Void Manipulation", "Withering Touch", "Decay", "Added Chaos Damage"],
}

# Gems that indicate attack vs spell
ATTACK_GEMS = {
    "Melee Physical Damage", "Multistrike", "Ruthless", "Close Combat",
    "Rage", "Pulverise", "Shockwave", "Fortify", "Ancestral Call",
    "Melee Splash", "Impale", "Chance to Bleed", "Brutality",
    "Point Blank Support", "Barrage Support", "Volley", "Greater Multiple Projectiles",
    "Lesser Multiple Projectiles", "Fork", "Chain", "Pierce", "Mirage Archer",
    "Awakened Melee Physical Damage", "Awakened Brutality"
}

SPELL_GEMS = {
    "Spell Echo", "Spell Cascade", "Unleash", "Intensify", "Arcane Surge",
    "Controlled Destruction", "Elemental Focus", "Concentrated Effect",
    "Increased Area of Effect", "Faster Casting", "Spell Totem",
    "Awakened Spell Echo", "Awakened Controlled Destruction"
}

# Gems that indicate mechanics
MECHANIC_GEMS = {
    "totems": ["Spell Totem", "Ballista Totem", "Ancestral Warchief", "Ancestral Protector"],
    "brands": ["Arcanist Brand", "Penance Brand", "Wintertide Brand", "Storm Brand", "Armageddon Brand"],
    "traps": ["Trap", "Cluster Traps", "Multiple Traps", "Advanced Traps"],
    "mines": ["Minefield", "Swift Assembly", "High-Impact Mine", "Blastchain Mine"],
    "minions": ["Minion Damage", "Minion Life", "Minion Speed", "Raise Zombie",
                "Summon Skeleton", "Raise Spectre", "Animate Guardian"],
}

# Base damage type skill indicators (skill name substrings)
SKILL_DAMAGE_HINTS = {
    "fire": ["Fire", "Flame", "Burn", "Ignite", "Inferno", "Blaze", "Magma", "Lava", "Molten", "Scorch"],
    "cold": ["Cold", "Ice", "Frost", "Freeze", "Chill", "Arctic", "Winter", "Glacial", "Frigid"],
    "lightning": ["Lightning", "Shock", "Spark", "Storm", "Thunder", "Arc", "Galvanic", "Electro"],
    "chaos": ["Chaos", "Poison", "Wither", "Blight", "Contagion", "Essence Drain", "Bane", "Despair"],
    "physical": ["Bleed", "Impale", "Lacerate", "Sunder", "Earthquake", "Ground Slam", "Cyclone",
                 "Bladestorm", "Cleave", "Double Strike", "Puncture"],
}


@dataclass
class BuildContext:
    """
    Extracted build characteristics for context-aware scoring.

    This class captures the key attributes of a build that affect how
    modifiers should be valued during optimization.
    """

    # Damage characteristics
    primary_damage_type: str = "physical"  # 'physical', 'fire', 'cold', 'lightning', 'chaos'
    secondary_damage_types: Set[str] = field(default_factory=set)
    damage_style: str = "hit"  # 'hit', 'dot', 'minion'
    attack_or_spell: str = "attack"  # 'attack', 'spell', 'both'

    # Defense characteristics
    defense_style: str = "life"  # 'life', 'es', 'hybrid'
    primary_mitigation: str = "armor"  # 'armor', 'evasion', 'block', 'dodge'

    # Class/Ascendancy
    character_class: str = "Unknown"  # 'Marauder', 'Witch', etc.
    ascendancy: str = "None"  # 'Slayer', 'Necromancer', etc.

    # Mechanics
    key_mechanics: Set[str] = field(default_factory=set)  # 'totems', 'brands', 'traps', 'mines', 'minions'
    key_keystones: Set[str] = field(default_factory=set)  # 'resolute_technique', 'ci', etc.

    # Raw data for reference
    main_skill_name: str = ""

    @classmethod
    def from_build_xml(cls, xml: str) -> "BuildContext":
        """
        Extract context from PoB build XML.

        Args:
            xml: Path of Building XML string

        Returns:
            BuildContext with extracted characteristics
        """
        extractor = BuildContextExtractor()
        return extractor.extract(xml)

    def get_relevant_keywords(self, objective: str = "dps") -> Dict[str, float]:
        """
        Get context-aware keyword weights for scoring.

        Returns a dictionary mapping keywords to their relevance multipliers
        based on the build's characteristics and optimization objective.

        Args:
            objective: Optimization objective ('dps', 'life', 'ehp', 'balanced')

        Returns:
            Dict mapping keywords to weight multipliers (0.0 to 2.0)
        """
        weights: Dict[str, float] = {}

        # Base weights for all damage types
        all_damage_types = ["physical", "fire", "cold", "lightning", "chaos"]

        # Initialize all damage types with base weights
        for dtype in all_damage_types:
            if dtype == self.primary_damage_type:
                weights[dtype] = 1.5
            elif dtype in self.secondary_damage_types:
                weights[dtype] = 1.2
            else:
                weights[dtype] = 0.5

        # Objective-specific adjustments
        if objective == "dps":
            self._add_dps_keywords(weights)
        elif objective == "life":
            self._add_life_keywords(weights)
        elif objective == "ehp":
            self._add_ehp_keywords(weights)
        elif objective == "balanced":
            self._add_dps_keywords(weights, multiplier=0.5)
            self._add_life_keywords(weights, multiplier=0.5)
            self._add_ehp_keywords(weights, multiplier=0.5)

        # Attack vs Spell adjustments
        if self.attack_or_spell == "attack":
            weights["attack"] = 1.5
            weights["spell"] = 0.3
            weights["accuracy"] = 1.3
            weights["melee"] = 1.4 if "melee" in self.main_skill_name.lower() else 1.0
        elif self.attack_or_spell == "spell":
            weights["spell"] = 1.5
            weights["attack"] = 0.3
            weights["cast speed"] = 1.3
        else:
            weights["attack"] = 1.0
            weights["spell"] = 1.0

        # Damage style adjustments
        if self.damage_style == "dot":
            weights["damage over time"] = 1.5
            weights["dot"] = 1.5
            weights["ailment"] = 1.3
            if self.primary_damage_type == "physical":
                weights["bleed"] = 1.5
                weights["bleeding"] = 1.5
            elif self.primary_damage_type == "fire":
                weights["ignite"] = 1.5
                weights["burning"] = 1.5
            elif self.primary_damage_type == "chaos":
                weights["poison"] = 1.5
        elif self.damage_style == "hit":
            weights["hit"] = 1.2
            weights["damage over time"] = 0.6
        elif self.damage_style == "minion":
            weights["minion"] = 1.5
            weights["minions"] = 1.5

        # Mechanic-based adjustments
        for mechanic in self.key_mechanics:
            weights[mechanic] = 1.5
            weights[mechanic.rstrip("s")] = 1.5  # singular form

        # Defense style adjustments (keystones will override below)
        if self.defense_style == "es":
            weights["energy shield"] = 1.5
            weights["es"] = 1.5
            weights["life"] = 0.3
        elif self.defense_style == "life":
            weights["life"] = 1.5
            weights["maximum life"] = 1.5
            weights["energy shield"] = 0.5
        elif self.defense_style == "hybrid":
            weights["life"] = 1.2
            weights["energy shield"] = 1.2

        # Mitigation adjustments
        if self.primary_mitigation == "armor":
            weights["armor"] = 1.3
            weights["armour"] = 1.3
            weights["physical damage reduction"] = 1.3
        elif self.primary_mitigation == "evasion":
            weights["evasion"] = 1.3
            weights["dodge"] = 1.2
        elif self.primary_mitigation == "block":
            weights["block"] = 1.4
            weights["spell block"] = 1.3

        # Keystone-based adjustments (override defense/mitigation defaults)
        if "resolute_technique" in self.key_keystones:
            weights["critical"] = 0.1
            weights["crit"] = 0.1
        else:
            weights["critical"] = 1.2
            weights["crit"] = 1.2

        if "ci" in self.key_keystones:
            weights["life"] = 0.1
            weights["energy shield"] = 1.5
            weights["es"] = 1.5

        if "acrobatics" in self.key_keystones:
            weights["evasion"] = 1.3
            weights["dodge"] = 1.3
            weights["armor"] = 0.5
            weights["armour"] = 0.5

        if "iron_reflexes" in self.key_keystones:
            weights["armor"] = 1.4
            weights["armour"] = 1.4
            weights["evasion"] = 1.2  # Still valuable as it converts

        if "mom" in self.key_keystones:
            weights["mana"] = 1.3

        if "avatar_of_fire" in self.key_keystones:
            weights["fire"] = 1.5
            weights["cold"] = 0.8
            weights["lightning"] = 0.8
            weights["physical"] = 0.8

        if "pain_attunement" in self.key_keystones:
            weights["low life"] = 1.3

        if "crimson_dance" in self.key_keystones:
            weights["bleed"] = 1.5
            weights["bleeding"] = 1.5

        if "perfect_agony" in self.key_keystones:
            weights["critical"] = 1.4
            weights["ailment"] = 1.3

        if "the_impaler" in self.key_keystones:
            weights["impale"] = 1.5

        return weights

    def _add_dps_keywords(self, weights: Dict[str, float], multiplier: float = 1.0) -> None:
        """Add DPS-related keywords to weights."""
        dps_keywords = {
            "damage": 1.3,
            "increased damage": 1.3,
            "more damage": 1.5,
            "penetration": 1.4,
            "attack speed": 1.3,
            "cast speed": 1.3,
            "critical strike": 1.2,
            "critical strike chance": 1.2,
            "critical strike multiplier": 1.3,
            "impale": 1.2,
            "area of effect": 1.1,
            "projectile": 1.1,
        }

        for keyword, weight in dps_keywords.items():
            adjusted = 1.0 + (weight - 1.0) * multiplier
            weights[keyword] = max(weights.get(keyword, 1.0), adjusted)

    def _add_life_keywords(self, weights: Dict[str, float], multiplier: float = 1.0) -> None:
        """Add life/recovery-related keywords to weights."""
        life_keywords = {
            "maximum life": 1.5,
            "life regeneration": 1.3,
            "life recovery": 1.4,
            "life leech": 1.3,
            "life gained": 1.2,
            "life on hit": 1.2,
            "life flask": 1.1,
        }

        for keyword, weight in life_keywords.items():
            adjusted = 1.0 + (weight - 1.0) * multiplier
            weights[keyword] = max(weights.get(keyword, 1.0), adjusted)

    def _add_ehp_keywords(self, weights: Dict[str, float], multiplier: float = 1.0) -> None:
        """Add EHP/defense-related keywords to weights."""
        ehp_keywords = {
            "maximum resistances": 1.5,
            "block": 1.3,
            "spell suppression": 1.4,
            "armour": 1.2,
            "armor": 1.2,
            "evasion": 1.2,
            "energy shield": 1.3,
            "physical damage reduction": 1.4,
            "reduced damage taken": 1.5,
            "fortify": 1.3,
            "endurance charge": 1.2,
        }

        for keyword, weight in ehp_keywords.items():
            adjusted = 1.0 + (weight - 1.0) * multiplier
            weights[keyword] = max(weights.get(keyword, 1.0), adjusted)

    def is_crit_build(self) -> bool:
        """Check if this is a crit-based build."""
        return "resolute_technique" not in self.key_keystones

    def is_dot_build(self) -> bool:
        """Check if this is a damage-over-time build."""
        return self.damage_style == "dot"

    def is_minion_build(self) -> bool:
        """Check if this is a minion build."""
        return self.damage_style == "minion" or "minions" in self.key_mechanics


class BuildContextExtractor:
    """
    Extracts build context from Path of Building XML.

    Uses multiple extraction methods to determine build characteristics:
    - Parse ascendancy from <Build> and <Spec> elements
    - Analyze skills for damage types and mechanics
    - Check allocated nodes for keystones
    - Analyze gear for defense style hints
    """

    def __init__(self, pob_path: str = "./PathOfBuilding", tree_version: Optional[str] = None):
        """
        Initialize the extractor.

        Args:
            pob_path: Path to PathOfBuilding directory (for keystone node IDs)
            tree_version: Tree version string. If None, auto-detects latest.
        """
        self.pob_path = Path(pob_path)
        if tree_version is None:
            tree_version = get_latest_tree_version(pob_path) or "3_27"
        self.tree_version = tree_version
        self._keystone_ids: Optional[Dict[int, str]] = None

    def extract(self, build_xml: str) -> BuildContext:
        """
        Full extraction pipeline.

        Args:
            build_xml: Path of Building XML string

        Returns:
            BuildContext with all extracted characteristics
        """
        try:
            root = ET.fromstring(build_xml)
        except ET.ParseError as e:
            logger.error(f"Failed to parse build XML: {e}")
            return BuildContext()

        # Extract class and ascendancy
        character_class, ascendancy = self._parse_ascendancy(root)

        # Analyze skills
        skill_analysis = self._analyze_skills(root)

        # Analyze keystones from tree
        keystones = self._analyze_keystones(root)

        # Analyze defenses
        defense_analysis = self._analyze_defenses(root, keystones)

        # Determine primary damage type
        primary_damage, secondary_damage = self._determine_damage_types(skill_analysis)

        # Determine attack vs spell
        attack_or_spell = self._determine_attack_or_spell(skill_analysis)

        # Determine damage style (hit, dot, minion)
        damage_style = self._determine_damage_style(skill_analysis, keystones)

        # Extract key mechanics
        key_mechanics = self._extract_mechanics(skill_analysis)

        return BuildContext(
            primary_damage_type=primary_damage,
            secondary_damage_types=secondary_damage,
            damage_style=damage_style,
            attack_or_spell=attack_or_spell,
            defense_style=defense_analysis.get("style", "life"),
            primary_mitigation=defense_analysis.get("mitigation", "armor"),
            character_class=character_class,
            ascendancy=ascendancy,
            key_mechanics=key_mechanics,
            key_keystones=keystones,
            main_skill_name=skill_analysis.get("main_skill", ""),
        )

    def _parse_ascendancy(self, root: ET.Element) -> Tuple[str, str]:
        """
        Extract class and ascendancy from Build element.

        Args:
            root: XML root element

        Returns:
            Tuple of (class_name, ascendancy_name)
        """
        build_elem = root.find("Build")
        if build_elem is None:
            return ("Unknown", "None")

        class_name = build_elem.get("className", "Unknown")
        ascendancy = build_elem.get("ascendClassName", "None")

        logger.debug(f"Parsed ascendancy: {class_name}/{ascendancy}")

        return (class_name, ascendancy)

    def _analyze_skills(self, root: ET.Element) -> Dict[str, Any]:
        """
        Analyze active skills for damage types and mechanics.

        Args:
            root: XML root element

        Returns:
            Dict with skill analysis results
        """
        result = {
            "main_skill": "",
            "damage_types": set(),
            "is_attack": False,
            "is_spell": False,
            "is_dot": False,
            "is_minion": False,
            "mechanics": set(),
            "support_gems": [],
            "active_gems": [],
        }

        skills_elem = root.find("Skills")
        if skills_elem is None:
            return result

        # Get active skill set
        active_set_id = skills_elem.get("activeSkillSet", "1")
        skill_set = skills_elem.find(f".//SkillSet[@id='{active_set_id}']")
        if skill_set is None:
            skill_set = skills_elem.find(".//SkillSet")
        if skill_set is None:
            return result

        # Find main skill group (marked with includeInFullDPS or mainSocketGroup)
        main_socket_group = root.find("Build")
        main_socket_idx = int(main_socket_group.get("mainSocketGroup", "1")) if main_socket_group is not None else 1

        all_skill_groups = list(skill_set.findall("Skill"))

        # Analyze each skill group
        for idx, skill_elem in enumerate(all_skill_groups, 1):
            if skill_elem.get("enabled", "true") != "true":
                continue

            is_main = (idx == main_socket_idx) or (skill_elem.get("includeInFullDPS") == "true" and
                                                   skill_elem.get("mainActiveSkill") == "1")

            gems = skill_elem.findall("Gem")
            for gem in gems:
                if gem.get("enabled", "true") != "true":
                    continue

                gem_name = gem.get("nameSpec", "")
                skill_id = gem.get("skillId", "")

                # Classify gem
                if gem_name in ATTACK_GEMS or "Attack" in skill_id:
                    result["is_attack"] = True
                if gem_name in SPELL_GEMS or "Spell" in skill_id:
                    result["is_spell"] = True

                # Check for support gems that indicate damage type
                for dtype, gem_list in DAMAGE_TYPE_GEMS.items():
                    if any(g.lower() in gem_name.lower() for g in gem_list):
                        result["damage_types"].add(dtype)

                # Check for mechanic gems
                for mechanic, gem_list in MECHANIC_GEMS.items():
                    if any(g.lower() in gem_name.lower() for g in gem_list):
                        result["mechanics"].add(mechanic)
                        if mechanic == "minions":
                            result["is_minion"] = True

                # Track if gem is a support
                if "Support" in skill_id or gem_name in ATTACK_GEMS or gem_name in SPELL_GEMS:
                    result["support_gems"].append(gem_name)
                else:
                    result["active_gems"].append(gem_name)

                    # Main skill detection
                    if is_main and not result["main_skill"]:
                        result["main_skill"] = gem_name

                    # Infer damage type from skill name
                    for dtype, hints in SKILL_DAMAGE_HINTS.items():
                        if any(hint.lower() in gem_name.lower() for hint in hints):
                            result["damage_types"].add(dtype)

        # Check for DoT indicators
        dot_indicators = ["burning", "bleed", "poison", "ignite", "decay", "blight",
                        "wither", "essence drain", "contagion", "vortex", "cold snap"]
        for gem in result["active_gems"]:
            if any(indicator in gem.lower() for indicator in dot_indicators):
                result["is_dot"] = True
                break

        # Check support gems for DoT
        for gem in result["support_gems"]:
            if any(s in gem.lower() for s in ["burning", "bleed", "decay", "swift affliction",
                                                "efficacy", "unbound ailments"]):
                result["is_dot"] = True
                break

        logger.debug(f"Skill analysis: main={result['main_skill']}, damage_types={result['damage_types']}")

        return result

    def _analyze_keystones(self, root: ET.Element) -> Set[str]:
        """
        Find allocated keystones from the passive tree.

        Args:
            root: XML root element

        Returns:
            Set of keystone identifiers (e.g., 'resolute_technique', 'ci')
        """
        keystones: Set[str] = set()

        # Get allocated node IDs
        tree_elem = root.find(".//Tree")
        if tree_elem is None:
            return keystones

        spec_elem = tree_elem.find(".//Spec")
        if spec_elem is None:
            return keystones

        nodes_str = spec_elem.get("nodes", "")
        if not nodes_str:
            return keystones

        allocated_nodes = set(int(n) for n in nodes_str.split(",") if n.strip())

        # Load keystone node IDs if not already loaded
        if self._keystone_ids is None:
            self._keystone_ids = self._load_keystone_ids()

        # Check which keystones are allocated
        for node_id in allocated_nodes:
            if node_id in self._keystone_ids:
                keystones.add(self._keystone_ids[node_id])

        logger.debug(f"Found keystones: {keystones}")

        return keystones

    def _load_keystone_ids(self) -> Dict[int, str]:
        """
        Load keystone node IDs from PathOfBuilding tree data.

        Returns:
            Dict mapping node_id -> keystone identifier
        """
        result: Dict[int, str] = {}

        tree_file = self.pob_path / "src" / "TreeData" / self.tree_version / "tree.lua"

        if not tree_file.exists():
            logger.warning(f"Tree file not found: {tree_file}")
            return result

        try:
            with open(tree_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except IOError as e:
            logger.error(f"Failed to read tree file: {e}")
            return result

        # Find keystone nodes
        # Pattern: [nodeId]= { ... ["isKeystone"]= true ... ["name"]= "..." }
        node_blocks = re.split(r'\[(\d+)\]\s*=\s*\{', content)

        for i in range(1, len(node_blocks), 2):
            node_id_str = node_blocks[i]
            node_content = node_blocks[i + 1] if i + 1 < len(node_blocks) else ""

            # Check if this is a keystone
            if '["isKeystone"]' not in node_content or 'true' not in node_content:
                continue

            # Extract name
            name_match = re.search(r'\["name"\]\s*=\s*"([^"]+)"', node_content)
            if name_match:
                name = name_match.group(1)
                if name in KEYSTONE_NAMES:
                    try:
                        node_id = int(node_id_str)
                        result[node_id] = KEYSTONE_NAMES[name]
                    except ValueError:
                        pass

        logger.info(f"Loaded {len(result)} keystone node IDs")

        return result

    def _analyze_defenses(self, root: ET.Element, keystones: Set[str]) -> Dict[str, str]:
        """
        Determine defense style from tree, gear, and stats.

        Args:
            root: XML root element
            keystones: Set of allocated keystone identifiers

        Returns:
            Dict with 'style' and 'mitigation' keys
        """
        result = {
            "style": "life",  # 'life', 'es', 'hybrid'
            "mitigation": "armor",  # 'armor', 'evasion', 'block', 'dodge'
        }

        # CI means ES build
        if "ci" in keystones:
            result["style"] = "es"

        # Ghost Reaver is a strong ES indicator
        if "ghost_reaver" in keystones:
            result["style"] = "es"

        # Pain Attunement suggests low-life ES
        if "pain_attunement" in keystones:
            result["style"] = "es"

        # Zealot's Oath suggests ES-focused regen
        if "zealots_oath" in keystones:
            result["style"] = "es" if "ci" in keystones else "hybrid"

        # Analyze mitigation keystones
        if "acrobatics" in keystones:
            result["mitigation"] = "evasion"
        elif "iron_reflexes" in keystones:
            result["mitigation"] = "armor"
        elif "glancing_blows" in keystones:
            result["mitigation"] = "block"

        # Analyze PlayerStat values from build
        build_elem = root.find("Build")
        if build_elem is not None:
            stats = {}
            for stat_elem in build_elem.findall("PlayerStat"):
                stat_name = stat_elem.get("stat", "")
                stat_value = stat_elem.get("value", "0")
                try:
                    stats[stat_name] = float(stat_value)
                except ValueError:
                    pass

            life = stats.get("Life", 0)
            es = stats.get("EnergyShield", 0)
            armor = stats.get("Armour", 0)
            evasion = stats.get("Evasion", 0)
            block = stats.get("EffectiveBlockChance", 0)

            # Determine defense style from stats
            if "ci" not in keystones:  # Not CI, can be life or hybrid
                if es > life * 0.5 and es > 500:
                    result["style"] = "hybrid"
                elif es > life:
                    result["style"] = "es"

            # Determine primary mitigation from stats
            if block > 50:
                result["mitigation"] = "block"
            elif armor > evasion * 2:
                result["mitigation"] = "armor"
            elif evasion > armor * 2:
                result["mitigation"] = "evasion"

        logger.debug(f"Defense analysis: {result}")

        return result

    def _determine_damage_types(self, skill_analysis: Dict[str, Any]) -> Tuple[str, Set[str]]:
        """
        Determine primary and secondary damage types.

        Args:
            skill_analysis: Results from _analyze_skills

        Returns:
            Tuple of (primary_type, set of secondary_types)
        """
        damage_types = skill_analysis.get("damage_types", set())

        if not damage_types:
            # Default to physical for attacks, lightning for spells
            if skill_analysis.get("is_attack", False):
                return ("physical", set())
            elif skill_analysis.get("is_spell", False):
                return ("lightning", set())
            return ("physical", set())

        # If only one type, it's primary with no secondary
        if len(damage_types) == 1:
            return (list(damage_types)[0], set())

        # For multiple types, use heuristics
        # Priority: physical > fire > cold > lightning > chaos (for attacks)
        # For spells: lightning > fire > cold > chaos > physical

        damage_list = list(damage_types)

        if skill_analysis.get("is_attack", False):
            priority = ["physical", "fire", "cold", "lightning", "chaos"]
        else:
            priority = ["lightning", "fire", "cold", "chaos", "physical"]

        primary = None
        for dtype in priority:
            if dtype in damage_list:
                primary = dtype
                break

        if primary is None:
            primary = damage_list[0]

        secondary = damage_types - {primary}

        return (primary, secondary)

    def _determine_attack_or_spell(self, skill_analysis: Dict[str, Any]) -> str:
        """
        Determine if build is attack-based, spell-based, or both.

        Args:
            skill_analysis: Results from _analyze_skills

        Returns:
            'attack', 'spell', or 'both'
        """
        is_attack = skill_analysis.get("is_attack", False)
        is_spell = skill_analysis.get("is_spell", False)

        if is_attack and is_spell:
            return "both"
        elif is_spell:
            return "spell"
        else:
            return "attack"  # Default to attack

    def _determine_damage_style(self, skill_analysis: Dict[str, Any], keystones: Set[str]) -> str:
        """
        Determine if build focuses on hits, DoT, or minions.

        Args:
            skill_analysis: Results from _analyze_skills
            keystones: Set of allocated keystone identifiers

        Returns:
            'hit', 'dot', or 'minion'
        """
        # Minion builds
        if skill_analysis.get("is_minion", False):
            return "minion"

        if "necromantic_aegis" in keystones:
            return "minion"

        # DoT builds
        if skill_analysis.get("is_dot", False):
            return "dot"

        if "crimson_dance" in keystones:
            return "dot"  # Bleed-focused

        # Default to hit
        return "hit"

    def _extract_mechanics(self, skill_analysis: Dict[str, Any]) -> Set[str]:
        """
        Extract key build mechanics from skill analysis.

        Args:
            skill_analysis: Results from _analyze_skills

        Returns:
            Set of mechanic identifiers
        """
        return skill_analysis.get("mechanics", set())


# Convenience function for simple extraction
def extract_build_context(build_xml: str) -> BuildContext:
    """
    Extract build context from PoB XML.

    Convenience wrapper around BuildContext.from_build_xml().

    Args:
        build_xml: Path of Building XML string

    Returns:
        BuildContext with extracted characteristics
    """
    return BuildContext.from_build_xml(build_xml)

"""
Default PoB configuration for imported characters.

A character imported from the GGG API has no Path of Building
configuration: no flasks active, no charges, no buffs, no conditions. PoB
then reports a fraction of the damage and effective HP the player sees in
their own PoB file. poe.ninja solves this with a rulebook: every config
option is switched on only when the build contains a *source* for it
(https://poe.ninja/poe1/builds/pob-rules). This module is a first cut of the
same idea, driven by text found in the build: item mods, gem names,
allocated passive names and stats, class and ascendancy.

Global assumptions (poe.ninja's): the enemy is a pinnacle boss, flasks are
active, and "on kill" effects are never assumed (bosses don't die).

Everything applied is returned as a list of Assumption records so the UI can
say exactly what was assumed and why.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

ON_KILL = re.compile(r"\b(on|when you|if you've|if you have|per) (kill|killed)\b|\bkill(ed|ing)? recently\b", re.I)


@dataclass
class Assumption:
    var: str            # PoB config variable, or "flasks" / "enemy"
    label: str          # what the player sees ("Frenzy charges up")
    reason: str         # the source line that triggered it
    value: object = True


@dataclass
class Rule:
    var: str
    label: str
    patterns: Sequence[str]      # regexes, matched case-insensitively against each source line
    value: object = True         # True (checkbox), int (count), or str (list option)
    requires_attack: bool = False
    unless: Sequence[str] = ()   # if any source matches one of these, the rule is off
    requires: Sequence[str] = () # other rule vars that must have fired


# Straight transcription of https://poe.ninja/poe1/builds/pob-rules (2026-09)
# onto PoB's ConfigOptions.lua variable names. Patterns describe *sources*:
# a gem, an item, an ascendancy node, a passive stat, a mastery. "On kill"
# lines are filtered out before matching (bosses do not die). Where poe.ninja
# uses a keyword ("any totem", "block build") the pattern is our reading.
RULES: List[Rule] = [
    # -- Charges ------------------------------------------------------------
    Rule("useFrenzyCharges", "Frenzy charges up", [
        r"terminus est", r"^frenzy( of \w+)?$", r"charged traps( support)?$", r"charged mines( support)?$", r"master sapper",
        r"tinkerskin", r"precursor'?s emblem", r"oro'?s sacrifice", r"the red trail", r"farrul'?s fur",
        r"disciple of the slaughter", r"frenzy charge on (hit|crit|block|melee|mana)", r"frenzy charge(s)? (on|when) ",
        r"gain (a |\d+ )?frenzy charge(s)? (on|when|every)", r"avidity", r"usurper'?s penance",
        r"gain a frenzy charge on hit against rare", r"frenzy charge.*mana spent", r"resonating shrine",
        r"poacher'?s mark", r"way of the poacher", r"avatar of the chase", r"blood rage", r"ascendancy:deadeye", r"ascendancy:raider", r"ascendancy:warden",
    ]),
    Rule("usePowerCharges", "Power charges up", [
        r"ascendancy:occultist", r"ascendancy:assassin", r"forbidden power", r"unstable infusion", r"deadly infusion",
        r"power siphon", r"power charge(s)? on critical( support)?", r"charged traps( support)?$", r"charged mines( support)?$",
        r"jaws of agony", r"voll'?s protector", r"precursor'?s emblem", r"cane of unravelling", r"farrul'?s fur", r"fenumus'? toxins",
        r"power charge on (block|hit|crit|mana|trap|mine)", r"power charge(s)? (on|when) ", r"gain (a |\d+ )?power charge(s)? (on|when|every)",
        r"anathema", r"liquid inspiration", r"stormrider", r"resonating shrine", r"malediction",
        r"channelling.*power charge", r"power charge.*channelling",
    ]),
    Rule("useEnduranceCharges", "Endurance charges up", [
        r"enduring cry", r"ascendancy:juggernaut", r"unrelenting", r"unflinching", r"unbreakable", r"voll'?s devotion",
        r"endurance charge (every|on|when)", r"endurance charge(s)? (on|when|every) ", r"gain (an |\d+ )?endurance charge(s)? (on|when|every)",
        r"replica farrul", r"disciple of the unyielding", r"resonating shrine", r"warlord'?s mark",
    ]),
    Rule("useSiphoningCharges", "Siphoning charges up", [r"disintegrator"]),
    Rule("useChallengerCharges", "Challenger charges up", [r"arena challenger"]),
    Rule("useGhostShrouds", "Ghost Shrouds up", [r"ghost dance"]),
    Rule("useBlitzCharges", "Blitz charges up", [r"blitz charge", r"^blitz$"]),
    # -- Life / ES states ---------------------------------------------------
    Rule("conditionFullLife", "On full life", [
        r"^ascendancy:slayer$", r"^ascendancy:ascendant$", r"offering to the serpent", r"chaos inoculation", r"damage on full life",
    ]),
    Rule("conditionLowLife", "On low life", [r"shavronne'?s wrappings", r"replica last resort", r"petrified blood"]),
    Rule("conditionHaveEnergyShield", "Always have energy shield", [r"chaos inoculation"]),
    Rule("conditionFullEnergyShield", "On full energy shield", [r"energy leech"]),
    Rule("conditionLeeching", "Leeching", [r"^ascendancy:slayer$", r"leeched as life", r"life leech", r"leech.*life", r"leeching"]),
    # -- Buffs ---------------------------------------------------------------
    Rule("buffLifetap", "Lifetap", [r"^lifetap$", r"lifetap support"]),
    Rule("buffOnslaught", "Onslaught", [
        r"onslaught while", r"sleepless sentries", r"lead by example", r"dance of blades", r"gain onslaught",
        r"you have onslaught", r"silver flask", r"onslaught support",
    ]),
    Rule("buffArcaneSurge", "Arcane Surge", [r"arcane surge"]),
    Rule("buffSacrificialZeal", "Sacrificial Zeal", [r"hand of the fervent"]),
    Rule("buffInfusion", "Infusion", [r"infused channell?ing"]),
    Rule("buffFortification", "Fortified", [
        r"^fortify( support)?$", r"vigilant strike", r"fortitude", r"melee hits fortify", r"fortify on melee hit", r"overlord", r"gain fortification",
    ], requires_attack=True),
    Rule("buffTailwind", "Tailwind", [r"gathering winds", r"tailwind"]),
    Rule("multiplierRage", "Rage at maximum", [
        r"crave the slaughter", r"rage on (attack |melee )?hit", r"rage when hit", r"rage on hit with axes", r"rage tincture",
        r"^rage( support)?$", r"ravenous passion", r"gain \d+ rage",
    ], value=100),
    Rule("buffUnholyMight", "Unholy Might", [r"unholy might"]),
    Rule("buffAdrenaline", "Adrenaline", [r"first to strike, last to fall", r"adrenaline"]),
    Rule("buffElusive", "Elusive", [r"nightblade", r"elusive on critical", r"elusive", r"withering step", r"mistwalker"]),
    Rule("buffAlchemistsGenius", "Alchemist's Genius", [r"spiked concoction", r"alchemist'?s genius"]),
    Rule("buffHerEmbrace", "Her Embrace", [r"oni-goroshi"]),
    Rule("embraceMadnessActive", "Embrace Madness", [r"beacon of madness", r"you're the crazy one"]),
    Rule("buffFanaticism", "Fanaticism", [r"instruments of zeal"]),
    Rule("conditionConvergence", "Convergence", [r"heart of destruction"]),
    Rule("conditionFocused", "Focused", [r"while focused"]),
    Rule("conditionHaveManaStorm", "Manastorm buff", [r"manastorm"]),
    Rule("conditionOnConsecratedGround", "On consecrated ground", [
        r"^sanctuary$", r"ascendancy:inquisitor", r"bottled faith", r"gifts from above", r"sulphur flask", r"creates? consecrated ground",
    ]),
    Rule("conditionEnemyOnConsecratedGround", "Enemy on consecrated ground", [
        r"^sanctuary$", r"ascendancy:inquisitor", r"bottled faith", r"gifts from above", r"sulphur flask", r"creates? consecrated ground",
    ]),
    Rule("conditionOnFungalGround", "On fungal ground", [r"sporeguard", r"fungal ground"]),
    Rule("conditionStationary", "Stationary", [r"ramako, sun'?s light", r"ralakesh'?s impatience", r"consecrated ground while stationary", r"while stationary"]),
    Rule("conditionMoving", "Moving", [r"while moving"]),
    # -- Recently / actions --------------------------------------------------
    Rule("conditionHaveTotem", "Totem summoned", [r"totem"]),
    Rule("conditionUsedBrandRecently", "Used a brand recently", [r"\bbrand\b"]),
    Rule("conditionMinionsDiedRecently", "Minion died recently", [r"^raise (zombie|spectre|spiders)", r"^summon (raging spirit|skeletons?|phantasm|carrion golem|stone golem|flame golem|ice golem|chaos golem|lightning golem|holy relic|reaper)", r"^animate (weapon|guardian)", r"^herald of (agony|purity)$", r"^dominating blow$", r"^absolution$"]),
    Rule("conditionPoisonedEnemyRecently", "Poisoned an enemy recently", [r"poison"]),
    Rule("conditionBeenHitRecently", "Been hit recently", [r"been hit recently", r"when you are hit", r"if you'?ve been hit", r"when hit(?! by your)"]),
    Rule("conditionBlockedRecently", "Blocked recently", [r"chance to block", r"block chance", r"blocked recently", r"on block"]),
    Rule("conditionGainedPowerChargeRecently", "Gained a power charge recently", [r".*"], requires=("usePowerCharges",)),
    Rule("conditionConsumed12SteelShardsRecently", "Consumed steel shards recently", [r"shattering steel", r"lancing steel"]),
    Rule("conditionUsedWarcryRecently", "Used a warcry recently", [r"warcry", r"enduring cry", r"intimidating cry", r"rallying cry", r"seismic cry", r"ancestral cry", r"infernal cry", r"general'?s cry", r"battlemage'?s cry", r"vengeful cry", r"divine cry"]),
    Rule("conditionSpawnedCorpseRecently", "Spawned a corpse recently", [r"^desecrate$", r"^unearth$"]),
    Rule("conditionConsumedCorpseRecently", "Consumed a corpse recently", [r"detonate dead", r"volatile dead", r"cremation", r"(flesh|bone|spirit) offering"]),
    Rule("conditionKilledRecently", "Killed recently (Writhing Jar)", [r"writhing jar"]),
    Rule("conditionImpaledRecently", "Impaled recently", [r"impale support", r"^impale$", r"chance to impale", r"impale enemies"]),
    Rule("conditionCausedBleedingRecently", "Caused bleeding recently", [r"chance to bleed", r"chance to cause bleeding", r"chance to inflict bleeding"]),
    Rule("conditionCritRecently", "Crit recently", [r".*"], unless=(r"resolute technique",)),
    Rule("conditionUsedFlaskRecently", "Used a flask recently", [r"ruby flask", r"sapphire flask", r"topaz flask", r"amethyst flask", r"used a flask recently"]),
    Rule("conditionSelfPoisoned", "Self-poisoned", [r"the golden rule"]),
    Rule("conditionSelfBleeding", "Self-bleeding", [r"the golden rule", r"the red trail"]),
    Rule("multiplierNearbyEnemies", "1 nearby enemy", [r".*"], value=1),
    Rule("enemyMultiplierEnemyPresenceSeconds", "Enemy in presence 10s", [r"war of attrition", r"ascendancy:gladiator"], value=10),
    # -- Enemy conditions ----------------------------------------------------
    Rule("conditionEnemyTaunted", "Enemy taunted", [r"ascendancy:champion", r"taunt(s)? (nearby|on|enemies)", r"chance to taunt"]),
    Rule("conditionEnemyIntimidated", "Enemy intimidated", [r"ascendancy:champion", r"the anticipation", r"belt of the deceiver", r"murderous eye jewel", r"chance to intimidate", r"intimidate (on|nearby)", r"enemies (are|become) intimidated"]),
    Rule("conditionEnemyMaimed", "Enemy maimed", [r"^maim( support)?$", r"searching eye jewel", r"the crimson storm", r"taproot", r"chance to maim", r"maim on hit", r"maim(s)? enemies"]),
    Rule("conditionEnemyBlinded", "Enemy blinded", [r"chance to blind", r"^blind( support)?$", r"blind (on|nearby)", r"enemies (are|become) blinded"]),
    Rule("conditionEnemyChilled", "Enemy chilled", [r".*"]),
    Rule("conditionEnemyIgnited", "Enemy ignited", [r".*"]),
    Rule("conditionEnemyBleeding", "Enemy bleeding", [r".*"]),
    Rule("conditionEnemyShocked", "Enemy shocked", [r"shaper of storms"]),
    Rule("conditionEnemyCoveredInAsh", "Enemy covered in ash", [r"hinekora, death'?s fury", r"ascendancy:chieftain"]),
    Rule("conditionEnemyFireExposure", "Fire exposure", [r"fire exposure"]),
    Rule("conditionEnemyColdExposure", "Cold exposure", [r"cold exposure"]),
    Rule("conditionEnemyLightningExposure", "Lightning exposure", [r"lightning exposure"]),
    Rule("conditionEnemyUnnerved", "Enemy unnerved", [r"unnerve on hit", r"enemies you curse are unnerved", r"unnerve"]),
    Rule("conditionEnemyDebilitated", "Enemy debilitated", [r"debilitate"]),
    # -- Skill specifics -----------------------------------------------------
    Rule("intensifyIntensity", "Intensity (4)", [r"intensify( support)?$", r"crackling lance", r"pinpoint( support)?$"], value=4),
    Rule("multiplierLinkedTargets", "1 link target", [r" link$", r"link support", r"^(flame|protective|soul|intuitive|vampiric|destructive|elemental) link$"], value=1),
    Rule("meleeDistance", "Melee distance 1", [r"flicker strike"], value=1),
    Rule("multiplierManaSpentRecently", "8000 mana spent recently", [r"indigon"], value=8000),
    Rule("multiplierWitheredStackCount", "Withered (15)", [r"eternal suffering", r"^wither$", r"sin'?s rebirth", r"chaos golem of the maelstr", r"chance to inflict withered", r"unholy might"], value=15),
    Rule("bannerPlanted", "Banner planted", [r"banner"]),
    Rule("heraldOfAgonyVirulenceStack", "Virulence (40)", [r"herald of agony"], value=40),
    Rule("prideEffect", "Pride at maximum effect", [r"^pride$"], value="MAX"),
    Rule("feedingFrenzyFeedingFrenzyActive", "Feeding Frenzy active", [r"feeding frenzy"]),
    Rule("bladestormInBloodstorm", "In Bloodstorm", [r"bladestorm"]),
    Rule("deathmarkDeathmarkActive", "Deathmark active", [r"deathmark", r"signal prey"]),
    Rule("flameWallAddedDamage", "Through Flame Wall", [r"flame wall"]),
    Rule("iceNovaCastOnFrostbolt", "Ice Nova on Frostbolt", [r"ice nova of frostbolts", r"ice nova"]),
    Rule("vortexCastOnFrostbolt", "Vortex on Frostbolt", [r"vortex of projection"]),
    Rule("meatShieldEnemyNearYou", "Enemy near you (Meat Shield)", [r"meat shield"]),
    Rule("configResonanceCount", "Trinity resonance (50)", [r"^trinity( support)?$"], value=50),
    Rule("configUnholyResonanceCount", "Unholy Trinity resonance (50)", [r"unholy trinity"], value=50),
    Rule("summonHolyRelicEnableHolyRelicBoon", "Holy Relic boon", [r"summon holy relic"]),
    Rule("raiseSpidersSpiderCount", "20 spiders", [r"raise spiders", r"arakaali'?s fang"], value=20),
    Rule("configSpectralWolfCount", "10 spectral wolves", [r"spectral wolf"], value=10),
    Rule("configSpectralTigerCount", "5 spectral tigers", [r"spectral tiger"], value=5),
    Rule("aspectOfTheSpiderWebStacks", "Spider's web stacks (3)", [r"aspect of the spider"], value=3),
    Rule("channellingCycloneCheck", "Cyclone channelling", [r"^cyclone( of \w+)?$"]),
    Rule("ColdSnapBypassCD", "Cold Snap bypass cooldown", [r"cold snap"], requires=("useFrenzyCharges",)),
]

ATTACK_GEM_HINTS = re.compile(r"attack|melee|strike|slam|cyclone|lacerate|flicker|blade|earthquake|shot|arrow|barrage|whirl", re.I)


# ---------------------------------------------------------------------- #
# Source collection
# ---------------------------------------------------------------------- #

def _text(el: Optional[ET.Element]) -> str:
    return (el.text or "") if el is not None else ""


def collect_sources(xml: str, tree_version: Optional[str] = None) -> List[str]:
    """
    Every line of text in the build that could be a config source:
    item mods, gem names, class/ascendancy, allocated passive names + stats,
    selected mastery effects. Returns unique, stripped lines.
    """
    root = ET.fromstring(xml)
    lines: List[str] = []

    build = root.find("Build")
    if build is not None:
        cls = build.get("className") or ""
        asc = build.get("ascendClassName") or ""
        if cls:
            lines.append(f"class:{cls}")
        if asc and asc != "None":
            lines.append(f"ascendancy:{asc}")

    for item in root.iter("Item"):
        for line in _text(item).splitlines():
            line = line.strip()
            if line:
                lines.append(line)

    for gem in root.iter("Gem"):
        if gem.get("enabled", "true") != "false":
            name = gem.get("nameSpec") or gem.get("skillId") or ""
            if name:
                lines.append(name)

    spec = root.find(".//Tree/Spec[@activeSpec='true']")
    if spec is None:
        spec = root.find(".//Tree/Spec")
    if spec is not None:
        version = tree_version or spec.get("treeVersion")
        try:
            from src.pob.tree_parser import load_passive_tree
            from src.pob.mastery_optimizer import get_mastery_database
            graph = load_passive_tree(version)
            ids = [int(n) for n in (spec.get("nodes") or "").split(",") if n.strip()]
            for nid in ids:
                node = graph.get_node(nid)
                if node is None:
                    continue
                if node.node_type in ("notable", "keystone") or node.is_ascendancy:
                    lines.append(node.name)
                for st in node.stats or []:
                    lines.append(st)
            try:
                db = get_mastery_database(tree_version=version)
                for pair in re.findall(r"\{(\d+),(\d+)\}", spec.get("masteryEffects") or ""):
                    eff = db.get_effect(int(pair[1]))
                    for st in getattr(eff, "stats", None) or []:
                        lines.append(st)
            except Exception:
                logger.debug("mastery effects unavailable for sources", exc_info=True)
        except Exception:
            logger.debug("tree sources unavailable", exc_info=True)

    seen = set()
    out = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


# ---------------------------------------------------------------------- #
# Rule evaluation
# ---------------------------------------------------------------------- #

def _is_attack_build(sources: Iterable[str], xml: str) -> bool:
    main = re.search(r'<Skill [^>]*mainActiveSkill="(\d+)"', xml)
    for gem in ET.fromstring(xml).iter("Gem"):
        name = gem.get("nameSpec") or ""
        if ATTACK_GEM_HINTS.search(name) and gem.get("enabled", "true") != "false":
            return True
    return False


def evaluate_rules(xml: str, tree_version: Optional[str] = None) -> List[Assumption]:
    sources = collect_sources(xml, tree_version)
    usable = [s for s in sources if not ON_KILL.search(s)]
    attack = _is_attack_build(usable, xml)

    def first_match(patterns: Sequence[str]) -> Optional[str]:
        for pat in patterns:
            if pat == ".*":
                return "poe.ninja rule: everyone"
            rx = re.compile(pat, re.I)
            for src in usable:
                if rx.search(src):
                    return src
        return None

    found: List[Assumption] = []
    fired = set()
    for rule in RULES:
        if rule.requires_attack and not attack:
            continue
        if rule.requires and not all(r in fired for r in rule.requires):
            continue
        if rule.unless and first_match(rule.unless) is not None:
            continue
        hit = first_match(rule.patterns)
        if hit:
            found.append(Assumption(rule.var, rule.label, hit, rule.value))
            fired.add(rule.var)
    return found


# ---------------------------------------------------------------------- #
# Applying to XML
# ---------------------------------------------------------------------- #

def apply_default_config(
    xml: str,
    tree_version: Optional[str] = None,
    enemy: str = "Pinnacle",
    activate_flasks: bool = True,
) -> Tuple[str, List[Assumption]]:
    """
    Write a ``<Config>`` reflecting the global assumptions plus every rule
    the build has a source for, and mark equipped flasks active.

    Existing Input values in the XML are kept (they win over rules); rules
    only add. Returns the new XML and the list of assumptions applied.
    """
    root = ET.fromstring(xml)
    assumptions: List[Assumption] = []

    config = root.find("Config")
    if config is None:
        config = ET.SubElement(root, "Config")
    config.set("activeConfigSet", config.get("activeConfigSet") or "1")
    cfg_set = config.find("ConfigSet")
    if cfg_set is None:
        cfg_set = ET.SubElement(config, "ConfigSet")
        cfg_set.set("id", "1")
    existing = {inp.get("name") for inp in cfg_set.findall("Input")}

    def add_input(name: str, value) -> None:
        if name in existing:
            return
        inp = ET.SubElement(cfg_set, "Input")
        inp.set("name", name)
        if value is True or value is False:
            inp.set("boolean", "true" if value else "false")
        elif isinstance(value, (int, float)):
            inp.set("number", str(value))
        else:
            inp.set("string", str(value))
        existing.add(name)

    add_input("enemyIsBoss", enemy)
    assumptions.append(Assumption("enemy", {"Pinnacle": "Pinnacle boss", "Boss": "Map boss", "Uber": "Uber boss", "None": "No boss"}.get(enemy, enemy), "poe.ninja global rule", enemy))
    # poe.ninja's other globals (always on, not shown as toggles)
    add_input("BrandsAttachedToEnemy", 1)
    add_input("DisableEHPGainOnBlock", True)
    add_input("multiplierNearbyRareOrUniqueEnemies", 1)

    for a in evaluate_rules(xml, tree_version):
        add_input(a.var, a.value)
        assumptions.append(a)

    if activate_flasks:
        activated = 0
        for slot in root.iter("Slot"):
            name = slot.get("name") or ""
            if name.startswith("Flask") and slot.get("itemId") not in (None, "0", ""):
                if slot.get("active") != "true":
                    slot.set("active", "true")
                activated += 1
        if activated:
            assumptions.append(Assumption("flasks", f"{activated} flask{'s' if activated != 1 else ''} active", "poe.ninja global rule"))

    # The config changed, so any stats PoB saved into the build are stale.
    build = root.find("Build")
    if build is not None:
        for child in list(build):
            if child.tag == "PlayerStat":
                build.remove(child)

    return ET.tostring(root, encoding="unicode"), assumptions


def describe(assumptions: Sequence[Assumption]) -> List[Dict[str, object]]:
    return [{"var": a.var, "label": a.label, "reason": a.reason, "value": a.value} for a in assumptions]

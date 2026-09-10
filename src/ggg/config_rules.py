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


@dataclass
class Rule:
    var: str
    label: str
    patterns: Sequence[str]      # regexes, matched case-insensitively against each source line
    value: object = True         # boolean True, or a string for list options
    requires_attack: bool = False


# Rule order matters only for readability. Patterns are deliberately about
# *generation* of a thing, not its maximum ("+1 to maximum Frenzy Charges"
# is not a source).
RULES: List[Rule] = [
    Rule("useFrenzyCharges", "Frenzy charges up", [
        r"gain (a |\d+ )?frenzy charge", r"frenzy charge(s)? on ", r"frenzy charge(s)? when ",
        r"^frenzy$", r"charged traps support", r"charged mines support", r"poacher'?s mark",
        r"terminus est", r"oro'?s sacrifice", r"the red trail", r"farrul'?s fur", r"precursor'?s emblem",
        r"disciple of the slaughter", r"usurper'?s penance", r"avidity", r"way of the poacher", r"avatar of the chase",
        r"blood rage",
    ]),
    Rule("usePowerCharges", "Power charges up", [
        r"gain (a |\d+ )?power charge", r"power charge(s)? on ", r"power charge(s)? when ",
        r"power siphon", r"power charge on critical", r"charged traps support", r"charged mines support",
        r"jaws of agony", r"voll'?s protector", r"cane of unravelling", r"fenumus'? toxins",
        r"precursor'?s emblem", r"farrul'?s fur", r"anathema", r"liquid inspiration", r"stormrider",
        r"unstable infusion", r"forbidden power", r"deadly infusion", r"malediction",
    ]),
    Rule("useEnduranceCharges", "Endurance charges up", [
        r"gain (an |\d+ )?endurance charge", r"endurance charge(s)? on ", r"endurance charge(s)? when ",
        r"endurance charge(s)? every", r"enduring cry", r"voll'?s devotion", r"warlord'?s mark",
        r"unrelenting", r"unbreakable", r"unflinching", r"disciple of the unyielding", r"replica farrul",
    ]),
    Rule("buffOnslaught", "Onslaught", [
        r"onslaught while", r"gain onslaught", r"you have onslaught", r"sleepless sentries", r"lead by example",
        r"dance of blades", r"silver flask", r"onslaught support",
    ]),
    Rule("buffFortification", "Fortified", [
        r"fortify", r"fortification", r"fortitude",
    ], requires_attack=True),
    Rule("buffArcaneSurge", "Arcane Surge", [r"arcane surge"]),
    Rule("buffTailwind", "Tailwind", [r"tailwind", r"gathering winds"]),
    Rule("buffAdrenaline", "Adrenaline", [r"adrenaline", r"first to strike, last to fall"]),
    Rule("buffElusive", "Elusive", [r"elusive", r"withering step", r"mistwalker"]),
    Rule("buffUnholyMight", "Unholy Might", [r"unholy might"]),
    Rule("buffLifetap", "Lifetap", [r"^lifetap$", r"lifetap support"]),
    Rule("buffInfusion", "Infusion", [r"infused channelling"]),
    Rule("conditionLeeching", "Leeching", [r"leeched as life", r"life leech", r"leech.*life", r"leeching"]),
    Rule("conditionFullLife", "On full life", [
        r"chaos inoculation", r"damage on full life", r"offering to the serpent", r"^ascendancy:slayer$",
    ]),
    Rule("conditionLowLife", "On low life", [r"shavronne'?s wrappings", r"replica last resort", r"petrified blood"]),
    Rule("channellingCycloneCheck", "Cyclone channelling", [r"^cyclone( of \w+)?$"]),
    Rule("conditionUsedFlaskRecently", "Used a flask recently", [r"used a flask recently", r"flask effect"]),
    Rule("conditionCritRecently", "Crit recently", [r"crit(ical strike)? recently", r"if you'?ve crit"]),
    Rule("conditionHaveTotem", "Totem summoned", [r"ancestral protector", r"ancestral warchief", r"totem"]),
    Rule("conditionEnemyMaimed", "Enemy maimed", [r"chance to maim", r"maim on hit", r"maim(s)? enemies", r"enemies (are|become) maimed", r"^maim$", r"maim support"]),
    Rule("conditionEnemyIntimidated", "Enemy intimidated", [r"intimidate (on|nearby)", r"chance to intimidate", r"enemies (are|become) intimidated", r"intimidating cry"]),
    Rule("conditionEnemyBlinded", "Enemy blinded", [r"chance to blind", r"blind (on|nearby)", r"enemies (are|become) blinded", r"blind enemies", r"^blind$"]),
    Rule("conditionEnemyTaunted", "Enemy taunted", [r"taunt(s)? (nearby|on|enemies)", r"chance to taunt", r"^taunt$"]),
    Rule("conditionStationary", "Stationary", [r"while stationary", r"ramako", r"ralakesh'?s impatience"]),
    Rule("conditionMoving", "Moving", [r"while moving"]),
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

    found: List[Assumption] = []
    for rule in RULES:
        if rule.requires_attack and not attack:
            continue
        hit = None
        for src in usable:
            for pat in rule.patterns:
                if re.search(pat, src, re.I):
                    hit = src
                    break
            if hit:
                break
        if hit:
            found.append(Assumption(rule.var, rule.label, hit))
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
    assumptions.append(Assumption("enemy", {"Pinnacle": "Pinnacle boss", "Boss": "Map boss", "Uber": "Uber boss", "None": "No boss"}.get(enemy, enemy), "poe.ninja global rule"))

    for a in evaluate_rules(xml, tree_version):
        add_input(a.var, True)
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

    return ET.tostring(root, encoding="unicode"), assumptions


def describe(assumptions: Sequence[Assumption]) -> List[Dict[str, str]]:
    return [{"var": a.var, "label": a.label, "reason": a.reason} for a in assumptions]

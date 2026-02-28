"""
PoB XML Parser - Extract pre-calculated stats directly from PoB XML

Path of Building stores pre-calculated statistics in the XML under <PlayerStat> tags.
This is much simpler and more reliable than trying to recalculate them.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional


def parse_pob_stats(xml: str) -> Dict[str, float]:
    """
    Parse pre-calculated statistics from Path of Building XML.

    PoB stores calculated stats in <Build><PlayerStat> tags with stat name and value.

    Args:
        xml: The PoB build XML string

    Returns:
        Dictionary mapping stat names to their values

    Examples:
        >>> xml = decode_pob_code(pob_code)
        >>> stats = parse_pob_stats(xml)
        >>> print(f"DPS: {stats['CombinedDPS']:,.0f}")
        DPS: 3,163,831
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}")

    stats = {}

    # Find all PlayerStat elements
    for player_stat in root.findall(".//PlayerStat"):
        stat_name = player_stat.get("stat")
        stat_value = player_stat.get("value")

        if stat_name and stat_value:
            try:
                # Convert to float
                stats[stat_name] = float(stat_value)
            except ValueError:
                # Skip stats that aren't numeric
                pass

    return stats


def get_build_summary(xml: str) -> Dict[str, Any]:
    """
    Extract a summary of key build information from PoB XML.

    Args:
        xml: The PoB build XML string

    Returns:
        Dictionary with build level, class, stats, etc.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}")

    # Get build element
    build_elem = root.find("Build")

    summary = {
        "level": int(build_elem.get("level", 0)) if build_elem else 0,
        "className": build_elem.get("className", "Unknown") if build_elem else "Unknown",
        "ascendClassName": build_elem.get("ascendClassName", "") if build_elem else "",
    }

    # Get pre-calculated stats
    stats = parse_pob_stats(xml)

    # Add key stats to summary
    summary.update({
        # DPS metrics
        "totalDPS": stats.get("TotalDPS", 0),
        "combinedDPS": stats.get("CombinedDPS", 0),
        "totalDotDPS": stats.get("TotalDotDPS", 0),
        "withImpaleDPS": stats.get("WithImpaleDPS", 0),
        "fullDPS": stats.get("FullDPS", 0),

        # Defensive stats
        "life": stats.get("Life", 0),
        "energyShield": stats.get("EnergyShield", 0),
        "evasion": stats.get("Evasion", 0),
        "armour": stats.get("Armour", 0),
        "totalEHP": stats.get("TotalEHP", 0),
        "blockChance": stats.get("BlockChance", 0),

        # Resistances
        "fireRes": stats.get("FireResist", 0),
        "coldRes": stats.get("ColdResist", 0),
        "lightningRes": stats.get("LightningResist", 0),
        "chaosRes": stats.get("ChaosResist", 0),

        # Attributes
        "strength": stats.get("Str", 0),
        "dexterity": stats.get("Dex", 0),
        "intelligence": stats.get("Int", 0),

        # Speed
        "speed": stats.get("Speed", 0),
        "hitChance": stats.get("AccuracyHitChance", 0),
        "critChance": stats.get("CritChance", 0),
    })

    return summary


def get_all_stats(xml: str) -> Dict[str, float]:
    """
    Get ALL pre-calculated stats from PoB XML.

    Useful for debugging or when you need access to all available stats.

    Args:
        xml: The PoB build XML string

    Returns:
        Dictionary with all stats from the XML
    """
    return parse_pob_stats(xml)

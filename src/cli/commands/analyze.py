"""
Analyze command - Build statistics and analysis.
"""

import click
import logging
from typing import Optional

from ..utils import InputHandler, get_output_handler, common_options, input_argument

logger = logging.getLogger(__name__)


@click.command()
@input_argument
@click.option(
    "--full", "-f",
    is_flag=True,
    help="Show all available stats."
)
@common_options
@click.pass_context
def analyze(
    ctx,
    input_source: str,
    full: bool,
    json_output: bool,
    output_file: Optional[str],
):
    """
    Analyze build statistics.

    \b
    INPUT can be:
      - Path to XML file (build.xml)
      - Path to PoB code file (build.txt)
      - PoB code string
      - "-" for stdin

    \b
    Examples:
      poe-optimizer analyze build.xml
      poe-optimizer analyze build.xml --full
      poe-optimizer analyze build.xml --json
    """
    from src.pob.xml_parser import get_build_summary
    from src.pob.modifier import get_passive_tree_summary
    from src.pob.jewel.registry import JewelRegistry

    output = get_output_handler(ctx, json_output, output_file)

    # Load input
    output.progress(f"Loading build from {input_source}...")
    try:
        build_xml = InputHandler.load(input_source)
    except (FileNotFoundError, IOError, ValueError) as e:
        raise click.ClickException(f"Failed to load build: {e}")

    # Get stats
    try:
        stats = get_build_summary(build_xml)
        tree_summary = get_passive_tree_summary(build_xml)
    except (KeyError, ValueError) as e:
        logger.debug("Failed to analyze build", exc_info=True)
        raise click.ClickException(f"Failed to analyze build: {e}")

    # Get jewel info
    try:
        registry = JewelRegistry.from_build_xml(build_xml)
        jewel_info = {
            "total": len(registry.unique_jewels) + len(registry.timeless_jewels) + len(registry.cluster_jewels),
            "timeless": len(registry.timeless_jewels),
            "cluster": len(registry.cluster_jewels),
            "unique": len(registry.unique_jewels),
        }
    except Exception:
        logger.debug("Could not parse jewel information", exc_info=True)
        jewel_info = {"total": 0, "error": "Could not parse jewels"}

    # Build result
    result = {
        "combat": {
            "combined_dps": stats.get("combinedDPS", 0),
            "total_dps": stats.get("totalDPS", 0),
            "hit_chance": stats.get("hitChance", 0),
            "crit_chance": stats.get("critChance", 0),
            "attack_speed": stats.get("speed", 0),
        },
        "defense": {
            "life": stats.get("life", 0),
            "energy_shield": stats.get("energyShield", 0),
            "total_ehp": stats.get("totalEHP", 0),
            "armour": stats.get("armour", 0),
            "evasion": stats.get("evasion", 0),
            "block_chance": stats.get("blockChance", 0),
        },
        "resistances": {
            "fire": stats.get("fireRes", 0),
            "cold": stats.get("coldRes", 0),
            "lightning": stats.get("lightningRes", 0),
            "chaos": stats.get("chaosRes", 0),
        },
        "attributes": {
            "strength": stats.get("strength", 0),
            "dexterity": stats.get("dexterity", 0),
            "intelligence": stats.get("intelligence", 0),
        },
        "passive_tree": {
            "allocated_nodes": len(tree_summary.get("allocated_nodes", [])),
            "mastery_effects": len(tree_summary.get("mastery_effects", {})),
        },
        "jewels": jewel_info,
    }

    if full:
        # Add all raw stats
        result["raw_stats"] = stats
        result["tree_details"] = tree_summary

    output.output(result, title="BUILD ANALYSIS")

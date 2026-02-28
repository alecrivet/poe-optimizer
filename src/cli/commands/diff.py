"""
Diff command - Compare two builds.
"""

import click
from typing import Optional

from ..utils import InputHandler, get_output_handler, common_options


@click.command()
@click.argument("build1", required=True, metavar="BUILD1")
@click.argument("build2", required=True, metavar="BUILD2")
@common_options
@click.pass_context
def diff(
    ctx,
    build1: str,
    build2: str,
    json_output: bool,
    output_file: Optional[str],
):
    """
    Compare two builds.

    \b
    BUILD1 and BUILD2 can be:
      - Path to XML file (build.xml)
      - Path to PoB code file (build.txt)
      - PoB code string

    \b
    Examples:
      poe-optimizer diff original.xml optimized.xml
      poe-optimizer diff build1.txt build2.txt --json
    """
    from src.pob.xml_parser import get_build_summary
    from src.pob.modifier import get_passive_tree_summary
    from src.visualization.tree_diff import get_tree_diff

    output = get_output_handler(ctx, json_output, output_file)

    # Load builds
    output.progress("Loading builds...")
    try:
        xml1 = InputHandler.load(build1)
        xml2 = InputHandler.load(build2)
    except Exception as e:
        raise click.ClickException(f"Failed to load builds: {e}")

    # Get stats
    try:
        stats1 = get_build_summary(xml1)
        stats2 = get_build_summary(xml2)
        tree1 = get_passive_tree_summary(xml1)
        tree2 = get_passive_tree_summary(xml2)
    except Exception as e:
        raise click.ClickException(f"Failed to analyze builds: {e}")

    # Calculate differences
    def calc_diff(v1, v2):
        if v1 == 0:
            return 0 if v2 == 0 else 100.0
        return ((v2 - v1) / v1) * 100

    nodes1 = set(tree1.get("allocated_nodes", []))
    nodes2 = set(tree2.get("allocated_nodes", []))

    result = {
        "stat_changes": {
            "combined_dps": {
                "build1": stats1.get("combinedDPS", 0),
                "build2": stats2.get("combinedDPS", 0),
                "change_pct": calc_diff(stats1.get("combinedDPS", 0), stats2.get("combinedDPS", 0)),
            },
            "life": {
                "build1": stats1.get("life", 0),
                "build2": stats2.get("life", 0),
                "change_pct": calc_diff(stats1.get("life", 0), stats2.get("life", 0)),
            },
            "total_ehp": {
                "build1": stats1.get("totalEHP", 0),
                "build2": stats2.get("totalEHP", 0),
                "change_pct": calc_diff(stats1.get("totalEHP", 0), stats2.get("totalEHP", 0)),
            },
            "energy_shield": {
                "build1": stats1.get("energyShield", 0),
                "build2": stats2.get("energyShield", 0),
                "change_pct": calc_diff(stats1.get("energyShield", 0), stats2.get("energyShield", 0)),
            },
        },
        "tree_changes": {
            "nodes_added": len(nodes2 - nodes1),
            "nodes_removed": len(nodes1 - nodes2),
            "nodes_unchanged": len(nodes1 & nodes2),
            "total_build1": len(nodes1),
            "total_build2": len(nodes2),
        },
        "mastery_changes": {
            "masteries_build1": len(tree1.get("mastery_effects", {})),
            "masteries_build2": len(tree2.get("mastery_effects", {})),
        },
    }

    # Add node lists if not too many
    added = list(nodes2 - nodes1)
    removed = list(nodes1 - nodes2)
    if len(added) <= 20:
        result["nodes_added"] = added
    if len(removed) <= 20:
        result["nodes_removed"] = removed

    output.output(result, title="BUILD COMPARISON")

    # Print summary
    if not json_output and not output_file:
        click.echo("\nSummary:")
        dps_change = result["stat_changes"]["combined_dps"]["change_pct"]
        life_change = result["stat_changes"]["life"]["change_pct"]
        ehp_change = result["stat_changes"]["total_ehp"]["change_pct"]

        color = "green" if dps_change > 0 else "red" if dps_change < 0 else "white"
        click.secho(f"  DPS:  {dps_change:+.1f}%", fg=color)

        color = "green" if life_change > 0 else "red" if life_change < 0 else "white"
        click.secho(f"  Life: {life_change:+.1f}%", fg=color)

        color = "green" if ehp_change > 0 else "red" if ehp_change < 0 else "white"
        click.secho(f"  EHP:  {ehp_change:+.1f}%", fg=color)

        click.echo(f"\n  Nodes: +{result['tree_changes']['nodes_added']} / -{result['tree_changes']['nodes_removed']}")

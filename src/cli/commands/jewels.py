"""
Jewels command - Show jewel information.
"""

import click
from typing import Optional

from ..utils import InputHandler, get_output_handler, common_options, input_argument


@click.command()
@input_argument
@common_options
@click.pass_context
def jewels(
    ctx,
    input_source: str,
    json_output: bool,
    output_file: Optional[str],
):
    """
    Show jewel information for a build.

    Displays all jewels including:
    - Timeless jewels (type, seed, variant)
    - Cluster jewels (size, notables)
    - Unique jewels (effects)
    - Protected nodes

    \b
    INPUT can be:
      - Path to XML file (build.xml)
      - Path to PoB code file (build.txt)
      - PoB code string
      - "-" for stdin

    \b
    Examples:
      poe-optimizer jewels build.xml
      poe-optimizer jewels build.xml --json
    """
    from src.pob.modifier import get_passive_tree_summary
    from src.pob.jewel.registry import JewelRegistry
    from src.pob.jewel.cluster import is_cluster_node_id

    output = get_output_handler(ctx, json_output, output_file)

    # Load input
    output.progress(f"Loading build from {input_source}...")
    try:
        build_xml = InputHandler.load(input_source)
    except Exception as e:
        raise click.ClickException(f"Failed to load build: {e}")

    # Get jewel registry
    try:
        registry = JewelRegistry.from_build_xml(build_xml)
        tree_summary = get_passive_tree_summary(build_xml)
        allocated_nodes = set(tree_summary.get("allocated_nodes", []))
        protected_nodes = registry.get_protected_nodes(allocated_nodes)
    except Exception as e:
        raise click.ClickException(f"Failed to parse jewels: {e}")

    # Build result
    result = {
        "summary": {
            "total_jewels": len(registry.unique_jewels) + len(registry.timeless_jewels) + len(registry.cluster_jewels),
            "socketed_jewels": sum(1 for j in registry.unique_jewels if j.socket_node_id) +
                               sum(1 for j in registry.timeless_jewels if j.socket_node_id) +
                               sum(1 for j in registry.cluster_jewels if j.socket_node_id),
            "protected_nodes": len(protected_nodes),
        },
        "timeless_jewels": [],
        "cluster_jewels": [],
        "unique_jewels": [],
        "protected_nodes": {
            "jewel_sockets": sorted([n for n in protected_nodes if n < 65536]),
            "cluster_nodes": sorted([n for n in protected_nodes if n >= 65536]),
        },
    }

    # Timeless jewels
    for jewel in registry.timeless_jewels:
        result["timeless_jewels"].append({
            "name": jewel.display_name,
            "type": jewel.jewel_type if jewel.jewel_type else "unknown",
            "seed": jewel.seed,
            "variant": jewel.variant,
            "socket_node_id": jewel.socket_node_id,
            "socketed": jewel.socket_node_id is not None,
        })

    # Cluster jewels
    for jewel in registry.cluster_jewels:
        result["cluster_jewels"].append({
            "name": jewel.display_name,
            "size": jewel.size.value if jewel.size else "unknown",
            "notables": jewel.notables,
            "socket_node_id": jewel.socket_node_id,
            "socketed": jewel.socket_node_id is not None,
        })

    # Unique jewels
    for jewel in registry.unique_jewels:
        result["unique_jewels"].append({
            "name": jewel.display_name,
            "socket_node_id": jewel.socket_node_id,
            "socketed": jewel.socket_node_id is not None,
        })

    output.output(result, title="JEWEL INFORMATION")

    # Print summary if not JSON
    if not json_output and not output_file:
        click.echo("\nFor optimizer:")
        click.echo(f"  {len(protected_nodes)} nodes are protected from modification")
        if result["protected_nodes"]["jewel_sockets"]:
            click.echo(f"  Jewel sockets: {result['protected_nodes']['jewel_sockets']}")
        if result["protected_nodes"]["cluster_nodes"]:
            click.echo(f"  Cluster nodes: {len(result['protected_nodes']['cluster_nodes'])} nodes")

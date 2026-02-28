"""
Jewels command - Show jewel information and analysis.
"""

import click
import logging
from typing import Optional

from ..utils import InputHandler, get_output_handler, common_options, input_argument

logger = logging.getLogger(__name__)


@click.command()
@input_argument
@common_options
@click.option(
    "--analyze-timeless", is_flag=True, default=False,
    help="Analyze timeless jewel socket recommendations"
)
@click.option(
    "--analyze-threads", is_flag=True, default=False,
    help="Analyze Thread of Hope placement options"
)
@click.option(
    "--analyze-clusters", is_flag=True, default=False,
    help="Analyze cluster jewel notable optimization"
)
@click.pass_context
def jewels(
    ctx,
    input_source: str,
    json_output: bool,
    output_file: Optional[str],
    analyze_timeless: bool,
    analyze_threads: bool,
    analyze_clusters: bool,
):
    """
    Show jewel information for a build.

    Displays all jewels including:
    - Timeless jewels (type, seed, variant)
    - Cluster jewels (size, notables)
    - Unique jewels (effects)
    - Protected nodes

    \b
    Analysis options:
      --analyze-timeless   Recommend optimal timeless jewel sockets
      --analyze-threads    Find best Thread of Hope placements
      --analyze-clusters   Suggest cluster notable optimizations

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
      poe-optimizer jewels build.xml --analyze-threads
      poe-optimizer jewels build.xml --analyze-clusters
    """
    from src.pob.modifier import get_passive_tree_summary
    from src.pob.jewel.registry import JewelRegistry
    from src.pob.jewel.cluster import is_cluster_node_id

    output = get_output_handler(ctx, json_output, output_file)

    # Load input
    output.progress(f"Loading build from {input_source}...")
    try:
        build_xml = InputHandler.load(input_source)
    except (FileNotFoundError, IOError, ValueError) as e:
        raise click.ClickException(f"Failed to load build: {e}")

    # Get jewel registry
    try:
        registry = JewelRegistry.from_build_xml(build_xml)
        tree_summary = get_passive_tree_summary(build_xml)
        allocated_nodes = set(tree_summary.get("allocated_nodes", []))
        protected_nodes = registry.get_protected_nodes(allocated_nodes)
    except (KeyError, ValueError) as e:
        logger.debug("Failed to parse jewels", exc_info=True)
        raise click.ClickException(f"Failed to parse jewels: {e}")

    # Load tree graph and position data for analysis
    tree_graph = None
    radius_calculator = None
    if analyze_threads or analyze_timeless:
        try:
            from src.pob.tree_parser import load_passive_tree
            from src.pob.tree_positions import TreePositionLoader
            from src.pob.jewel.radius_calculator import RadiusCalculator

            tree_graph = load_passive_tree()
            position_loader = TreePositionLoader()
            positions = position_loader.load_positions()
            radius_calculator = RadiusCalculator(positions)
        except Exception as e:
            logger.debug("Could not load tree data for analysis", exc_info=True)
            output.progress(f"Warning: Could not load tree data for analysis: {e}")

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

    # Thread of Hope analysis
    if analyze_threads and tree_graph and radius_calculator:
        try:
            from src.pob.jewel.thread_of_hope import ThreadOfHopeOptimizer

            output.progress("Analyzing Thread of Hope placements...")
            toh_optimizer = ThreadOfHopeOptimizer(radius_calculator, tree_graph)

            result["thread_of_hope_analysis"] = {"placements": []}

            for ring_size in ["Small", "Medium", "Large", "Very Large"]:
                placements = toh_optimizer.find_optimal_placement(
                    build_xml, ring_size, objective="value"
                )

                for placement in placements[:3]:  # Top 3 per size
                    notable_names = []
                    for nid in placement.ring_notables:
                        node = tree_graph.get_node(nid)
                        if node:
                            notable_names.append(node.name)

                    result["thread_of_hope_analysis"]["placements"].append({
                        "socket_id": placement.socket_node_id,
                        "ring_size": ring_size,
                        "notable_count": placement.notable_count,
                        "notables": notable_names[:5],  # Limit to 5
                        "pathing_cost": placement.pathing_cost,
                        "value_score": round(placement.value_score, 1),
                        "efficiency": round(placement.efficiency, 2),
                    })
        except Exception as e:
            logger.debug("Thread of Hope analysis failed", exc_info=True)
            result["thread_of_hope_analysis"] = {"error": str(e)}

    # Timeless jewel socket analysis
    if analyze_timeless and tree_graph and radius_calculator:
        try:
            from src.pob.jewel.timeless_value import TimelessValueCalculator

            output.progress("Analyzing timeless jewel sockets...")
            value_calc = TimelessValueCalculator(radius_calculator, tree_graph)

            result["timeless_analysis"] = {"socket_recommendations": []}

            # Analyze each jewel socket
            jewel_sockets = tree_graph.get_jewel_sockets()
            for socket in jewel_sockets[:10]:  # Limit to 10
                nodes_in_radius = radius_calculator.get_nodes_in_radius(
                    socket.node_id, "Large"
                )
                notable_count = sum(
                    1 for nid in nodes_in_radius
                    if tree_graph.get_node(nid) and
                    tree_graph.get_node(nid).node_type == "notable"
                )

                result["timeless_analysis"]["socket_recommendations"].append({
                    "socket_id": socket.node_id,
                    "socket_name": socket.name if hasattr(socket, 'name') else f"Socket {socket.node_id}",
                    "nodes_in_radius": len(nodes_in_radius),
                    "notables_in_radius": notable_count,
                    "currently_socketed": socket.node_id in allocated_nodes,
                })

            # Sort by notables in radius
            result["timeless_analysis"]["socket_recommendations"].sort(
                key=lambda x: x["notables_in_radius"], reverse=True
            )
        except Exception as e:
            logger.debug("Timeless jewel analysis failed", exc_info=True)
            result["timeless_analysis"] = {"error": str(e)}

    # Cluster jewel analysis
    if analyze_clusters and registry.has_cluster_jewels():
        try:
            from src.pob.jewel.cluster_optimizer import ClusterNotableOptimizer

            output.progress("Analyzing cluster jewel notables...")
            cluster_optimizer = ClusterNotableOptimizer(calculator=None)

            result["cluster_analysis"] = {"clusters": []}

            subgraphs = registry.get_cluster_subgraphs(allocated_nodes)
            for subgraph in subgraphs:
                # Get notable names
                allocated_notables = []
                available_notables = []
                for notable_id in subgraph.notables:
                    node = subgraph.nodes.get(notable_id)
                    if node:
                        if notable_id in allocated_nodes:
                            allocated_notables.append(node.name)
                        else:
                            available_notables.append(node.name)

                result["cluster_analysis"]["clusters"].append({
                    "socket_id": subgraph.socket_node,
                    "total_notables": len(subgraph.notables),
                    "allocated_notables": allocated_notables,
                    "available_notables": available_notables,
                    "optimization_potential": len(available_notables) > 0,
                })
        except Exception as e:
            logger.debug("Cluster jewel analysis failed", exc_info=True)
            result["cluster_analysis"] = {"error": str(e)}

    output.output(result, title="JEWEL INFORMATION")

    # Print summary if not JSON
    if not json_output and not output_file:
        click.echo("\nFor optimizer:")
        click.echo(f"  {len(protected_nodes)} nodes are protected from modification")
        if result["protected_nodes"]["jewel_sockets"]:
            click.echo(f"  Jewel sockets: {result['protected_nodes']['jewel_sockets']}")
        if result["protected_nodes"]["cluster_nodes"]:
            click.echo(f"  Cluster nodes: {len(result['protected_nodes']['cluster_nodes'])} nodes")

        # Thread of Hope analysis summary
        if "thread_of_hope_analysis" in result and "placements" in result["thread_of_hope_analysis"]:
            placements = result["thread_of_hope_analysis"]["placements"]
            if placements:
                click.echo("\nThread of Hope Analysis:")
                for p in placements[:5]:  # Top 5 overall
                    click.echo(
                        f"  Socket {p['socket_id']} ({p['ring_size']}): "
                        f"{p['notable_count']} notables, score={p['value_score']}"
                    )
                    if p['notables']:
                        click.echo(f"    Notables: {', '.join(p['notables'][:3])}")

        # Timeless analysis summary
        if "timeless_analysis" in result and "socket_recommendations" in result["timeless_analysis"]:
            recs = result["timeless_analysis"]["socket_recommendations"]
            if recs:
                click.echo("\nTimeless Jewel Socket Recommendations:")
                for r in recs[:5]:
                    status = "allocated" if r["currently_socketed"] else "not allocated"
                    click.echo(
                        f"  {r['socket_name']}: {r['notables_in_radius']} notables in radius ({status})"
                    )

        # Cluster analysis summary
        if "cluster_analysis" in result and "clusters" in result["cluster_analysis"]:
            clusters = result["cluster_analysis"]["clusters"]
            if clusters:
                click.echo("\nCluster Jewel Analysis:")
                for c in clusters:
                    click.echo(
                        f"  Socket {c['socket_id']}: "
                        f"{len(c['allocated_notables'])}/{c['total_notables']} notables allocated"
                    )
                    if c['available_notables']:
                        click.echo(f"    Available: {', '.join(c['available_notables'][:3])}")

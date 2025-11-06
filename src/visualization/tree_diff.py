"""
Tree Difference Visualization

Visualizes differences between two passive skill trees.
Shows nodes added, removed, and mastery changes.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional

logger = logging.getLogger(__name__)


def visualize_tree_diff(
    original_xml: str,
    optimized_xml: str,
    output_file: str = "tree_diff.txt",
    tree_parser=None,
):
    """
    Create visual representation of tree differences.

    Shows:
    - Nodes added (with names and stats)
    - Nodes removed (with names and stats)
    - Mastery changes
    - Net point change

    Args:
        original_xml: Original build XML
        optimized_xml: Optimized build XML
        output_file: Path to save text report
        tree_parser: PassiveTreeGraph for node lookups (optional)

    Returns:
        Path to output file if successful, None otherwise
    """
    from ..pob.modifier import get_passive_tree_summary

    # Get summaries
    original_summary = get_passive_tree_summary(original_xml)
    optimized_summary = get_passive_tree_summary(optimized_xml)

    original_nodes = set(original_summary['allocated_nodes'])
    optimized_nodes = set(optimized_summary['allocated_nodes'])
    original_masteries = original_summary['mastery_effects']
    optimized_masteries = optimized_summary['mastery_effects']

    # Calculate differences
    nodes_added = optimized_nodes - original_nodes
    nodes_removed = original_nodes - optimized_nodes
    net_change = len(optimized_nodes) - len(original_nodes)

    # Find mastery changes
    mastery_changes = []
    all_mastery_nodes = set(original_masteries.keys()) | set(optimized_masteries.keys())

    for node_id in all_mastery_nodes:
        old_effect = original_masteries.get(node_id)
        new_effect = optimized_masteries.get(node_id)

        if old_effect != new_effect:
            mastery_changes.append((node_id, old_effect, new_effect))

    # Create report
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("PASSIVE TREE DIFFERENCES")
    report_lines.append("="*80)
    report_lines.append("")

    # Summary
    report_lines.append("📊 Summary:")
    report_lines.append(f"   Original points: {len(original_nodes)}")
    report_lines.append(f"   Optimized points: {len(optimized_nodes)}")
    report_lines.append(f"   Net change: {net_change:+d} points")
    report_lines.append(f"   Nodes added: {len(nodes_added)}")
    report_lines.append(f"   Nodes removed: {len(nodes_removed)}")
    report_lines.append(f"   Masteries changed: {len(mastery_changes)}")
    report_lines.append("")

    # Nodes added
    if nodes_added:
        report_lines.append("✅ NODES ADDED:")
        report_lines.append("")

        if tree_parser:
            for node_id in sorted(nodes_added):
                node = tree_parser.get_node(node_id)
                if node:
                    report_lines.append(f"   + Node {node_id}: {node.name} ({node.node_type})")
                    if node.stats:
                        for stat in node.stats:
                            report_lines.append(f"      └─ {stat}")
                else:
                    report_lines.append(f"   + Node {node_id}: (name unknown)")
                report_lines.append("")
        else:
            for node_id in sorted(nodes_added):
                report_lines.append(f"   + Node {node_id}")
        report_lines.append("")

    # Nodes removed
    if nodes_removed:
        report_lines.append("❌ NODES REMOVED:")
        report_lines.append("")

        if tree_parser:
            for node_id in sorted(nodes_removed):
                node = tree_parser.get_node(node_id)
                if node:
                    report_lines.append(f"   - Node {node_id}: {node.name} ({node.node_type})")
                    if node.stats:
                        for stat in node.stats:
                            report_lines.append(f"      └─ {stat}")
                else:
                    report_lines.append(f"   - Node {node_id}: (name unknown)")
                report_lines.append("")
        else:
            for node_id in sorted(nodes_removed):
                report_lines.append(f"   - Node {node_id}")
        report_lines.append("")

    # Mastery changes
    if mastery_changes:
        report_lines.append("🎯 MASTERY CHANGES:")
        report_lines.append("")

        if tree_parser:
            from ..pob.mastery_optimizer import get_mastery_database
            try:
                mastery_db = get_mastery_database()

                for node_id, old_effect, new_effect in mastery_changes:
                    node = tree_parser.get_node(node_id)
                    node_name = node.name if node else f"Node {node_id}"

                    report_lines.append(f"   ✏️  {node_name} (Node {node_id}):")

                    if old_effect is None:
                        report_lines.append(f"      Added mastery effect {new_effect}")
                    elif new_effect is None:
                        report_lines.append(f"      Removed mastery effect {old_effect}")
                    else:
                        # Try to get effect details
                        if node_id in mastery_db.masteries:
                            mastery_node = mastery_db.masteries[node_id]

                            old_effect_obj = mastery_db.effect_lookup.get(old_effect)
                            new_effect_obj = mastery_db.effect_lookup.get(new_effect)

                            if old_effect_obj:
                                report_lines.append(f"      Old: {old_effect_obj.stats[0] if old_effect_obj.stats else f'Effect {old_effect}'}")
                            else:
                                report_lines.append(f"      Old: Effect {old_effect}")

                            if new_effect_obj:
                                report_lines.append(f"      New: {new_effect_obj.stats[0] if new_effect_obj.stats else f'Effect {new_effect}'}")
                            else:
                                report_lines.append(f"      New: Effect {new_effect}")
                        else:
                            report_lines.append(f"      Changed: {old_effect} → {new_effect}")

                    report_lines.append("")
            except Exception as e:
                logger.debug(f"Could not load mastery details: {e}")
                for node_id, old_effect, new_effect in mastery_changes:
                    report_lines.append(f"   ✏️  Mastery Node {node_id}: {old_effect} → {new_effect}")
        else:
            for node_id, old_effect, new_effect in mastery_changes:
                report_lines.append(f"   ✏️  Mastery Node {node_id}: {old_effect} → {new_effect}")

        report_lines.append("")

    # No changes
    if not nodes_added and not nodes_removed and not mastery_changes:
        report_lines.append("   No tree changes (trees are identical)")
        report_lines.append("")

    report_lines.append("="*80)

    # Write to file
    report = "\n".join(report_lines)

    with open(output_file, 'w') as f:
        f.write(report)

    logger.info(f"Saved tree diff report to {output_file}")

    # Also print to console
    print(report)

    return output_file


def create_tree_diff_report(
    original_xml: str,
    optimized_xml: str,
    output_dir: str = "tree_diff",
    base_name: str = "diff",
):
    """
    Create comprehensive tree difference report.

    Args:
        original_xml: Original build XML
        optimized_xml: Optimized build XML
        output_dir: Directory to save reports
        base_name: Base name for output files

    Returns:
        Dict mapping report type to file path
    """
    import os

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    files = {}

    # Try to load tree parser for detailed names
    tree_parser = None
    try:
        from ..pob.tree_parser import load_passive_tree
        tree_parser = load_passive_tree()
        logger.info("Loaded tree parser for detailed node names")
    except Exception as e:
        logger.debug(f"Could not load tree parser: {e}")

    # Text report with names
    file1 = os.path.join(output_dir, f"{base_name}_report.txt")
    result = visualize_tree_diff(original_xml, optimized_xml, file1, tree_parser)
    if result:
        files['text_report'] = result

    logger.info(f"Created tree diff report in {output_dir}")
    return files


def get_tree_diff_summary(original_xml: str, optimized_xml: str) -> Dict:
    """
    Get summary of tree differences as a dictionary.

    Args:
        original_xml: Original build XML
        optimized_xml: Optimized build XML

    Returns:
        Dict with keys: nodes_added, nodes_removed, net_change, mastery_changes
    """
    from ..pob.modifier import get_passive_tree_summary

    original_summary = get_passive_tree_summary(original_xml)
    optimized_summary = get_passive_tree_summary(optimized_xml)

    original_nodes = set(original_summary['allocated_nodes'])
    optimized_nodes = set(optimized_summary['allocated_nodes'])
    original_masteries = original_summary['mastery_effects']
    optimized_masteries = optimized_summary['mastery_effects']

    nodes_added = optimized_nodes - original_nodes
    nodes_removed = original_nodes - optimized_nodes
    net_change = len(optimized_nodes) - len(original_nodes)

    # Count mastery changes
    mastery_changes = 0
    all_mastery_nodes = set(original_masteries.keys()) | set(optimized_masteries.keys())

    for node_id in all_mastery_nodes:
        old_effect = original_masteries.get(node_id)
        new_effect = optimized_masteries.get(node_id)
        if old_effect != new_effect:
            mastery_changes += 1

    return {
        'nodes_added': list(nodes_added),
        'nodes_removed': list(nodes_removed),
        'net_change': net_change,
        'mastery_changes': mastery_changes,
        'original_count': len(original_nodes),
        'optimized_count': len(optimized_nodes),
    }


def print_tree_diff_summary(original_xml: str, optimized_xml: str):
    """
    Print a quick summary of tree differences to console.

    Args:
        original_xml: Original build XML
        optimized_xml: Optimized build XML
    """
    summary = get_tree_diff_summary(original_xml, optimized_xml)

    print(f"\n{'='*60}")
    print("TREE OPTIMIZATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Original points:     {summary['original_count']}")
    print(f"  Optimized points:    {summary['optimized_count']}")
    print(f"  Net change:          {summary['net_change']:+d} points")
    print(f"  Nodes added:         {len(summary['nodes_added'])}")
    print(f"  Nodes removed:       {len(summary['nodes_removed'])}")
    print(f"  Masteries changed:   {summary['mastery_changes']}")
    print(f"{'='*60}\n")

"""
Pareto Frontier Visualization

Provides 2D and 3D visualization of Pareto frontiers for multi-objective optimization.
Shows trade-offs between DPS, Life, and EHP objectives.
"""

import logging
from typing import List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

# Try to import plotting libraries (optional dependencies)
try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available - install with: pip install matplotlib")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly not available - install with: pip install plotly")


def plot_pareto_frontier_3d(
    frontier,
    output_file: str = "pareto_frontier_3d.html",
    title: str = "Pareto Frontier: DPS vs Life vs EHP",
    interactive: bool = True,
):
    """
    Create 3D visualization of Pareto frontier.

    Args:
        frontier: ParetoFrontier object
        output_file: Path to save HTML file
        title: Plot title
        interactive: If True, create interactive Plotly plot. Otherwise use matplotlib.

    Returns:
        Path to output file if successful, None otherwise
    """
    if frontier.size() == 0:
        logger.warning("Empty frontier - nothing to plot")
        return None

    # Extract data from frontier
    individuals = frontier.individuals
    dps = [ind.score.dps_percent for ind in individuals]
    life = [ind.score.life_percent for ind in individuals]
    ehp = [ind.score.ehp_percent for ind in individuals]

    # Create labels for hover
    labels = []
    extremes = frontier.get_extreme_points()
    balanced = frontier.get_balanced_solution()

    for ind in individuals:
        label = []
        if extremes.get('max_dps') == ind:
            label.append("Max DPS")
        if extremes.get('max_life') == ind:
            label.append("Max Life")
        if extremes.get('max_ehp') == ind:
            label.append("Max EHP")
        if balanced == ind:
            label.append("Balanced")

        if label:
            labels.append(" / ".join(label))
        else:
            labels.append("")

    if interactive and PLOTLY_AVAILABLE:
        return _plot_frontier_plotly(dps, life, ehp, labels, output_file, title)
    elif MATPLOTLIB_AVAILABLE:
        return _plot_frontier_matplotlib(dps, life, ehp, labels, output_file, title)
    else:
        logger.error("No plotting library available. Install matplotlib or plotly.")
        return None


def _plot_frontier_plotly(
    dps: List[float],
    life: List[float],
    ehp: List[float],
    labels: List[str],
    output_file: str,
    title: str,
) -> str:
    """Create interactive 3D plot with Plotly."""
    # Create hover text
    hover_text = []
    for i in range(len(dps)):
        text = f"DPS: +{dps[i]:.1f}%<br>Life: +{life[i]:.1f}%<br>EHP: +{ehp[i]:.1f}%"
        if labels[i]:
            text += f"<br><b>{labels[i]}</b>"
        hover_text.append(text)

    # Create colors (highlight special points)
    colors = []
    sizes = []
    for label in labels:
        if label:
            colors.append('red')  # Special points in red
            sizes.append(12)
        else:
            colors.append('blue')  # Regular points in blue
            sizes.append(8)

    # Create 3D scatter plot
    fig = go.Figure(data=[
        go.Scatter3d(
            x=dps,
            y=life,
            z=ehp,
            mode='markers+text',
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.8,
                line=dict(color='black', width=1)
            ),
            text=labels,
            textposition='top center',
            textfont=dict(size=10, color='black'),
            hovertext=hover_text,
            hoverinfo='text',
            name='Pareto Frontier'
        )
    ])

    # Update layout
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis=dict(title='DPS Improvement (%)', backgroundcolor="rgb(230, 230,230)"),
            yaxis=dict(title='Life Improvement (%)', backgroundcolor="rgb(230, 230,230)"),
            zaxis=dict(title='EHP Improvement (%)', backgroundcolor="rgb(230, 230,230)"),
        ),
        width=1000,
        height=800,
        showlegend=True
    )

    # Save to HTML
    fig.write_html(output_file)
    logger.info(f"Saved 3D Pareto frontier to {output_file}")
    return output_file


def _plot_frontier_matplotlib(
    dps: List[float],
    life: List[float],
    ehp: List[float],
    labels: List[str],
    output_file: str,
    title: str,
) -> str:
    """Create static 3D plot with matplotlib."""
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')

    # Plot regular points
    regular_indices = [i for i, label in enumerate(labels) if not label]
    if regular_indices:
        ax.scatter(
            [dps[i] for i in regular_indices],
            [life[i] for i in regular_indices],
            [ehp[i] for i in regular_indices],
            c='blue',
            marker='o',
            s=50,
            alpha=0.6,
            label='Frontier Solutions'
        )

    # Plot special points
    special_indices = [i for i, label in enumerate(labels) if label]
    if special_indices:
        ax.scatter(
            [dps[i] for i in special_indices],
            [life[i] for i in special_indices],
            [ehp[i] for i in special_indices],
            c='red',
            marker='*',
            s=200,
            alpha=1.0,
            label='Key Solutions',
            edgecolors='black',
            linewidths=1
        )

        # Add labels
        for i in special_indices:
            ax.text(dps[i], life[i], ehp[i], f'  {labels[i]}',
                   fontsize=9, weight='bold')

    # Set labels
    ax.set_xlabel('DPS Improvement (%)', fontsize=11, weight='bold')
    ax.set_ylabel('Life Improvement (%)', fontsize=11, weight='bold')
    ax.set_zlabel('EHP Improvement (%)', fontsize=11, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold')

    # Add legend
    ax.legend(loc='upper left')

    # Add grid
    ax.grid(True, alpha=0.3)

    # Save to file
    output_file_png = output_file.replace('.html', '.png')
    plt.savefig(output_file_png, dpi=150, bbox_inches='tight')
    logger.info(f"Saved 3D Pareto frontier to {output_file_png}")
    plt.close()

    return output_file_png


def plot_pareto_frontier_2d(
    frontier,
    objective1: str = 'dps',
    objective2: str = 'life',
    output_file: str = "pareto_frontier_2d.png",
    title: Optional[str] = None,
):
    """
    Create 2D projection of Pareto frontier.

    Args:
        frontier: ParetoFrontier object
        objective1: First objective ('dps', 'life', or 'ehp')
        objective2: Second objective ('dps', 'life', or 'ehp')
        output_file: Path to save PNG file
        title: Plot title (auto-generated if None)

    Returns:
        Path to output file if successful, None otherwise
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("matplotlib not available. Install with: pip install matplotlib")
        return None

    if frontier.size() == 0:
        logger.warning("Empty frontier - nothing to plot")
        return None

    # Extract data
    individuals = frontier.individuals
    obj1_values = [getattr(ind.score, f'{objective1}_percent') for ind in individuals]
    obj2_values = [getattr(ind.score, f'{objective2}_percent') for ind in individuals]

    # Create plot
    plt.figure(figsize=(10, 8))

    # Plot all points
    plt.scatter(obj1_values, obj2_values, c='blue', marker='o', s=100,
                alpha=0.6, edgecolors='black', linewidths=1, label='Frontier')

    # Highlight extremes
    extremes = frontier.get_extreme_points()
    for key, ind in extremes.items():
        x = getattr(ind.score, f'{objective1}_percent')
        y = getattr(ind.score, f'{objective2}_percent')
        plt.scatter(x, y, c='red', marker='*', s=300,
                   edgecolors='black', linewidths=1.5)
        plt.annotate(key.replace('max_', '').upper(), (x, y),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=10, weight='bold')

    # Highlight balanced
    balanced = frontier.get_balanced_solution()
    if balanced:
        x = getattr(balanced.score, f'{objective1}_percent')
        y = getattr(balanced.score, f'{objective2}_percent')
        plt.scatter(x, y, c='green', marker='D', s=200,
                   edgecolors='black', linewidths=1.5, label='Balanced')

    # Labels
    plt.xlabel(f'{objective1.upper()} Improvement (%)', fontsize=12, weight='bold')
    plt.ylabel(f'{objective2.upper()} Improvement (%)', fontsize=12, weight='bold')

    if title is None:
        title = f'Pareto Frontier: {objective1.upper()} vs {objective2.upper()}'
    plt.title(title, fontsize=14, weight='bold')

    plt.grid(True, alpha=0.3)
    plt.legend()

    # Save
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    logger.info(f"Saved 2D Pareto frontier to {output_file}")
    plt.close()

    return output_file


def plot_all_projections(
    frontier,
    output_dir: str = "plots",
    base_name: str = "pareto_frontier",
):
    """
    Create all 2D projections of the Pareto frontier.

    Creates three 2D plots:
    - DPS vs Life
    - DPS vs EHP
    - Life vs EHP

    Args:
        frontier: ParetoFrontier object
        output_dir: Directory to save plots
        base_name: Base name for output files

    Returns:
        List of created file paths
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("matplotlib not available")
        return []

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    files = []

    # DPS vs Life
    file1 = os.path.join(output_dir, f"{base_name}_dps_vs_life.png")
    result = plot_pareto_frontier_2d(frontier, 'dps', 'life', file1)
    if result:
        files.append(result)

    # DPS vs EHP
    file2 = os.path.join(output_dir, f"{base_name}_dps_vs_ehp.png")
    result = plot_pareto_frontier_2d(frontier, 'dps', 'ehp', file2)
    if result:
        files.append(result)

    # Life vs EHP
    file3 = os.path.join(output_dir, f"{base_name}_life_vs_ehp.png")
    result = plot_pareto_frontier_2d(frontier, 'life', 'ehp', file3)
    if result:
        files.append(result)

    logger.info(f"Created {len(files)} 2D projection plots in {output_dir}")
    return files

"""
Visualization module for POE Build Optimizer.

Provides visualization tools for:
- Pareto frontier (3D plots)
- Evolution progress (line charts)
- Tree differences (node comparison)
"""

from .frontier_plot import plot_pareto_frontier_3d, plot_pareto_frontier_2d
from .evolution_plot import plot_evolution_progress, plot_fitness_distribution
from .tree_diff import visualize_tree_diff, create_tree_diff_report

__all__ = [
    'plot_pareto_frontier_3d',
    'plot_pareto_frontier_2d',
    'plot_evolution_progress',
    'plot_fitness_distribution',
    'visualize_tree_diff',
    'create_tree_diff_report',
]

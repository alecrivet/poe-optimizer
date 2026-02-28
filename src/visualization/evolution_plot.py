"""
Evolution Progress Visualization

Visualizes genetic algorithm evolution over generations.
Shows fitness progress, convergence, and population distribution.
"""

import logging
from typing import List, Optional, Dict
import os

logger = logging.getLogger(__name__)

# Try to import matplotlib (optional dependency)
try:
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available - install with: pip install matplotlib")


def plot_evolution_progress(
    best_fitness_history: List[float],
    avg_fitness_history: List[float],
    output_file: str = "evolution_progress.png",
    title: str = "Genetic Algorithm Evolution Progress",
    objective: str = "fitness",
):
    """
    Plot fitness evolution over generations.

    Shows:
    - Best fitness in each generation (line)
    - Average fitness in each generation (line)
    - Shaded area between best and avg

    Args:
        best_fitness_history: Best fitness value in each generation
        avg_fitness_history: Average fitness value in each generation
        output_file: Path to save PNG file
        title: Plot title
        objective: Objective name for y-axis label

    Returns:
        Path to output file if successful, None otherwise
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("matplotlib not available. Install with: pip install matplotlib")
        return None

    if not best_fitness_history:
        logger.warning("Empty fitness history - nothing to plot")
        return None

    generations = list(range(1, len(best_fitness_history) + 1))

    # Create figure
    fig, ax = plt.figure(figsize=(12, 7)), plt.gca()

    # Plot best fitness
    ax.plot(generations, best_fitness_history,
            label='Best Fitness', color='darkgreen', linewidth=2.5,
            marker='o', markersize=4)

    # Plot average fitness
    ax.plot(generations, avg_fitness_history,
            label='Average Fitness', color='steelblue', linewidth=2,
            marker='s', markersize=3, alpha=0.8)

    # Fill area between
    ax.fill_between(generations, best_fitness_history, avg_fitness_history,
                     alpha=0.2, color='lightblue', label='Population Spread')

    # Annotate final values
    final_best = best_fitness_history[-1]
    final_avg = avg_fitness_history[-1]
    ax.annotate(f'Final Best:\n{final_best:+.2f}%',
                xy=(generations[-1], final_best),
                xytext=(-80, 20), textcoords='offset points',
                fontsize=10, weight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', lw=1.5))

    # Annotate initial improvement
    initial_best = best_fitness_history[0]
    total_improvement = final_best - initial_best
    if len(generations) > 5:
        ax.annotate(f'Total Gain:\n{total_improvement:+.2f}%',
                    xy=(generations[0], initial_best),
                    xytext=(30, -30), textcoords='offset points',
                    fontsize=10, weight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3', lw=1.5))

    # Labels and formatting
    ax.set_xlabel('Generation', fontsize=12, weight='bold')
    ax.set_ylabel(f'{objective.capitalize()} Improvement (%)', fontsize=12, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='lower right', fontsize=10)

    # Add horizontal line at 0
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    logger.info(f"Saved evolution progress to {output_file}")
    plt.close()

    return output_file


def plot_fitness_distribution(
    final_population,
    output_file: str = "fitness_distribution.png",
    title: str = "Final Population Fitness Distribution",
    objective: str = "fitness",
):
    """
    Plot fitness distribution of final population.

    Shows histogram of fitness values with statistics.

    Args:
        final_population: Population object with individuals
        output_file: Path to save PNG file
        title: Plot title
        objective: Objective name for labels

    Returns:
        Path to output file if successful, None otherwise
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("matplotlib not available")
        return None

    # Extract fitness values
    fitness_values = [ind.fitness for ind in final_population.individuals]

    if not fitness_values:
        logger.warning("Empty population - nothing to plot")
        return None

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot histogram
    n, bins, patches = ax.hist(fitness_values, bins=15, color='skyblue',
                                edgecolor='black', alpha=0.7)

    # Color the best bin differently
    max_fitness = max(fitness_values)
    for i, patch in enumerate(patches):
        if bins[i] <= max_fitness < bins[i+1]:
            patch.set_facecolor('lightgreen')

    # Add statistics
    mean_fitness = sum(fitness_values) / len(fitness_values)
    median_fitness = sorted(fitness_values)[len(fitness_values) // 2]

    # Add vertical lines for statistics
    ax.axvline(mean_fitness, color='red', linestyle='--', linewidth=2,
               label=f'Mean: {mean_fitness:+.2f}%')
    ax.axvline(median_fitness, color='orange', linestyle='--', linewidth=2,
               label=f'Median: {median_fitness:+.2f}%')
    ax.axvline(max_fitness, color='darkgreen', linestyle='--', linewidth=2.5,
               label=f'Best: {max_fitness:+.2f}%')

    # Labels
    ax.set_xlabel(f'{objective.capitalize()} Improvement (%)', fontsize=12, weight='bold')
    ax.set_ylabel('Number of Individuals', fontsize=12, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    logger.info(f"Saved fitness distribution to {output_file}")
    plt.close()

    return output_file


def plot_convergence_analysis(
    best_fitness_history: List[float],
    output_file: str = "convergence_analysis.png",
    title: str = "Convergence Analysis",
    window_size: int = 5,
):
    """
    Analyze convergence by plotting improvement rate over time.

    Shows:
    - Fitness over time
    - Improvement rate (derivative)
    - Convergence point detection

    Args:
        best_fitness_history: Best fitness in each generation
        output_file: Path to save PNG file
        title: Plot title
        window_size: Window for smoothing improvement rate

    Returns:
        Path to output file if successful, None otherwise
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("matplotlib not available")
        return None

    if len(best_fitness_history) < window_size + 1:
        logger.warning("Not enough generations for convergence analysis")
        return None

    import numpy as np

    generations = np.array(range(1, len(best_fitness_history) + 1))
    fitness = np.array(best_fitness_history)

    # Calculate improvement rate (derivative)
    improvement_rate = np.diff(fitness)
    improvement_rate_gens = generations[1:]

    # Smooth improvement rate
    if len(improvement_rate) >= window_size:
        smoothed_rate = np.convolve(improvement_rate,
                                     np.ones(window_size)/window_size,
                                     mode='valid')
        smoothed_rate_gens = improvement_rate_gens[window_size-1:]
    else:
        smoothed_rate = improvement_rate
        smoothed_rate_gens = improvement_rate_gens

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    # Plot 1: Fitness over time
    ax1.plot(generations, fitness, color='darkgreen', linewidth=2, marker='o', markersize=4)
    ax1.set_ylabel('Best Fitness (%)', fontsize=11, weight='bold')
    ax1.set_title(title, fontsize=14, weight='bold')
    ax1.grid(True, alpha=0.3)

    # Annotate best
    best_gen = np.argmax(fitness) + 1
    best_fitness = np.max(fitness)
    ax1.annotate(f'Best: {best_fitness:+.2f}%\n@ Gen {best_gen}',
                 xy=(best_gen, best_fitness),
                 xytext=(20, -30), textcoords='offset points',
                 fontsize=9, weight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7),
                 arrowprops=dict(arrowstyle='->', lw=1.5))

    # Plot 2: Improvement rate
    ax2.bar(improvement_rate_gens, improvement_rate, alpha=0.5, color='steelblue',
            label='Per-generation Improvement', width=0.8)

    if len(smoothed_rate) > 0:
        ax2.plot(smoothed_rate_gens, smoothed_rate, color='darkblue', linewidth=2.5,
                label=f'Smoothed ({window_size}-gen average)')

    ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
    ax2.set_xlabel('Generation', fontsize=11, weight='bold')
    ax2.set_ylabel('Improvement Rate (% per gen)', fontsize=11, weight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right', fontsize=9)

    # Detect convergence point (when improvement rate drops below threshold)
    convergence_threshold = 0.05  # 0.05% improvement per generation
    if len(smoothed_rate) > 0:
        convergence_mask = smoothed_rate < convergence_threshold
        if np.any(convergence_mask):
            convergence_gen = smoothed_rate_gens[np.argmax(convergence_mask)]
            ax2.axvline(convergence_gen, color='red', linestyle='--', linewidth=1.5,
                       alpha=0.7, label=f'Convergence @ Gen {convergence_gen}')
            ax2.legend(loc='upper right', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    logger.info(f"Saved convergence analysis to {output_file}")
    plt.close()

    return output_file


def create_evolution_report(
    result,
    output_dir: str = "evolution_plots",
    base_name: str = "evolution",
):
    """
    Create complete evolution report with all plots.

    Creates:
    - Evolution progress plot
    - Fitness distribution plot
    - Convergence analysis plot

    Args:
        result: GeneticOptimizationResult object
        output_dir: Directory to save plots
        base_name: Base name for output files

    Returns:
        Dict mapping plot type to file path
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("matplotlib not available")
        return {}

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    files = {}

    # Evolution progress
    file1 = os.path.join(output_dir, f"{base_name}_progress.png")
    result_file = plot_evolution_progress(
        result.best_fitness_history,
        result.avg_fitness_history,
        file1
    )
    if result_file:
        files['progress'] = result_file

    # Fitness distribution
    file2 = os.path.join(output_dir, f"{base_name}_distribution.png")
    result_file = plot_fitness_distribution(
        result.final_population,
        file2
    )
    if result_file:
        files['distribution'] = result_file

    # Convergence analysis
    file3 = os.path.join(output_dir, f"{base_name}_convergence.png")
    result_file = plot_convergence_analysis(
        result.best_fitness_history,
        file3
    )
    if result_file:
        files['convergence'] = result_file

    logger.info(f"Created {len(files)} evolution plots in {output_dir}")
    return files

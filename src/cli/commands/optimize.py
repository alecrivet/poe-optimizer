"""
Optimize command - Main optimization workflow.
"""

import click
import logging
import time
from typing import Optional

from ..utils import InputHandler, get_output_handler, common_options, input_argument

logger = logging.getLogger(__name__)


@click.command()
@input_argument
@click.option(
    "--objective", "-O",
    type=click.Choice(["dps", "life", "ehp", "balanced", "es", "mana"]),
    default="dps",
    help="Optimization objective. Default: dps"
)
@click.option(
    "--algorithm", "-a",
    type=click.Choice(["greedy", "genetic", "multi"]),
    default="greedy",
    help="Algorithm to use. Default: greedy"
)
@click.option(
    "--iterations", "-i",
    type=int,
    default=50,
    help="Max iterations for greedy algorithm. Default: 50"
)
@click.option(
    "--generations", "-g",
    type=int,
    default=50,
    help="Generations for genetic algorithm. Default: 50"
)
@click.option(
    "--population-size", "-p",
    type=int,
    default=30,
    help="Population size for genetic algorithm. Default: 30"
)
@click.option(
    "--mutation-rate",
    type=float,
    default=0.2,
    help="Mutation rate for genetic algorithm. Default: 0.2"
)
@click.option(
    "--allow-point-change/--no-point-change",
    default=False,
    help="Allow adding/removing passive points. Default: no"
)
@click.option(
    "--max-point-change",
    type=int,
    default=5,
    help="Maximum point change allowed. Default: 5"
)
@click.option(
    "--optimize-masteries/--no-masteries",
    default=True,
    help="Optimize mastery selections. Default: yes"
)
@click.option(
    "--protect-jewels/--no-protect-jewels",
    default=True,
    help="Protect jewel sockets and cluster nodes. Default: yes"
)
@click.option(
    "--min-life",
    type=int,
    default=None,
    help="Minimum life constraint."
)
@click.option(
    "--min-ehp",
    type=int,
    default=None,
    help="Minimum EHP constraint."
)
@click.option(
    "--max-points",
    type=int,
    default=None,
    help="Explicit maximum passive point cap (overrides auto-detection from level)."
)
@click.option(
    "--disable-constraints",
    is_flag=True,
    default=False,
    help="Disable point budget constraints. Default: constraints enabled."
)
@click.option(
    "--pob-code", "-c",
    is_flag=True,
    help="Output PoB code instead of stats."
)
@common_options
@click.pass_context
def optimize(
    ctx,
    input_source: str,
    objective: str,
    algorithm: str,
    iterations: int,
    generations: int,
    population_size: int,
    mutation_rate: float,
    allow_point_change: bool,
    max_point_change: int,
    optimize_masteries: bool,
    protect_jewels: bool,
    min_life: Optional[int],
    min_ehp: Optional[int],
    max_points: Optional[int],
    disable_constraints: bool,
    pob_code: bool,
    json_output: bool,
    output_file: Optional[str],
):
    """
    Optimize a build's passive tree.

    \b
    INPUT can be:
      - Path to XML file (build.xml)
      - Path to PoB code file (build.txt)
      - PoB code string
      - "-" for stdin

    \b
    Examples:
      poe-optimizer optimize build.xml --objective dps
      poe-optimizer optimize build.xml -O life -a genetic -g 100
      poe-optimizer optimize build.xml --min-life 5000
      cat build.xml | poe-optimizer optimize - -O balanced
    """
    from src.pob.codec import encode_pob_code
    from src.pob.modifier import get_passive_tree_summary
    from src.pob.jewel.registry import JewelRegistry

    output = get_output_handler(ctx, json_output, output_file)

    # Load input
    output.progress(f"Loading build from {input_source}...")
    try:
        build_xml = InputHandler.load(input_source)
    except (FileNotFoundError, IOError, ValueError) as e:
        raise click.ClickException(f"Failed to load build: {e}")

    # Show jewel info if protecting
    if protect_jewels:
        try:
            registry = JewelRegistry.from_build_xml(build_xml)
            summary = get_passive_tree_summary(build_xml)
            protected = registry.get_protected_nodes(set(summary["allocated_nodes"]))
            if protected:
                output.info(f"Protected nodes: {len(protected)} (jewel sockets + cluster nodes)")
        except Exception:
            logger.debug("Jewel parsing failed (optional)", exc_info=True)

    # Build constraints
    constraints = None
    if disable_constraints:
        from src.optimizer.constraints import ConstraintSet
        constraints = ConstraintSet()  # Empty constraint set — prevents auto-creation
        output.info("Constraints disabled")
    elif max_points is not None:
        from src.optimizer.constraints import ConstraintSet, PointBudgetConstraint
        constraints = ConstraintSet(
            point_budget=PointBudgetConstraint(max_points=max_points)
        )
        output.info(f"Point budget constraint: max {max_points} points")
    # Otherwise (constraints=None), auto_constraints_from_xml is called inside the optimizer

    # Select optimizer
    output.progress(f"Starting {algorithm} optimization for {objective}...")
    start_time = time.time()

    try:
        if algorithm == "greedy":
            from src.optimizer.tree_optimizer import GreedyTreeOptimizer

            optimizer = GreedyTreeOptimizer(
                max_iterations=iterations,
                min_improvement=0.1,
                optimize_masteries=optimize_masteries,
                constraints=constraints,
            )
            result = optimizer.optimize(
                build_xml,
                objective=objective,
                allow_point_increase=allow_point_change,
            )

            optimized_xml = result.optimized_xml
            improvements = {
                "dps_change": result.optimized_stats.dps_change_percent,
                "life_change": result.optimized_stats.life_change_percent,
                "ehp_change": result.optimized_stats.ehp_change_percent,
            }
            details = {
                "iterations": result.iterations,
                "modifications": len(result.modifications_applied),
            }

        elif algorithm == "genetic":
            from src.optimizer.genetic_optimizer import GeneticTreeOptimizer

            optimizer = GeneticTreeOptimizer(
                population_size=population_size,
                generations=generations,
                mutation_rate=mutation_rate,
                optimize_masteries=optimize_masteries,
                constraints=constraints,
            )
            result = optimizer.optimize(build_xml, objective=objective)

            optimized_xml = result.best_xml
            improvements = {
                "fitness": result.best_fitness,
            }
            if result.best_fitness_details:
                improvements.update({
                    "dps_change": result.best_fitness_details.dps_change_percent,
                    "life_change": result.best_fitness_details.life_change_percent,
                    "ehp_change": result.best_fitness_details.ehp_change_percent,
                })
            details = {
                "generations": result.generations,
                "final_population_size": len(result.final_population.individuals),
            }

        elif algorithm == "multi":
            from src.optimizer.multi_objective_optimizer import MultiObjectiveOptimizer

            optimizer = MultiObjectiveOptimizer(
                population_size=population_size,
                generations=generations,
            )
            result = optimizer.optimize(build_xml)

            # Use first Pareto-optimal solution
            if result.pareto_front:
                best = result.pareto_front[0]
                optimized_xml = best.xml
                improvements = {
                    "dps_change": best.objectives.get("dps", 0),
                    "life_change": best.objectives.get("life", 0),
                    "ehp_change": best.objectives.get("ehp", 0),
                }
            else:
                optimized_xml = build_xml
                improvements = {}
            details = {
                "generations": result.generations,
                "pareto_solutions": len(result.pareto_front),
            }

    except Exception as e:
        logger.debug("Optimization failed", exc_info=True)
        raise click.ClickException(f"Optimization failed: {e}")

    elapsed = time.time() - start_time

    # Display constraint violations as warnings
    violations = getattr(result, 'constraint_violations', [])
    for v in violations:
        output.warning(f"Constraint violation: {v}")

    # Generate PoB code
    optimized_code = encode_pob_code(optimized_xml)

    # Output results
    if pob_code:
        # Just output the PoB code
        if output_file:
            with open(output_file, "w") as f:
                f.write(optimized_code)
            output.success(f"PoB code saved to: {output_file}")
        else:
            click.echo(optimized_code)
    else:
        results = {
            "algorithm": algorithm,
            "objective": objective,
            "elapsed_seconds": round(elapsed, 1),
            "improvements": improvements,
            "details": details,
            "pob_code_length": len(optimized_code),
        }

        if json_output:
            results["pob_code"] = optimized_code
            output.output(results)
        else:
            output.output(results, title="OPTIMIZATION COMPLETE")
            click.echo(f"\nPoB Code ({len(optimized_code)} chars):")
            click.echo(f"  {optimized_code[:80]}...")
            click.echo(f"\nCopy the full code with: poe-optimizer optimize {input_source} --pob-code")

        # ALWAYS save PoB code to a .txt file alongside the output
        if output_file:
            pob_file = output_file.replace('.xml', '.txt').replace('.json', '.txt')
            if not pob_file.endswith('.txt'):
                pob_file += '.txt'
            with open(pob_file, "w") as f:
                f.write(optimized_code)
            output.info(f"PoB code also saved to: {pob_file}")

    output.success(f"Optimization completed in {elapsed:.1f}s")

# Configuration & Tuning Guide

This guide documents all configuration parameters for the PoE Build Optimizer and provides recommendations for different use cases.

## Table of Contents

1. [Greedy Optimizer Configuration](#greedy-optimizer-configuration)
2. [Genetic Algorithm Configuration](#genetic-algorithm-configuration)
3. [Multi-Objective Configuration](#multi-objective-configuration)
4. [Constraint Configuration](#constraint-configuration)
5. [Visualization Configuration](#visualization-configuration)
6. [Performance Tuning](#performance-tuning)
7. [Recommended Presets](#recommended-presets)

---

## Greedy Optimizer Configuration

### Constructor Parameters

```python
GreedyTreeOptimizer(
    max_iterations: int = 50,
    optimize_masteries: bool = True,
    verbose: bool = False,
)
```

### `max_iterations`

**Type:** `int`
**Default:** `50`
**Range:** `1` to `500`

Maximum number of optimization iterations. Each iteration:
1. Tries adding/removing each node
2. Keeps the best change
3. Stops if no improvement found

**Effect on Results:**
- **Lower (10-20):** Faster but may miss improvements
- **Default (50):** Good balance of speed and thoroughness
- **Higher (100-200):** More thorough, diminishing returns after 100

**Effect on Runtime:**
- ~2-3 seconds per iteration
- 50 iterations ≈ 2-3 minutes
- 100 iterations ≈ 5-6 minutes

**Recommendations:**

| Use Case | Value | Why |
|----------|-------|-----|
| Quick test | 10-20 | Fast feedback |
| Normal use | 50 | Good default |
| Maximum optimization | 100-150 | Thorough search |
| Debugging | 5 | Quick iterations |

**Example:**
```python
# Quick test
optimizer = GreedyTreeOptimizer(max_iterations=10)

# Thorough optimization
optimizer = GreedyTreeOptimizer(max_iterations=150)
```

### `optimize_masteries`

**Type:** `bool`
**Default:** `True`

Whether to optimize mastery selections after finding best node allocation.

**True:**
- Tries all mastery effects for allocated mastery nodes
- Picks best effect for each mastery
- Adds ~30 seconds to runtime
- Recommended for most use cases

**False:**
- Keeps original mastery selections
- Faster optimization
- Use only when masteries are already optimized

**Recommendations:**
- ✅ **Use True** for: New builds, optimization runs, final polish
- ❌ **Use False** for: Quick tests, mastery effects already optimal

### `verbose`

**Type:** `bool`
**Default:** `False`

Print progress information during optimization.

**True:**
```
Iteration 1: +2.5% DPS (added node 12345)
Iteration 2: +3.1% DPS (removed node 67890)
Iteration 3: +3.8% DPS (added node 11111)
...
Optimizing masteries...
Mastery [12345]: +1.2% DPS
Final result: +8.5% DPS
```

**False:**
- No output until complete
- Cleaner for scripts and automation

---

## Genetic Algorithm Configuration

### Constructor Parameters

```python
GeneticTreeOptimizer(
    population_size: int = 30,
    generations: int = 50,
    mutation_rate: float = 0.2,
    crossover_rate: float = 0.8,
    elitism_count: int = 5,
    tournament_size: int = 3,
    max_points_change: int = 10,
    optimize_masteries: bool = True,
)
```

### `population_size`

**Type:** `int`
**Default:** `30`
**Range:** `10` to `100`

Number of individuals (tree configurations) in the population.

**Effect on Results:**
- **Lower (10-20):** Less diversity, may converge prematurely
- **Default (30):** Good exploration vs exploitation balance
- **Higher (50-100):** Better exploration, more likely to find global optimum

**Effect on Runtime:**
- Runtime scales **linearly** with population size
- 30 individuals × 50 generations = 1,500 evaluations ≈ 10-15 minutes
- 50 individuals × 50 generations = 2,500 evaluations ≈ 20-25 minutes

**Recommendations:**

| Use Case | Value | Why |
|----------|-------|-----|
| Quick test | 10-15 | Faster iteration |
| Normal use | 30 | Good default |
| Thorough search | 50 | Better exploration |
| Research | 100 | Maximum diversity |

**Example:**
```python
# Fast genetic algorithm
optimizer = GeneticTreeOptimizer(population_size=15, generations=30)

# Thorough genetic algorithm
optimizer = GeneticTreeOptimizer(population_size=50, generations=100)
```

### `generations`

**Type:** `int`
**Default:** `50`
**Range:** `10` to `200`

Number of generations (evolution cycles).

**Effect on Results:**
- **Lower (20-30):** May not converge to optimum
- **Default (50):** Usually sufficient for convergence
- **Higher (100-200):** Better results, but diminishing returns after 100

**Effect on Runtime:**
- Runtime scales **linearly** with generations
- Each generation evaluates entire population
- 50 generations ≈ 10-15 minutes
- 100 generations ≈ 20-30 minutes

**Convergence Detection:**
The algorithm automatically detects convergence (no improvement for 10 generations) and may stop early.

**Recommendations:**

| Use Case | Value | Why |
|----------|-------|-----|
| Quick test | 20-30 | Fast results |
| Normal use | 50 | Good default |
| Maximum optimization | 100 | Ensure convergence |
| Research | 200 | Explore search space |

### `mutation_rate`

**Type:** `float`
**Default:** `0.2` (20%)
**Range:** `0.0` to `1.0`

Probability of mutation after crossover.

**Effect on Results:**
- **Lower (0.05-0.1):** Exploitation-focused, may get stuck
- **Default (0.2):** Good balance
- **Higher (0.4-0.5):** More exploration, may be too random

**What Mutation Does:**
- Randomly adds or removes nodes
- Changes mastery selections
- Introduces diversity to prevent stagnation

**Recommendations:**

| Use Case | Value | Why |
|----------|-------|-----|
| Fine-tuning | 0.1 | Small adjustments |
| Normal use | 0.2 | Good balance |
| Exploration | 0.3-0.4 | Find novel solutions |
| Random search | 0.5+ | Too random, not recommended |

**Example:**
```python
# Conservative (fine-tuning around good solution)
optimizer = GeneticTreeOptimizer(mutation_rate=0.1)

# Exploratory (finding novel solutions)
optimizer = GeneticTreeOptimizer(mutation_rate=0.35)
```

### `crossover_rate`

**Type:** `float`
**Default:** `0.8` (80%)
**Range:** `0.0` to `1.0`

Probability of crossover (combining parents).

**Effect on Results:**
- **Lower (0.5-0.6):** Less combination, more random
- **Default (0.8):** Standard for genetic algorithms
- **Higher (0.95):** Almost always combine parents

**What Crossover Does:**
- Takes two parent trees
- Combines their allocated nodes (union of common nodes + probabilistic unique nodes)
- Creates offspring inheriting traits from both parents

**Recommendations:**
- Use default `0.8` in most cases
- Lower to `0.6` if you want more random exploration
- Raise to `0.95` if you want incremental improvements

### `elitism_count`

**Type:** `int`
**Default:** `5`
**Range:** `0` to `population_size // 2`

Number of best individuals preserved across generations.

**Effect on Results:**
- **None (0):** May lose best solutions, not recommended
- **Low (2-3):** Less exploitation
- **Default (5):** Good preservation of good solutions
- **High (10+):** Less exploration, may converge too fast

**What Elitism Does:**
- Automatically keeps N best individuals
- Prevents losing good solutions
- Ensures monotonic improvement of best solution

**Recommendations:**

| Use Case | Value | Why |
|----------|-------|-----|
| Maximum exploration | 2-3 | Allow more change |
| Normal use | 5 | Good default |
| Exploitation | 10 | Quick convergence |
| No elitism | 0 | Not recommended |

**Formula:** `elitism_count ≈ population_size × 0.15`

### `tournament_size`

**Type:** `int`
**Default:** `3`
**Range:** `2` to `population_size // 3`

Number of individuals in tournament selection.

**Effect on Results:**
- **Smaller (2):** Less selection pressure, more diversity
- **Default (3):** Good balance
- **Larger (5-7):** Strong selection pressure, fast convergence

**What Tournament Selection Does:**
1. Randomly sample N individuals
2. Pick the best from the sample
3. Use as parent for reproduction

**Recommendations:**

| Use Case | Value | Why |
|----------|-------|-----|
| Maintain diversity | 2 | Weak selection |
| Normal use | 3 | Good balance |
| Fast convergence | 5 | Strong selection |

**Formula:** `tournament_size ≈ population_size × 0.1`

### `max_points_change`

**Type:** `int`
**Default:** `10`
**Range:** `0` to `50`

Maximum change in total points allocated from original build.

**Effect on Results:**
- **Smaller (5):** Stay close to original point count
- **Default (10):** Allow moderate reallocation
- **Larger (20+):** Significant tree restructuring

**Use Cases:**
- **0:** Only optimize node selection, keep point count exact
- **5:** Minor tweaks
- **10:** Standard optimization
- **20+:** Major rebuild

**Example:**
```python
# Keep point count exact
optimizer = GeneticTreeOptimizer(max_points_change=0)

# Allow major restructuring
optimizer = GeneticTreeOptimizer(max_points_change=25)
```

### `optimize_masteries`

Same as greedy optimizer. See [Greedy Optimizer - optimize_masteries](#optimize_masteries).

---

## Multi-Objective Configuration

### Pareto Frontier Calculation

```python
calculate_pareto_frontier(
    individuals: List[ParetoIndividual]
) -> ParetoFrontier
```

**No configuration parameters.** Automatically extracts non-dominated solutions.

### Pareto Ranks (NSGA-II)

```python
calculate_pareto_ranks(
    individuals: List[ParetoIndividual]
) -> List[List[ParetoIndividual]]
```

**No configuration parameters.** Returns fronts sorted by dominance rank.

### Crowding Distance

```python
calculate_crowding_distances(
    front: List[ParetoIndividual]
) -> None
```

**No configuration parameters.** Modifies individuals in-place with crowding distance.

---

## Constraint Configuration

### Point Budget Constraint

```python
PointBudgetConstraint(
    min_points: Optional[int] = None,
    max_points: Optional[int] = None
)
```

**`min_points`**: Minimum points required (usually `None`)
**`max_points`**: Maximum points allowed (from level)

**From Level:**
```python
constraint = PointBudgetConstraint.from_level(
    level: int,
    min_offset: int = 0
)
```

**Examples:**
```python
# Level 95 character (max 116 points)
constraint = PointBudgetConstraint.from_level(95)

# Level 85 with minimum 100 points
constraint = PointBudgetConstraint.from_level(85, min_offset=-15)
# This gives: max_points=106, min_points=91

# Custom range
constraint = PointBudgetConstraint(min_points=100, max_points=116)
```

### Attribute Constraint

```python
AttributeConstraint(
    min_str: int = 0,
    min_dex: int = 0,
    min_int: int = 0
)
```

**From Gems:**
```python
constraint = AttributeConstraint.from_gems(
    gem_requirements: List[Dict[str, int]]
)
```

**Examples:**
```python
# From gem requirements
gems = [
    {'str': 155, 'dex': 0, 'int': 0},    # Molten Strike
    {'str': 98, 'dex': 68, 'int': 0},    # Ancestral Call
    {'str': 0, 'dex': 0, 'int': 111},    # Elemental Focus
]
constraint = AttributeConstraint.from_gems(gems)
# Result: min_str=155, min_dex=68, min_int=111

# Manual
constraint = AttributeConstraint(min_str=150, min_dex=100, min_int=0)
```

### Jewel Socket Constraint

```python
JewelSocketConstraint(
    min_sockets: Optional[int] = None,
    max_sockets: Optional[int] = None
)
```

**Examples:**
```python
# At least 2 jewel sockets
constraint = JewelSocketConstraint(min_sockets=2)

# Exactly 3 jewel sockets
constraint = JewelSocketConstraint(min_sockets=3, max_sockets=3)

# At most 5 jewel sockets
constraint = JewelSocketConstraint(max_sockets=5)
```

### Constraint Set

```python
ConstraintSet(
    point_budget: Optional[PointBudgetConstraint] = None,
    attributes: Optional[AttributeConstraint] = None,
    jewel_sockets: Optional[JewelSocketConstraint] = None
)
```

**Example:**
```python
constraints = ConstraintSet(
    point_budget=PointBudgetConstraint.from_level(95),
    attributes=AttributeConstraint.from_gems(gem_requirements),
    jewel_sockets=JewelSocketConstraint(min_sockets=2)
)

# Validate
if constraints.validate(build_xml):
    print("✓ All constraints satisfied")
else:
    for violation in constraints.get_violations(build_xml):
        print(f"✗ {violation}")
```

---

## Visualization Configuration

### Pareto Frontier Plot

```python
plot_pareto_frontier_3d(
    frontier: ParetoFrontier,
    output_file: str = "pareto_frontier_3d.html",
    title: str = "Pareto Frontier: DPS vs Life vs EHP",
    interactive: bool = True
)
```

**`output_file`**: Where to save the plot (`.html` for interactive, `.png` for static)
**`title`**: Plot title
**`interactive`**: Use Plotly (True) or matplotlib (False)

**Examples:**
```python
# Interactive 3D plot (recommended)
plot_pareto_frontier_3d(
    frontier,
    output_file="my_frontier.html",
    title="My Ranger: DPS vs Life vs EHP",
    interactive=True
)

# Static 3D plot (for reports)
plot_pareto_frontier_3d(
    frontier,
    output_file="frontier.png",
    interactive=False
)
```

### 2D Projection Plot

```python
plot_pareto_frontier_2d(
    frontier: ParetoFrontier,
    x_axis: str = 'dps',
    y_axis: str = 'life',
    output_file: str = "pareto_frontier_2d.png",
    title: str = "Pareto Frontier: DPS vs Life"
)
```

**`x_axis`/`y_axis`**: Objectives to plot (`'dps'`, `'life'`, `'ehp'`)

### Evolution Progress Plot

```python
plot_evolution_progress(
    best_fitness_history: List[float],
    avg_fitness_history: List[float],
    output_file: str = "evolution_progress.png",
    title: str = "Genetic Algorithm Evolution Progress",
    objective: str = "fitness"
)
```

**`objective`**: Name for y-axis label

### Convergence Analysis

```python
plot_convergence_analysis(
    best_fitness_history: List[float],
    window_size: int = 5,
    output_file: str = "convergence.png"
)
```

**`window_size`**: Smoothing window for improvement rate calculation

### Tree Diff Viewer

```python
visualize_tree_diff(
    original_xml: str,
    optimized_xml: str,
    output_file: str = "tree_diff.txt",
    tree_parser: Optional[PassiveTreeGraph] = None
)
```

**`tree_parser`**: Pre-loaded tree graph (optional, for performance)

---

## Performance Tuning

### Speed vs Quality Trade-offs

| Configuration | Runtime | Quality | Use Case |
|---------------|---------|---------|----------|
| Greedy (10 iter) | 30s | Low | Quick test |
| Greedy (50 iter) | 2-3 min | Good | Normal use |
| Greedy (150 iter) | 6-8 min | High | Maximum greedy |
| Genetic (15 pop, 30 gen) | 5 min | Good | Fast genetic |
| Genetic (30 pop, 50 gen) | 10-15 min | High | Normal genetic |
| Genetic (50 pop, 100 gen) | 40-50 min | Very High | Research |

### Memory Usage

**Greedy:** ~100-200 MB
**Genetic:** ~500 MB to 2 GB (depends on population size)

**Tips:**
- Reduce `population_size` if memory constrained
- Process builds sequentially, not in parallel
- Close other applications during genetic optimization

### CPU Usage

**Greedy:** Single-threaded, uses 1 core
**Genetic:** Population evaluation could be parallelized (not currently implemented)

**Future optimization potential:**
- Parallel fitness evaluation
- Caching of tree graph
- JIT compilation of relative calculator

---

## Recommended Presets

### Quick Test
```python
optimizer = GreedyTreeOptimizer(
    max_iterations=10,
    optimize_masteries=False
)
# Runtime: ~30 seconds
# Quality: Basic improvements only
```

### Standard Greedy
```python
optimizer = GreedyTreeOptimizer(
    max_iterations=50,
    optimize_masteries=True
)
# Runtime: 2-3 minutes
# Quality: Good for most builds
```

### Maximum Greedy
```python
optimizer = GreedyTreeOptimizer(
    max_iterations=150,
    optimize_masteries=True
)
# Runtime: 6-8 minutes
# Quality: Thorough local optimization
```

### Quick Genetic
```python
optimizer = GeneticTreeOptimizer(
    population_size=15,
    generations=30,
    mutation_rate=0.2,
    crossover_rate=0.8,
    elitism_count=3,
    optimize_masteries=True
)
# Runtime: 5-7 minutes
# Quality: Basic global optimization
```

### Standard Genetic
```python
optimizer = GeneticTreeOptimizer(
    population_size=30,
    generations=50,
    mutation_rate=0.2,
    crossover_rate=0.8,
    elitism_count=5,
    optimize_masteries=True
)
# Runtime: 10-15 minutes
# Quality: Good global optimization
```

### Maximum Genetic
```python
optimizer = GeneticTreeOptimizer(
    population_size=50,
    generations=100,
    mutation_rate=0.15,
    crossover_rate=0.85,
    elitism_count=7,
    optimize_masteries=True
)
# Runtime: 40-50 minutes
# Quality: Maximum optimization
```

### Research/Experimentation
```python
optimizer = GeneticTreeOptimizer(
    population_size=100,
    generations=200,
    mutation_rate=0.2,
    crossover_rate=0.8,
    elitism_count=10,
    optimize_masteries=True
)
# Runtime: 2-3 hours
# Quality: Exhaustive search
```

---

## Environment Variables

Currently no environment variables are used. Future versions may support:

```bash
# Hypothetical future configuration
export POE_OPTIMIZER_CACHE_DIR="/tmp/poe-cache"
export POE_OPTIMIZER_NUM_THREADS="4"
export POE_OPTIMIZER_LOG_LEVEL="INFO"
```

---

## Configuration Files

Currently no configuration files are supported. All configuration is done via Python API.

**Future consideration:** YAML or TOML configuration files for presets:

```yaml
# optimizer_config.yaml (hypothetical)
presets:
  quick:
    type: greedy
    max_iterations: 10
    optimize_masteries: false

  standard:
    type: greedy
    max_iterations: 50
    optimize_masteries: true

  thorough:
    type: genetic
    population_size: 30
    generations: 50
```

---

## Summary

**For most users:**
- Start with **Standard Greedy** preset (2-3 minutes)
- If results are good (>5% improvement), try **Standard Genetic** (10-15 minutes)
- Use constraints to ensure builds meet requirements
- Visualize results to understand trade-offs

**For advanced users:**
- Tune `mutation_rate` and `crossover_rate` for your use case
- Increase `population_size` and `generations` for better results
- Use **Maximum Genetic** preset for final optimization
- Experiment with custom objective functions

**For researchers:**
- Use **Research** preset with high population and generations
- Run multiple trials and analyze variance
- Consider implementing parallelization for faster evaluation
- Explore parameter sensitivity analysis


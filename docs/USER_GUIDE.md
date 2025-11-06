# Path of Exile Build Optimizer - User Guide

Welcome to the Path of Exile Build Optimizer! This guide will walk you through everything you need to know to optimize your builds.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Understanding the Algorithms](#understanding-the-algorithms)
4. [Optimization Objectives](#optimization-objectives)
5. [Advanced Features](#advanced-features)
6. [Interpreting Results](#interpreting-results)
7. [Best Practices](#best-practices)
8. [FAQ](#faq)

---

## Getting Started

### Installation

1. **Clone the repository with submodules:**
```bash
git clone --recursive https://github.com/alecrivet/poe-optimizer.git
cd poe-optimizer
```

2. **Create and activate virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install optional visualization dependencies:**
```bash
pip install matplotlib plotly numpy
```

5. **Verify installation:**
```bash
python tests/test_optimizer.py
```

### Getting Your Build Code

To optimize a build, you need its Path of Building code:

1. Open Path of Building
2. Load your build
3. Click **Import/Export Build** tab
4. Copy the build code (long string of characters)
5. Save it to a file like `examples/my_build`

---

## Basic Usage

### Quick Optimization (2-5 minutes)

The fastest way to improve your build:

```python
from src.pob.codec import decode_pob_code, encode_pob_code
from src.optimizer.tree_optimizer import GreedyTreeOptimizer

# Load your build
with open('examples/my_build', 'r') as f:
    pob_code = f.read().strip()
build_xml = decode_pob_code(pob_code)

# Create optimizer
optimizer = GreedyTreeOptimizer(
    max_iterations=50,      # Try up to 50 improvements
    optimize_masteries=True # Also optimize mastery selections
)

# Optimize for DPS
result = optimizer.optimize(build_xml, objective='dps')

# Get the optimized build code
optimized_code = encode_pob_code(result.optimized_xml)
print(f"DPS improvement: {result.optimized_stats.dps_change_percent:+.2f}%")
print(f"Optimized build code: {optimized_code}")
```

### Using Integration Examples

The easiest way to get started is to use the pre-built integration examples:

```bash
# Example 1: Quick 2-minute optimization
python examples/integration/example_1_quick_optimization.py

# Example 2: Genetic algorithm (10-20 minutes)
python examples/integration/example_2_genetic_algorithm.py

# Example 3: Explore trade-offs between objectives
python examples/integration/example_3_multi_objective.py

# Example 4: Advanced features (7 objectives + constraints)
python examples/integration/example_4_advanced_features.py

# Example 5: Complete pipeline comparison
python examples/integration/example_5_complete_workflow.py
```

Each example includes clear instructions and comments. Start with Example 1 for the quickest results.

---

## Understanding the Algorithms

### Greedy Algorithm (Fast)

**When to use:** Quick improvements, testing builds, iterative refinement

**How it works:**
1. Tries adding/removing each node in the tree
2. Keeps the change if it improves the objective
3. Repeats until no improvements found
4. Optimizes mastery selections at the end

**Pros:**
- Fast (2-5 minutes)
- Consistent results
- Good for incremental improvements

**Cons:**
- May get stuck in local optima
- Won't find unconventional solutions

**Configuration:**
```python
optimizer = GreedyTreeOptimizer(
    max_iterations=50,       # More = thorough but slower
    optimize_masteries=True, # Recommended
    verbose=True            # Show progress
)
```

### Genetic Algorithm (Thorough)

**When to use:** Maximum optimization, exploring alternatives, final polish

**How it works:**
1. Creates population of 30 random tree variations
2. Evaluates fitness of each variation
3. Selects best variations to "reproduce"
4. Combines parent trees (crossover) and mutates offspring
5. Repeats for 50 generations
6. Returns best solution found

**Pros:**
- Explores solution space broadly
- Escapes local optima
- Can discover unexpected solutions
- Better final results

**Cons:**
- Slower (10-20 minutes)
- Results may vary between runs
- Requires more computational resources

**Configuration:**
```python
optimizer = GeneticTreeOptimizer(
    population_size=30,      # More = better exploration
    generations=50,          # More = better optimization
    mutation_rate=0.2,       # 20% chance of random changes
    crossover_rate=0.8,      # 80% chance of combining parents
    elitism_count=5,         # Preserve 5 best solutions
    tournament_size=3,       # Selection pressure
    max_points_change=10,    # Max ±10 points from original
    optimize_masteries=True
)
```

### Multi-Objective Optimization

**When to use:** Exploring trade-offs, balancing multiple goals

**How it works:**
1. Runs optimization for multiple objectives simultaneously
2. Finds Pareto frontier (best trade-off points)
3. Returns solutions representing different balances

**Example: Pareto Frontier**

```
       DPS ↑
       10% |    ⚫ Max DPS (10% DPS, 2% Life)
        8% |      ⚫ Balanced (7% DPS, 5% Life)
        6% |
        4% |            ⚫ Max Life (3% DPS, 9% Life)
        2% |
           └─────────────────────→ Life
```

**Usage:**
```python
from src.optimizer.multi_objective_optimizer import (
    create_multi_objective_score,
    calculate_pareto_frontier
)

# Run optimization for different objectives
dps_result = optimizer.optimize(build_xml, objective='dps')
life_result = optimizer.optimize(build_xml, objective='life')
balanced_result = optimizer.optimize(build_xml, objective='balanced')

# Compare and pick based on your needs
```

---

## Optimization Objectives

### Core Objectives

#### DPS (Damage Per Second)
- **Best for:** Bossing builds, speed farming
- **Maximizes:** Raw damage output
- **May sacrifice:** Survivability, sustain

```python
result = optimizer.optimize(build_xml, objective='dps')
```

#### Life
- **Best for:** Hardcore, league start, tanky builds
- **Maximizes:** Maximum life pool
- **May sacrifice:** Damage, clear speed

```python
result = optimizer.optimize(build_xml, objective='life')
```

#### EHP (Effective Hit Points)
- **Best for:** Balanced defense
- **Maximizes:** Life × resistances × other defenses
- **Considers:** Armour, evasion, ES contribution to life

```python
result = optimizer.optimize(build_xml, objective='ehp')
```

#### Balanced
- **Best for:** General mapping, league start
- **Maximizes:** Weighted combination of DPS, Life, EHP
- **Default weights:** 50% DPS, 30% Life, 20% EHP

```python
result = optimizer.optimize(build_xml, objective='balanced')
```

### Extended Objectives

Available with `extended_objectives.py`:

#### Mana Efficiency
- Maximizes unreserved mana
- Considers mana regeneration
- **Use case:** MOM builds, hybrid builds

#### Energy Shield
- Maximizes total energy shield
- Considers ES recharge rate
- **Use case:** CI builds, hybrid builds

#### Block Chance
- Maximizes attack and spell block
- Averages both values
- **Use case:** Block-based builds, gladiator

#### Clear Speed
- Composite metric of movement speed, attack/cast speed, and AoE
- **Formula:** `(movement × 0.4) + (attack_speed × 0.4) + (aoe × 0.2)`
- **Use case:** Mapping builds, speed farming

**Example usage:**
```python
from src.optimizer.extended_objectives import evaluate_extended_objectives

# Get 7-objective evaluation
extended_score = evaluate_extended_objectives(
    original_xml=original,
    modified_xml=optimized,
    base_evaluation=base_eval
)

print(f"Mana: {extended_score.mana_percent:+.2f}%")
print(f"ES: {extended_score.es_percent:+.2f}%")
print(f"Block: {extended_score.block_percent:+.2f}%")
print(f"Clear Speed: {extended_score.clear_speed_percent:+.2f}%")
```

---

## Advanced Features

### Constraints

Ensure builds meet specific requirements:

#### Point Budget Constraint

```python
from src.optimizer.constraints import PointBudgetConstraint

# For a level 95 character (max 116 points)
constraint = PointBudgetConstraint.from_level(95)

# Or specify manually
constraint = PointBudgetConstraint(
    min_points=100,  # At least 100 points
    max_points=116   # At most 116 points
)

# Validate
if constraint.validate(build_xml):
    print("Build meets point budget!")
else:
    print(constraint.get_violation_message(build_xml))
```

#### Attribute Constraint

Ensure build has enough STR/DEX/INT for gems:

```python
from src.optimizer.constraints import AttributeConstraint

# From gem requirements
gems = [
    {'str': 155, 'dex': 0, 'int': 0},    # Molten Strike
    {'str': 98, 'dex': 68, 'int': 0},    # Ancestral Call
]
constraint = AttributeConstraint.from_gems(gems)

# Or manual
constraint = AttributeConstraint(
    min_str=155,
    min_dex=68,
    min_int=0
)

if constraint.validate(build_xml):
    print("Build meets attribute requirements!")
```

#### Jewel Socket Constraint

Ensure minimum jewel sockets:

```python
from src.optimizer.constraints import JewelSocketConstraint

constraint = JewelSocketConstraint(
    min_sockets=2,  # At least 2 jewel sockets
    max_sockets=None
)

if constraint.validate(build_xml):
    print(f"Build has enough jewel sockets!")
```

#### Combined Constraints

```python
from src.optimizer.constraints import ConstraintSet

constraints = ConstraintSet(
    point_budget=PointBudgetConstraint.from_level(95),
    attributes=AttributeConstraint.from_gems(gem_requirements),
    jewel_sockets=JewelSocketConstraint(min_sockets=2)
)

# Validate all at once
if constraints.validate(build_xml):
    print("Build satisfies all constraints!")
else:
    violations = constraints.get_violations(build_xml)
    print("Violations:")
    for v in violations:
        print(f"  - {v}")
```

### Visualization

#### Pareto Frontier Plot

```python
from src.visualization.frontier_plot import plot_pareto_frontier_3d

# After multi-objective optimization
plot_pareto_frontier_3d(
    frontier=pareto_frontier,
    output_file="my_frontier.html",
    title="My Build: DPS vs Life vs EHP",
    interactive=True  # Creates interactive 3D plot
)
```

Opens interactive plot in browser with:
- 3D scatter plot of solutions
- Highlighted extreme points (max DPS, max Life, max EHP)
- Highlighted balanced solution
- Hover for details

#### Evolution Progress

```python
from src.visualization.evolution_plot import plot_evolution_progress

# After genetic algorithm
plot_evolution_progress(
    best_fitness_history=result.best_fitness_history,
    avg_fitness_history=result.avg_fitness_history,
    output_file="evolution.png",
    title="Optimization Progress"
)
```

Shows:
- Best fitness per generation (green line)
- Average fitness per generation (blue line)
- Population spread (shaded area)
- Final improvement annotation

#### Tree Difference Viewer

```python
from src.visualization.tree_diff import visualize_tree_diff

visualize_tree_diff(
    original_xml=original,
    optimized_xml=optimized,
    output_file="tree_diff.txt"
)
```

Displays:
```
=== NODES ADDED ===
✓ [12345] Deadly Draw
  +20% Physical Damage with Bows
  +15% Attack Speed with Bows

✓ [67890] Hunter's Gambit
  +25% Critical Strike Chance with Bows

=== NODES REMOVED ===
✗ [11111] Iron Grip
  +10% Physical Damage
  (Low impact for bow build)

=== MASTERY CHANGES ===
[Notable 12345] Master Fletcher
  Old: +1 Projectile (300% value)
  New: +50% Damage to Bleeding Enemies (450% value)
  Change: +150% ✓

=== SUMMARY ===
Nodes added: 2 (+8 points)
Nodes removed: 1 (-3 points)
Net change: +5 points
```

---

## Interpreting Results

### Understanding the Output

When optimization completes, you'll see:

```python
print(f"DPS: {result.optimized_stats.dps_change_percent:+.2f}%")
print(f"Life: {result.optimized_stats.life_change_percent:+.2f}%")
print(f"EHP: {result.optimized_stats.ehp_change_percent:+.2f}%")
```

**Example output:**
```
DPS: +7.32%
Life: +2.14%
EHP: +3.56%
```

### What's a Good Improvement?

| Improvement | Rating | Notes |
|-------------|--------|-------|
| +1-3% | Small | Still worth it for passive tree tweaks |
| +3-5% | Good | Typical for well-optimized builds |
| +5-10% | Great | Significant gains, worth the time |
| +10%+ | Excellent | Rare, usually means original build had issues |

### Relative vs Absolute Stats

The optimizer uses **relative calculations** with ~5-10% accuracy. This is fine for:
- ✅ Comparing solutions (which is better?)
- ✅ Ranking nodes (which has most impact?)
- ✅ Finding improvements

For exact stats, import the optimized build into Path of Building and check the Stats tab.

### When Results Seem Wrong

If you get unexpected results:

1. **Verify the build imports correctly:**
   ```python
   from src.pob.xml_parser import parse_pob_xml
   stats = parse_pob_xml(build_xml)
   print(f"Original DPS: {stats.get('TotalDPS', 0)}")
   ```

2. **Check relative calculator accuracy:**
   ```python
   python tests/test_relative_calculator.py
   ```

3. **Inspect tree changes:**
   ```python
   from src.visualization.tree_diff import visualize_tree_diff
   visualize_tree_diff(original_xml, optimized_xml, "diff.txt")
   ```

4. **Verify in Path of Building:**
   - Import optimized build
   - Check calculations match expectations
   - Path of Building is ground truth!

---

## Best Practices

### Starting a New Build

1. **Import your current PoB build**
2. **Run quick greedy optimization first** (2 mins)
   - See if there are obvious improvements
   - Get baseline results
3. **If gains are significant (>5%), run genetic algorithm** (20 mins)
   - Get maximum optimization
4. **Import result back to PoB and verify**
   - Double-check stats match expectations
   - Ensure build still works as intended

### Optimizing for Different Content

**Bossing (Pure DPS):**
```python
result = optimizer.optimize(build_xml, objective='dps')
```

**Mapping (Balanced):**
```python
result = optimizer.optimize(build_xml, objective='balanced')
# Or explore trade-offs with multi-objective
```

**Hardcore/League Start:**
```python
# Prioritize life
result = optimizer.optimize(build_xml, objective='life')

# Or use constraints
constraints = ConstraintSet(
    point_budget=PointBudgetConstraint.from_level(85),  # Lower level
    jewel_sockets=JewelSocketConstraint(min_sockets=2)
)
```

**Speed Farming:**
```python
from src.optimizer.extended_objectives import evaluate_extended_objectives

# Optimize for clear speed
# (Requires custom objective function - see example_4)
```

### Iterative Refinement

For best results, optimize in stages:

```python
# Stage 1: Greedy optimization
greedy_opt = GreedyTreeOptimizer(max_iterations=50)
greedy_result = greedy_opt.optimize(build_xml, 'dps')

# Stage 2: If greedy found >3% improvement, try genetic
if greedy_result.optimized_stats.dps_change_percent > 3.0:
    genetic_opt = GeneticTreeOptimizer(generations=50)
    final_result = genetic_opt.optimize(greedy_result.optimized_xml, 'dps')
else:
    final_result = greedy_result

# Stage 3: Fine-tune masteries if needed
# (Automatic with optimize_masteries=True)
```

### Performance Tips

**For faster optimization:**
- Reduce `max_iterations` (greedy) or `generations` (genetic)
- Use greedy instead of genetic for testing
- Optimize on representative builds, not every variant

**For better results:**
- Increase `generations` to 100 (genetic)
- Increase `population_size` to 50 (genetic)
- Run optimization multiple times and pick best

---

## FAQ

### Can I optimize items and gems?

Not yet. Current version only optimizes passive tree and masteries. Item and gem optimization is planned for future releases.

### Does it work with Timeless Jewels?

No. Timeless Jewels require complex calculations that aren't currently supported. The optimizer will preserve your Timeless Jewel allocation but won't optimize around it.

### Can I use this for SSF builds?

Yes! Use constraints to ensure the build meets requirements:
```python
constraints = ConstraintSet(
    point_budget=PointBudgetConstraint.from_level(90),
    attributes=AttributeConstraint.from_gems(gems),
    jewel_sockets=JewelSocketConstraint(min_sockets=1)
)
```

### How accurate are the improvements?

The relative calculator has ~5-10% accuracy for ranking nodes. The actual improvements in Path of Building may vary by this amount. Always verify results in PoB.

### Can I weight objectives differently?

Yes, for balanced optimization:
```python
# In tree_optimizer.py, modify the balanced objective:
# Default: 0.5 * dps + 0.3 * life + 0.2 * ehp
# You can customize weights in the code
```

For full control, use multi-objective optimization and pick your preferred solution from the Pareto frontier.

### My build got worse. What happened?

Possible causes:
1. **Relative calculator inaccuracy** - Verify in PoB
2. **Objective mismatch** - Optimizing for DPS may reduce Life
3. **Build-specific mechanics** - Some builds have complex interactions
4. **Bug** - Please report with build code!

### How do I report a bug?

1. Save your input build code: `examples/bug_report_input`
2. Save your output build code: `examples/bug_report_output`
3. Note the command/code you ran
4. Open issue at: https://github.com/alecrivet/poe-optimizer/issues

### Can I contribute?

Yes! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## Next Steps

- **Try the examples:** `examples/integration/`
- **Read technical docs:** `notes/sessions/`
- **Check the API:** Read module docstrings
- **Join discussion:** GitHub Issues

Happy optimizing! 🎮⚡

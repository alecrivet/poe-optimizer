# Multi-Objective Optimization Explained

## 🎯 The Problem: Multiple Conflicting Goals

In Path of Exile, you often want to optimize multiple things at once:
- **DPS** (Damage) - Kill monsters faster
- **Life** - Survive longer
- **Defense (EHP)** - Take less damage

**The Challenge:** These objectives often conflict!
- Adding damage nodes → lose defensive nodes
- Adding life nodes → lose damage nodes
- You can't maximize everything at once

## ❓ Traditional Approach: Single Objective

With single-objective optimization, you pick ONE goal:

```python
# Option 1: Maximize DPS only
optimizer.optimize(objective='dps')
Result: +10% DPS, +1% Life, +0% EHP

# Option 2: Maximize Life only
optimizer.optimize(objective='life')
Result: +2% DPS, +8% Life, +3% EHP

# Option 3: Balance (average of all three)
optimizer.optimize(objective='balanced')
Result: +5% DPS, +4% Life, +4% EHP
```

**Problem:** You have to decide the trade-off BEFORE optimization!
- What if you want to see all possible trade-offs first?
- What if you don't know which balance you prefer?

## 🌟 Multi-Objective Solution: Pareto Frontier

Instead of picking ONE objective, multi-objective optimization finds ALL good trade-offs!

### Example Population

```
Solution A: +10% DPS, +2% Life, +3% EHP  ← High damage, low survivability
Solution B: +7% DPS, +5% Life, +6% EHP   ← Balanced
Solution C: +3% DPS, +9% Life, +8% EHP   ← Low damage, high survivability
Solution D: +5% DPS, +3% Life, +4% EHP   ← Mediocre in all
```

**Question:** Which solutions are "best"?

## 🔍 Pareto Dominance

**Definition:** Solution A **dominates** Solution B if:
1. A is **better or equal** in ALL objectives
2. A is **strictly better** in AT LEAST ONE objective

### Example 1: Clear Dominance

```
Solution B: +7% DPS, +5% Life, +6% EHP
Solution D: +5% DPS, +3% Life, +4% EHP

Comparison:
- DPS: 7% > 5% ✓ (B better)
- Life: 5% > 3% ✓ (B better)
- EHP: 6% > 4% ✓ (B better)

Result: B dominates D (better in all objectives)
```

### Example 2: Non-Dominance (Trade-off)

```
Solution A: +10% DPS, +2% Life, +3% EHP
Solution C: +3% DPS, +9% Life, +8% EHP

Comparison:
- DPS: 10% > 3% ✓ (A better)
- Life: 2% < 9% ✗ (C better)
- EHP: 3% < 8% ✗ (C better)

Result: Neither dominates (A has better DPS, C has better Life/EHP)
```

## 🏆 Pareto Frontier

The **Pareto Frontier** is the set of all non-dominated solutions.

From our example:
```
Population:
  Solution A: +10% DPS, +2% Life, +3% EHP  ← Non-dominated ✓
  Solution B: +7% DPS, +5% Life, +6% EHP   ← Non-dominated ✓
  Solution C: +3% DPS, +9% Life, +8% EHP   ← Non-dominated ✓
  Solution D: +5% DPS, +3% Life, +4% EHP   ← Dominated by B ✗

Pareto Frontier: {A, B, C}
```

**Interpretation:**
- A, B, C are all equally "good" (none dominates others)
- D is "bad" (dominated by B)
- The frontier represents all possible trade-offs

## 📊 Visualizing the Trade-off

```
         DPS
          ↑
       10 | A ●
          |
        7 |     ● B
          |
        5 |         ● D (dominated!)
          |
        3 |             ● C
          |
        0 +---------------→ Life
          0   2   4   6   9

Pareto Frontier: A → B → C (the curve)
Dominated: D (inside the curve)
```

**The frontier forms a curve showing the trade-off:**
- Move from A to B: Lose 3% DPS, gain 3% Life
- Move from B to C: Lose 4% DPS, gain 4% Life
- You can't improve DPS without losing Life, or vice versa

## 🎓 Real Example: Character Build

### Scenario
You have a level 100 character with 124 passive points allocated.
You want to optimize your passive tree.

### Single-Objective Results

```bash
# DPS-focused optimization
optimizer.optimize(objective='dps')
Result: +8.2% DPS, +1.1% Life, +0.8% EHP
```

Good for DPS, but very fragile!

```bash
# Life-focused optimization
optimizer.optimize(objective='life')
Result: +1.8% DPS, +6.5% Life, +4.2% EHP
```

Tanky, but low damage!

### Multi-Objective Results

```bash
# Find all trade-offs
frontier = optimizer.optimize_multi_objective()
```

**Pareto Frontier (5 solutions):**

```
Solution 1 (Max DPS):      +8.2% DPS, +1.1% Life, +0.8% EHP
Solution 2 (DPS-focused):  +7.5% DPS, +2.8% Life, +2.1% EHP
Solution 3 (Balanced):     +5.3% DPS, +4.5% Life, +4.8% EHP
Solution 4 (Tank-focused): +3.1% DPS, +5.9% Life, +6.2% EHP
Solution 5 (Max Life):     +1.8% DPS, +6.5% Life, +4.2% EHP
```

**Now you can pick based on preference!**
- Farming easy content? Pick Solution 1 (max DPS)
- Doing hard bosses? Pick Solution 4 or 5 (tanky)
- General mapping? Pick Solution 3 (balanced)

## 🧬 NSGA-II Algorithm

**NSGA-II** = Non-dominated Sorting Genetic Algorithm II

It's a genetic algorithm specifically designed for multi-objective optimization.

### Key Differences from Regular GA

**Regular Genetic Algorithm:**
```
1. Evaluate fitness (single number)
2. Select parents (highest fitness)
3. Create offspring
4. Keep best individuals (highest fitness)
```

**NSGA-II:**
```
1. Evaluate ALL objectives (DPS, Life, EHP)
2. Rank by Pareto dominance
3. Select parents (prefer non-dominated + diversity)
4. Create offspring
5. Keep best by rank AND diversity
```

### The NSGA-II Process

**Step 1: Non-dominated Sorting**

Assign each individual a rank:
```
Rank 0 (Frontier): Non-dominated solutions
  Individual A: +10% DPS, +2% Life, +3% EHP
  Individual B: +7% DPS, +5% Life, +6% EHP
  Individual C: +3% DPS, +9% Life, +8% EHP

Rank 1: Dominated only by Rank 0
  Individual D: +5% DPS, +3% Life, +4% EHP

Rank 2: Dominated by Rank 0 and 1
  Individual E: +4% DPS, +2% Life, +3% EHP
```

Lower rank = better!

**Step 2: Crowding Distance**

Within the same rank, prefer diverse solutions:

```
         DPS
          ↑
       10 | A ●←─────── large distance (isolated)
          |
        7 |     ● B ←── medium distance
          |
        3 |             ● C ←─ large distance (isolated)
          |
        0 +---------------→ Life
          0   2   6   9

Crowding distance = sum of distances to neighbors in each objective
```

**Why diversity?** Maintain different trade-offs on the frontier!

**Step 3: Selection**

Prefer individuals with:
1. Lower rank (better dominance)
2. Higher crowding distance (more diverse)

```python
def compare(ind1, ind2):
    if ind1.rank < ind2.rank:
        return ind1  # Better rank
    elif ind1.rank > ind2.rank:
        return ind2
    else:
        # Same rank, prefer more diverse
        if ind1.crowding_distance > ind2.crowding_distance:
            return ind1
        else:
            return ind2
```

**Step 4: Evolution**

Same as regular GA:
- Crossover parents to create offspring
- Mutate offspring
- Evaluate new generation
- Repeat!

### Full NSGA-II Cycle

```
Generation 1:
  Population: 30 random variations
  ↓
  Evaluate all objectives (DPS, Life, EHP)
  ↓
  Non-dominated sorting → Assign ranks
  ↓
  Calculate crowding distances
  ↓
  Select parents (tournament on rank + diversity)
  ↓
  Crossover + Mutation
  ↓
Generation 2:
  Population: 30 new individuals
  ↓
  [Repeat for 50 generations]
  ↓
Final Result:
  Pareto Frontier with ~10 diverse solutions
```

## 🎮 How to Use

### Basic Usage

```python
from src.optimizer.genetic_optimizer import GeneticTreeOptimizer

# Create optimizer
optimizer = GeneticTreeOptimizer(
    population_size=30,
    generations=50,
)

# Multi-objective optimization (returns frontier)
frontier = optimizer.optimize_multi_objective(build_xml)

# View all solutions
print(frontier)
# Output:
# Pareto Frontier: 8 Solutions
#
# Extreme Points:
#   Max DPS:  +8.2% DPS, +1.1% Life, +0.8% EHP
#   Max Life: +1.8% DPS, +6.5% Life, +4.2% EHP
#   Balanced: +5.3% DPS, +4.5% Life, +4.8% EHP
```

### Choosing a Solution

```python
# Get extreme points
extremes = frontier.get_extreme_points()

# Max DPS build
max_dps_build = extremes['max_dps'].xml

# Max Life build
max_life_build = extremes['max_life'].xml

# Balanced build
balanced_build = frontier.get_balanced_solution().xml

# Custom preference (e.g., 60% DPS, 40% Life)
# Pick solution closest to your preference from frontier
```

## 📈 Performance Comparison

### Single-Objective Optimization

```
Time: 10-15 minutes
Result: 1 optimal solution for chosen objective
Advantage: Fast, simple
Disadvantage: Might miss better trade-offs
```

### Multi-Objective Optimization

```
Time: 15-25 minutes
Result: 8-12 optimal solutions (entire frontier)
Advantage: See all trade-offs, choose later
Disadvantage: Slower, more complex
```

### When to Use Each

**Use Single-Objective when:**
- You know exactly what you want (pure DPS, pure tank, etc.)
- You want quick results
- You're fine-tuning an already good build

**Use Multi-Objective when:**
- You're unsure about the right balance
- You want to explore different playstyles
- You're optimizing a new build from scratch
- You want to see what's possible

## 🔬 Mathematical Foundation

### Pareto Dominance (Formal Definition)

Solution **x** dominates solution **y** (denoted x ≻ y) if:

```
∀i: f_i(x) ≥ f_i(y)  (x is at least as good in all objectives)
∃j: f_j(x) > f_j(y)  (x is strictly better in at least one objective)
```

Where:
- f_i(x) = objective i value for solution x
- f_1 = DPS, f_2 = Life, f_3 = EHP

### Pareto Optimal Set

The set of all non-dominated solutions:

```
P* = {x ∈ X | ¬∃y ∈ X : y ≻ x}
```

In plain English: "All solutions where no other solution dominates them"

### Crowding Distance (Formal)

For solution i in objective m:

```
distance_i += (f_m(i+1) - f_m(i-1)) / (f_m^max - f_m^min)
```

Sum over all objectives m ∈ {DPS, Life, EHP}

Boundary solutions: distance = ∞

## 🎯 Key Takeaways

1. **Multi-objective optimization finds ALL good trade-offs**
   - Not just one solution, but entire frontier
   - Pick your preferred balance after seeing options

2. **Pareto dominance determines quality**
   - Solution dominates if better in all objectives
   - Frontier = all non-dominated solutions
   - No solution on frontier is "better" than others (different trade-offs)

3. **NSGA-II maintains diverse frontier**
   - Ranks by dominance
   - Preserves diversity via crowding distance
   - Evolves entire frontier over generations

4. **Use when you want to explore trade-offs**
   - See what's possible before committing
   - Switch between builds for different content
   - Understand the cost of improving one objective

5. **Trade-off visualization is key**
   - Frontier shows achievable combinations
   - Moving along frontier = trading one objective for another
   - Dominated solutions are strictly worse

---

**Implementation:** `src/optimizer/multi_objective_optimizer.py`
**Integration:** `src/optimizer/genetic_optimizer.py` (NSGA-II mode)
**Tests:** `test_multi_objective.py`

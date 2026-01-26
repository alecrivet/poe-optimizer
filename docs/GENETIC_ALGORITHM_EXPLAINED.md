# Genetic Algorithm for Passive Tree Optimization

## 🧬 What is a Genetic Algorithm?

A genetic algorithm is inspired by natural evolution. Instead of making small local improvements (like the greedy algorithm), it maintains a **population** of different solutions and evolves them over generations.

### Natural Evolution Analogy

```
Biology                    → Our Algorithm
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Organism (animal)          → Individual (passive tree)
Population (species)       → Population (30 trees)
DNA/Genes                  → Allocated nodes + masteries
Fitness (survival)         → DPS/Life/EHP improvement
Reproduction               → Crossover (combine parents)
Random mutations           → Add/remove nodes, change masteries
Natural selection          → Keep best individuals
Generations                → Evolution cycles
```

## 🔄 The Evolution Cycle

```
Generation 1:
  Population: [Tree A, Tree B, Tree C, ..., Tree Z]  (30 individuals)
                     ↓
              Evaluate Fitness
              (Which trees are best?)
                     ↓
              Select Parents
              (Tournament: pick 2 best from random 3)
                     ↓
              Crossover
              (Combine parent trees to create offspring)
                     ↓
              Mutation
              (Random changes: add/remove nodes)
                     ↓
Generation 2:
  Population: [Tree A', Tree B', Tree C', ..., Tree Z']  (new generation)

Repeat for 50 generations...
```

## 🧩 Key Components

### 1. Individual (Passive Tree)

Each individual represents one possible passive tree configuration:

```python
Individual:
  xml: <PathOfBuilding build with allocated nodes>
  fitness: 5.2%  # DPS improvement over original
  allocated_nodes: [12345, 23456, 34567, ...]
  mastery_effects: {44298: 5, 55123: 7}
```

### 2. Population (Collection of Trees)

The population holds 30 different tree configurations:

```python
Population (Generation 1):
  Individual 1: 124 nodes, fitness = 5.2% DPS
  Individual 2: 127 nodes, fitness = 4.8% DPS
  Individual 3: 121 nodes, fitness = 6.1% DPS  ← Best!
  ...
  Individual 30: 125 nodes, fitness = 2.1% DPS
```

### 3. Fitness Evaluation

How good is each tree? We compare against the original build:

```python
Original Build: 1,000,000 DPS, 5,000 Life
Modified Build: 1,050,000 DPS, 5,100 Life

Fitness (DPS): +5.0%  ← Higher is better!
```

### 4. Selection (Choosing Parents)

**Tournament Selection:**
- Randomly pick 3 individuals
- Choose the best one as parent
- Repeat to get 2 parents

```
Random Sample: [Individual 5, Individual 12, Individual 23]
Fitness:       [3.2%,        5.1%,           2.8%]
Winner:        Individual 12 (5.1%) → Parent 1

Random Sample: [Individual 7, Individual 19, Individual 3]
Fitness:       [4.5%,        2.9%,           6.1%]
Winner:        Individual 3 (6.1%) → Parent 2
```

### 5. Crossover (Combining Parents)

Take parts from both parents to create offspring:

```
Parent 1 Nodes: [A, B, C, D, E, F]
Parent 2 Nodes: [A, B, C, G, H, I]

Step 1 - Intersection (always include):
  Common Nodes: [A, B, C]

Step 2 - Unique nodes (50% chance each):
  From Parent 1: [D, E, F] → Include D and F (50% chance)
  From Parent 2: [G, H, I] → Include G and H (50% chance)

Offspring Nodes: [A, B, C, D, F, G, H]
                 └─common─┘ └─P1─┘ └─P2┘
```

**Masteries:** Take from fitter parent

```
Parent 1 Masteries: {M1: effect_5, M2: effect_3}  (fitness 5.2%)
Parent 2 Masteries: {M1: effect_7, M2: effect_3}  (fitness 4.1%)

Offspring Masteries: {M1: effect_5, M2: effect_3}  ← From Parent 1 (fitter)
```

### 6. Mutation (Random Changes)

20% chance to randomly modify the offspring:

```
Original Offspring: [A, B, C, D, E]

Mutation Types (random pick):
  1. Add node:    [A, B, C, D, E, F]  ← Added random adjacent node F
  2. Remove node: [A, B, C, E]        ← Removed node D
  3. Change mastery: {M1: 5 → 7}      ← Changed mastery effect
```

### 7. Elitism (Preserve Best)

Keep the 5 best individuals from each generation:

```
Generation 1 Best 5:
  Individual 3:  6.1% DPS  ← Guaranteed to survive!
  Individual 8:  5.8% DPS  ← Guaranteed to survive!
  Individual 12: 5.1% DPS  ← Guaranteed to survive!
  Individual 1:  5.2% DPS  ← Guaranteed to survive!
  Individual 21: 4.9% DPS  ← Guaranteed to survive!

Generation 2:
  These 5 are automatically included
  + 25 new offspring (crossover + mutation)
```

## 📊 Complete Example

### Initial Population (Generation 0)

```
Individual 1 (Original):  0.0% (baseline)
Individual 2:             +2.3% (random variation)
Individual 3:             -1.2% (bad variation)
Individual 4:             +3.1% (good variation)
...
Individual 30:            +1.8%
```

### Generation 1 Evolution

**Selection:**
```
Tournament 1: [Ind 2, Ind 5, Ind 12] → Winner: Ind 2 (3.2%)
Tournament 2: [Ind 4, Ind 9, Ind 23] → Winner: Ind 4 (3.1%)
Parents: Ind 2 + Ind 4
```

**Crossover:**
```
Parent 2 nodes: [common] + [unique from P2]
Parent 4 nodes: [common] + [unique from P4]
Offspring nodes: [common] + [some from P2] + [some from P4]
```

**Mutation (20% chance):**
```
Random mutation triggered!
Action: Add node
Offspring: Added node 45678 (Elemental Damage)
```

**Result:**
```
Offspring fitness: +3.8% ← Better than both parents!
```

### After 50 Generations

```
Generation 1 best:  3.8% DPS
Generation 10 best: 5.2% DPS
Generation 20 best: 6.7% DPS
Generation 30 best: 7.3% DPS
Generation 40 best: 7.5% DPS
Generation 50 best: 7.6% DPS  ← Final result

Improvement over generations = evolution!
```

## 🎯 Why Use Genetic Algorithm?

### Greedy Algorithm (Local Search)
```
Start → Try nearby changes → Pick best → Repeat

Pros:
✓ Fast
✓ Simple
✓ Good for refinement

Cons:
✗ Can get stuck in local optima
✗ Only explores nearby solutions
✗ Predictable
```

### Genetic Algorithm (Global Search)
```
Start → Try many different solutions → Evolve → Combine best features

Pros:
✓ Explores solution space broadly
✓ Can escape local optima
✓ Discovers novel solutions
✓ Handles multiple objectives

Cons:
✗ Slower (evaluates many trees)
✗ More complex
✗ Requires more computation
```

## 🚀 When to Use Each

**Use Greedy Algorithm when:**
- You want quick local improvements
- Build is reasonably optimized
- You have a specific objective

**Use Genetic Algorithm when:**
- Starting from scratch or poorly optimized build
- Want to explore radically different tree configurations
- Optimizing multiple objectives (DPS + Life + Defense)
- Have time for longer optimization

**Best Practice:**
1. Run greedy algorithm first (fast local optimization)
2. Then run genetic algorithm (explore alternatives)
3. Pick the best result

## 📈 Performance Comparison

```
Test Build: Shadow Assassin, 124 nodes, 1M DPS baseline

Greedy Algorithm:
  Time: 2 minutes
  Result: 1,048,000 DPS (+4.8%)
  Changes: Removed 3 suboptimal nodes, optimized masteries

Genetic Algorithm:
  Time: 15 minutes
  Result: 1,076,000 DPS (+7.6%)
  Changes: Found better path through tree, different node choices

Winner: Genetic Algorithm (but takes longer)
```

## 🔧 Configuration

```python
GeneticTreeOptimizer(
    population_size=30,      # More = better exploration, slower
    generations=50,          # More = better results, slower
    mutation_rate=0.2,       # 20% chance of random changes
    crossover_rate=0.8,      # 80% chance of combining parents
    elitism_count=5,         # Keep 5 best individuals
    tournament_size=3,       # Tournament selection pool
)
```

**Tuning Tips:**
- Increase `population_size` for more diverse exploration
- Increase `generations` if fitness still improving
- Increase `mutation_rate` if population converging too fast
- Increase `elitism_count` to preserve more good solutions

## 🎓 Key Takeaways

1. **Genetic algorithms mimic natural evolution**
   - Population of solutions evolves over time
   - Fitter individuals are more likely to reproduce
   - Random mutations add diversity

2. **Three key operators:**
   - Selection: Choose fit individuals as parents
   - Crossover: Combine parents to create offspring
   - Mutation: Random changes for diversity

3. **Elitism ensures progress:**
   - Best solutions are never lost
   - Each generation is at least as good as previous

4. **Trade-off: Time vs Quality:**
   - Genetic algorithms take longer
   - But find better solutions than greedy search
   - Especially good for complex optimization landscapes

## 🔬 Mathematical Foundation

**Fitness Function:**
```
f(tree) = objective_improvement_percent

For DPS:  f(tree) = (new_DPS - baseline_DPS) / baseline_DPS * 100
For Life: f(tree) = (new_Life - baseline_Life) / baseline_Life * 100
```

**Selection Pressure:**
```
Tournament selection with size k=3:
P(best individual selected) = k/n = 3/30 = 10%
P(worst individual selected) = very low

This ensures steady progress while maintaining diversity.
```

**Genetic Diversity:**
```
Initial diversity: High (random variations)
Without mutation: Diversity decreases → convergence
With mutation: Diversity maintained → continued exploration
```

---

**Implementation:** `src/optimizer/genetic_optimizer.py`
**Usage:** See test examples in `test_genetic_optimizer.py`

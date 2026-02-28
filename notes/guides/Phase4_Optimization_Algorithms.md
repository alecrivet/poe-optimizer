# Phase 4: Optimization Algorithms
## Week 4 - The Core Intelligence

### Overview
**Goal:** Implement the algorithms that actually optimize builds. This is where the magic happens - taking a seed build and evolving it into something optimized for DPS, survivability, and budget.

**Time Estimate:** 5-7 days
**Priority:** Critical - This is the whole point of the project!

**Approaches:**
1. **Genetic Algorithm** - Evolve builds over generations
2. **Greedy Optimization** - Iteratively pick best upgrades
3. **Hybrid** - Combine both for best results

---

## Prerequisites

### Completed
- ✅ Phase 1: PoB integration
- ✅ Phase 2: Data access
- ✅ Phase 3: Build representation

### New Libraries
```bash
pip install deap numpy scipy tqdm
```

- **DEAP:** Genetic algorithm framework
- **numpy/scipy:** Numerical optimization
- **tqdm:** Progress bars (important for long runs!)

---

## Day 1-2: Passive Tree Optimization

The passive tree is a graph pathfinding problem with ~1,500 nodes. We need to find the optimal allocation of ~100-120 points.

### Challenge
- **Search space:** Billions of possible combinations
- **Constraint:** Must form connected path
- **Objective:** Maximize DPS + EHP per point spent

### Tasks

#### 1. Implement Simple Greedy Pathfinder

**Claude Code Prompt:**
> "Create src/optimizer/tree_optimizer.py with a PassiveTreeOptimizer class. Start with a simple greedy algorithm:
>
> ```python
> class PassiveTreeOptimizer:
>     '''Optimize passive skill tree allocation.'''
>
>     def __init__(self, tree_graph, calculator):
>         self.tree = tree_graph
>         self.calculator = calculator
>
>     def greedy_optimize(
>         self,
>         build: Build,
>         target_keystones: List[str],
>         point_budget: int
>     ) -> Set[int]:
>         '''
>         Greedy algorithm: always pick the best next node.
>
>         Algorithm:
>         1. Start from class starting node
>         2. For each unallocated neighbor:
>            a. Test allocating it
>            b. Evaluate build with PoB
>            c. Calculate value = (DPS_gain + EHP_gain) / point
>         3. Pick node with best value
>         4. Repeat until budget exhausted
>
>         Returns:
>             Set of node IDs to allocate
>         '''
>
>     def find_path_to_keystone(
>         self,
>         current_nodes: Set[int],
>         keystone_name: str
>     ) -> List[int]:
>         '''
>         Find shortest path from allocated nodes to a keystone.
>         Uses NetworkX shortest_path.
>         '''
>
>     def _evaluate_node_value(
>         self,
>         build: Build,
>         node_id: int
>     ) -> float:
>         '''
>         Estimate value of allocating a node.
>
>         For speed, use heuristics instead of calling PoB:
>         - +X% increased damage: value += X * 10
>         - +Y to maximum life: value += Y
>         - Keystones: value += 100
>
>         For accuracy, call PoB and measure actual DPS change.
>         '''
> ```
>
> Implement the greedy algorithm first. It's simple and fast."

**File Location:** `src/optimizer/tree_optimizer.py`

#### 2. Add Heuristic-Based Value Estimation

**Claude Code Prompt:**
> "Add a fast heuristic evaluator to PassiveTreeOptimizer:
>
> ```python
> def estimate_node_value(self, node_data: dict, build_context: dict) -> float:
>     '''
>     Fast heuristic value estimation without calling PoB.
>
>     Args:
>         node_data: Node info from tree (name, stats, type)
>         build_context: Build info (main skill, damage type, etc.)
>
>     Returns:
>         Estimated value score
>
>     Heuristics:
>     - Physical damage nodes for physical skills
>     - Life nodes always valuable (1 life = 1 point)
>     - Keystones very valuable (100 points)
>     - Notables medium value (20 points)
>     - Small nodes low value (5 points)
>     - Irrelevant stats (ES for life builds) = 0 points
>     '''
>
>     value = 0.0
>     stats = node_data.get('stats', [])
>
>     for stat in stats:
>         # Parse stat text and assign value
>         if 'increased Physical Damage' in stat:
>             # Extract number
>             import re
>             match = re.search(r'(\d+)%', stat)
>             if match:
>                 value += int(match.group(1)) * 10
>
>         elif 'maximum Life' in stat:
>             match = re.search(r'(\d+) to maximum Life', stat)
>             if match:
>                 value += int(match.group(1))
>
>         # Add more heuristics...
>
>     # Multiply by node importance
>     if node_data['type'] == 'keystone':
>         value *= 2
>     elif node_data['type'] == 'notable':
>         value *= 1.5
>
>     return value
> ```
>
> This lets us evaluate thousands of nodes quickly without calling PoB."

#### 3. Test Tree Optimizer

**Claude Code Prompt:**
> "Create tests/test_tree_optimizer.py:
> 1. Test finding path to 'Resolute Technique' from Duelist start
> 2. Test greedy optimization allocates ~100 points
> 3. Verify allocated path is connected
> 4. Compare greedy vs random allocation (greedy should be much better)
> 5. Test that it respects point budget
> Include timing - should complete in <1 minute for 100 points."

---

## Day 3: Item Optimization

Item selection is easier than tree - we just need to try items and pick the best ones for each slot.

### Tasks

#### 1. Implement Item Optimizer

**Claude Code Prompt:**
> "Create src/optimizer/item_optimizer.py with an ItemOptimizer class:
>
> ```python
> class ItemOptimizer:
>     '''Optimize item selection for a build.'''
>
>     def __init__(self, item_database, pricing, calculator):
>         self.items = item_database
>         self.pricing = pricing
>         self.calculator = calculator
>
>     def optimize_items(
>         self,
>         build: Build,
>         constraints: Constraints
>     ) -> Dict[str, str]:
>         '''
>         Find best items for each slot within budget.
>
>         Algorithm:
>         1. Prioritize slots (weapon > armor > accessories)
>         2. For each slot:
>            a. Get valid items for slot + skill
>            b. Filter by budget
>            c. Test each item (up to N items per slot)
>            d. Pick item with best value/cost ratio
>         3. Return item selections
>
>         Returns:
>             Dict of slot_name -> item_name
>         '''
>
>     def optimize_slot(
>         self,
>         build: Build,
>         slot: str,
>         remaining_budget: int
>     ) -> Tuple[str, float]:
>         '''
>         Find best item for a specific slot.
>
>         Returns:
>             (item_name, item_price)
>         '''
>
>     def calculate_item_value(
>         self,
>         build: Build,
>         slot: str,
>         item_name: str
>     ) -> float:
>         '''
>         Calculate value of equipping an item.
>
>         Steps:
>         1. Clone build
>         2. Equip item in slot
>         3. Evaluate with PoB
>         4. Compare DPS/EHP with baseline
>         5. Return combined score
>
>         Value = (DPS_gain * weight_dps) + (EHP_gain * weight_ehp)
>         '''
> ```
>
> Implement with caching to avoid re-evaluating same items."

**File Location:** `src/optimizer/item_optimizer.py`

#### 2. Add Budget-Aware Selection

**Claude Code Prompt:**
> "Add smart budget allocation to ItemOptimizer:
>
> ```python
> def allocate_budget(
>     self,
>     total_budget: int,
>     num_slots: int
> ) -> Dict[str, int]:
>     '''
>     Allocate budget across equipment slots.
>
>     Strategy:
>     - Weapon: 40% of budget (biggest DPS impact)
>     - Body armor: 20% (biggest defense impact)
>     - Other slots: Divide remaining 40%
>
>     Returns:
>         Dict of slot -> budget_chaos
>     '''
> ```
>
> This prevents spending all budget on one item."

#### 3. Test Item Optimizer

**Claude Code Prompt:**
> "Create tests/test_item_optimizer.py:
> 1. Test optimizing weapon slot for Cyclone build
> 2. Verify selected weapon is appropriate (two-handed melee)
> 3. Test budget constraint is respected
> 4. Test that better items are preferred when affordable
> 5. Mock PoB calls to speed up tests
> Use small item subset for testing (10 weapons, not 500)."

---

## Day 4-5: Genetic Algorithm

This is the sophisticated approach - evolve builds over many generations.

### Tasks

#### 1. Design Genetic Representation

**Claude Code Prompt:**
> "Create src/optimizer/genetic.py with genetic algorithm implementation using DEAP library:
>
> ```python
> from deap import base, creator, tools, algorithms
>
> class GeneticBuildOptimizer:
>     '''Genetic algorithm for build optimization.'''
>
>     def __init__(self, calculator, data_loader, constraints):
>         self.calculator = calculator
>         self.data = data_loader
>         self.constraints = constraints
>
>         # GA parameters
>         self.population_size = 50
>         self.num_generations = 100
>         self.mutation_rate = 0.15
>         self.crossover_rate = 0.7
>         self.tournament_size = 3
>
>         self._setup_deap()
>
>     def _setup_deap(self):
>         '''Configure DEAP framework.'''
>         # Create fitness and individual classes
>         creator.create('FitnessMax', base.Fitness, weights=(1.0,))
>         creator.create('Individual', list, fitness=creator.FitnessMax)
>
>         # Register genetic operators
>         self.toolbox = base.Toolbox()
>         self.toolbox.register('evaluate', self.evaluate_individual)
>         self.toolbox.register('mate', self.crossover)
>         self.toolbox.register('mutate', self.mutate)
>         self.toolbox.register('select', tools.selTournament, tournsize=self.tournament_size)
>
>     def optimize(self, seed_build: Build) -> Build:
>         '''
>         Run genetic algorithm optimization.
>
>         Args:
>             seed_build: Starting template
>
>         Returns:
>             Best build found
>         '''
>
>     def create_random_individual(self, seed_build: Build):
>         '''
>         Create a random build based on seed.
>         Randomizes: passive nodes, items
>         Keeps fixed: skill, class, ascendancy
>         '''
>
>     def evaluate_individual(self, individual) -> Tuple[float]:
>         '''
>         Fitness function for genetic algorithm.
>
>         Steps:
>         1. Convert individual to Build object
>         2. Validate constraints
>         3. Evaluate with PoB
>         4. Calculate fitness score
>
>         Fitness = weighted sum of objectives:
>         - DPS (normalized)
>         - EHP (normalized)
>         - 1/Cost (normalized)
>         - Constraint penalties
>
>         Returns:
>             (fitness,): Tuple with single fitness value
>         '''
>
>     def crossover(self, ind1, ind2):
>         '''
>         Crossover operator: combine two parent builds.
>
>         Strategy:
>         - Passive tree: Swap subtrees (pick random node, swap branches)
>         - Items: Randomly swap items between parents
>
>         Returns:
>             (child1, child2)
>         '''
>
>     def mutate(self, individual):
>         '''
>         Mutation operator: randomly modify a build.
>
>         Mutations:
>         - Add/remove passive node (maintain connectivity!)
>         - Swap one item for another in same slot
>         - Adjust gem links
>
>         Returns:
>             (mutated_individual,)
>         '''
> ```
>
> Use DEAP's built-in algorithms where possible. Focus on good mutation/crossover operators."

**File Location:** `src/optimizer/genetic.py`

**Key Design Decisions:**

**Individual Representation:**
```python
# Each individual is a list: [passive_nodes, items, gems]
individual = [
    {node_ids},                    # Set of allocated passive nodes
    {slot: item_name},             # Dict of equipped items
    [[gem_links]],                 # List of gem link groups
]
```

**Fitness Function:**
```python
def fitness(individual) -> float:
    # Normalize objectives to [0, 1]
    norm_dps = dps / 10_000_000  # 10M DPS = 1.0
    norm_ehp = ehp / 500_000     # 500K EHP = 1.0
    norm_cost = 1 - (cost / max_budget)  # Cheaper = better

    # Weighted sum
    fitness = (
        norm_dps * 0.5 +      # 50% weight on damage
        norm_ehp * 0.3 +      # 30% weight on defense
        norm_cost * 0.2       # 20% weight on cost
    )

    # Penalty for constraint violations
    if life < min_life:
        fitness *= 0.5
    if any_res < 75:
        fitness *= 0.3

    return fitness
```

#### 2. Implement Efficient Evaluation

**Claude Code Prompt:**
> "Add caching and parallelization to genetic algorithm:
>
> ```python
> import functools
> from multiprocessing import Pool
>
> @functools.lru_cache(maxsize=1000)
> def cached_evaluate(build_hash: str) -> dict:
>     '''Cache PoB evaluations to avoid redundant calculations.'''
>
> def evaluate_population_parallel(self, population, num_workers=4):
>     '''
>     Evaluate entire population in parallel.
>     Speeds up GA significantly.
>     '''
>     with Pool(num_workers) as pool:
>         fitnesses = pool.map(self.evaluate_individual, population)
>     return fitnesses
> ```
>
> This is critical for performance - we'll evaluate 5000+ builds (50 pop × 100 gen)."

#### 3. Add Progress Tracking

**Claude Code Prompt:**
> "Add detailed logging and progress bars to genetic algorithm:
>
> ```python
> from tqdm import tqdm
> import logging
>
> def optimize(self, seed_build: Build) -> Build:
>     '''Run GA with progress tracking.'''
>
>     # Initialize population
>     population = [self.create_random_individual(seed_build)
>                   for _ in range(self.population_size)]
>
>     # Track best individual ever seen
>     best_ever = None
>     best_fitness = 0
>
>     # Evolution loop with progress bar
>     pbar = tqdm(range(self.num_generations), desc='Evolving')
>     for gen in pbar:
>         # Evaluate
>         fitnesses = self.evaluate_population_parallel(population)
>
>         # Update best
>         gen_best_idx = np.argmax(fitnesses)
>         if fitnesses[gen_best_idx] > best_fitness:
>             best_ever = population[gen_best_idx]
>             best_fitness = fitnesses[gen_best_idx]
>
>         # Log progress
>         pbar.set_postfix({
>             'best_fit': f'{best_fitness:.3f}',
>             'avg_fit': f'{np.mean(fitnesses):.3f}',
>             'gen': gen
>         })
>
>         # Genetic operations...
>         offspring = self.toolbox.select(population, len(population))
>         # ... crossover, mutation ...
>         population = offspring
>
>     return best_ever
> ```
>
> Users need to see progress - optimization takes minutes!"

#### 4. Test Genetic Algorithm

**Claude Code Prompt:**
> "Create tests/test_genetic.py:
> 1. Test GA improves fitness over generations (gen 0 < gen 50)
> 2. Test mutation maintains build validity
> 3. Test crossover produces valid offspring
> 4. Test population diversity (not all identical after 10 gens)
> 5. Compare GA result vs random build (should be much better)
> Use small population (10) and few generations (20) for testing."

---

## Day 5-6: Hybrid Optimization Strategy

Combine approaches for best results.

### Tasks

#### 1. Create Master Optimizer

**Claude Code Prompt:**
> "Create src/optimizer/master_optimizer.py that combines all optimizers:
>
> ```python
> class MasterOptimizer:
>     '''Coordinates all optimization strategies.'''
>
>     def __init__(self, calculator, data_loader, constraints):
>         self.tree_opt = PassiveTreeOptimizer(...)
>         self.item_opt = ItemOptimizer(...)
>         self.genetic_opt = GeneticBuildOptimizer(...)
>
>     def optimize_hybrid(
>         self,
>         seed_build: Build,
>         strategy: str = 'genetic_first'
>     ) -> Build:
>         '''
>         Hybrid optimization strategy.
>
>         Strategy 'genetic_first':
>         1. Run genetic algorithm (50 gens) for coarse search
>         2. Take best build from GA
>         3. Run greedy tree optimization to fine-tune
>         4. Run greedy item optimization
>         5. Return final build
>
>         Strategy 'greedy_first':
>         1. Greedy optimize tree
>         2. Greedy optimize items
>         3. Use as seed for GA refinement (20 gens)
>
>         Strategy 'iterative':
>         1. Alternate: optimize tree → optimize items → repeat
>         2. Stop when improvement < 1%
>         '''
>
>     def optimize_fast(self, seed_build: Build) -> Build:
>         '''
>         Fast optimization using only greedy algorithms.
>         Completes in <1 minute.
>         '''
>
>     def optimize_thorough(self, seed_build: Build) -> Build:
>         '''
>         Thorough optimization using genetic algorithm.
>         Takes 5-10 minutes but finds better builds.
>         '''
> ```
>
> Provide multiple optimization modes for different time budgets."

**File Location:** `src/optimizer/master_optimizer.py`

#### 2. Add Multi-Objective Optimization

**Claude Code Prompt:**
> "Add Pareto frontier calculation for multi-objective optimization:
>
> ```python
> def find_pareto_frontier(
>     self,
>     seed_build: Build,
>     objectives: List[str] = ['dps', 'ehp', 'cost']
> ) -> List[Build]:
>     '''
>     Find Pareto-optimal builds.
>
>     A build is Pareto-optimal if no other build is better
>     in ALL objectives simultaneously.
>
>     Returns:
>         List of non-dominated builds
>
>     Example:
>     Build A: 5M DPS, 200K EHP, 10 div
>     Build B: 6M DPS, 150K EHP, 20 div
>     Build C: 4M DPS, 250K EHP, 5 div
>     → All three are Pareto-optimal (trade-offs)
>     '''
>
>     # Run GA with modified fitness to explore different trade-offs
>     # Use NSGA-II algorithm from DEAP for multi-objective
>
>     from deap import tools
>     # Use NSGA2 selection instead of tournament
>     # ... implementation ...
> ```
>
> This gives users choices instead of one 'optimal' build."

#### 3. Integration Test

**Claude Code Prompt:**
> "Create tests/test_master_optimizer.py:
> 1. Test full optimization pipeline (seed → optimized build)
> 2. Verify optimized build meets all constraints
> 3. Verify optimized build is better than seed (DPS, EHP)
> 4. Test different strategies produce different builds
> 5. Benchmark: optimization completes in <10 minutes
> 6. Validate result imports successfully into actual PoB
> This is the ultimate integration test!"

---

## Day 7: Command-Line Interface (Preview)

Add basic CLI to test optimization.

### Tasks

**Claude Code Prompt:**
> "Create src/cli.py with basic optimization command:
>
> ```python
> import click
>
> @click.command()
> @click.option('--skill', default='Cyclone', help='Main skill')
> @click.option('--class-name', default='Duelist')
> @click.option('--ascendancy', default='Slayer')
> @click.option('--budget', default=5000000, help='Budget in chaos')
> @click.option('--strategy', default='hybrid', help='fast/hybrid/thorough')
> @click.option('--output', default='build.xml', help='Output file')
> def optimize(skill, class_name, ascendancy, budget, strategy, output):
>     '''Optimize a PoE build.'''
>
>     print(f'🔧 Optimizing {skill} {ascendancy}...')
>     print(f'💰 Budget: {budget:,} chaos')
>     print(f'🎯 Strategy: {strategy}')
>
>     # Load data
>     print('📚 Loading game data...')
>     data = PoBDataLoader()
>     data.load_all()
>
>     # Create seed build
>     seed = Build(
>         class_name=class_name,
>         ascendancy=ascendancy,
>         main_skill=skill,
>     )
>
>     # Create constraints
>     constraints = Constraints(
>         min_life=4000,
>         min_dps=1_000_000,
>         max_budget_chaos=budget,
>     )
>
>     # Optimize
>     optimizer = MasterOptimizer(calculator, data, constraints)
>
>     if strategy == 'fast':
>         best = optimizer.optimize_fast(seed)
>     elif strategy == 'thorough':
>         best = optimizer.optimize_thorough(seed)
>     else:
>         best = optimizer.optimize_hybrid(seed)
>
>     # Display results
>     print('\\n✨ Optimization complete!')
>     print(f'📊 DPS:  {best.stats[\"dps\"]:>12,.0f}')
>     print(f'❤️  Life: {best.stats[\"life\"]:>12,}')
>     print(f'🛡️  EHP:  {best.stats[\"ehp\"]:>12,.0f}')
>
>     # Export
>     generator = BuildXMLGenerator(data.items, data.gems)
>     xml = generator.generate_xml(best)
>     with open(output, 'w') as f:
>         f.write(xml)
>
>     code = generator.encode_for_import(xml)
>     print(f'\\n📋 PoB Import Code:')
>     print(code[:80] + '...')
>     print(f'\\n💾 Saved to: {output}')
>
> if __name__ == '__main__':
>     optimize()
> ```
>
> Usage:
> ```bash
> python -m src.cli --skill Cyclone --budget 10000000 --strategy thorough
> ```"

**File Location:** `src/cli.py`

---

## Deliverables Checklist

- [ ] `src/optimizer/tree_optimizer.py` - Passive tree optimization
- [ ] `src/optimizer/item_optimizer.py` - Item selection
- [ ] `src/optimizer/genetic.py` - Genetic algorithm
- [ ] `src/optimizer/master_optimizer.py` - Hybrid coordinator
- [ ] `src/cli.py` - Basic CLI interface
- [ ] `tests/test_tree_optimizer.py` - Tree tests
- [ ] `tests/test_item_optimizer.py` - Item tests
- [ ] `tests/test_genetic.py` - GA tests
- [ ] `tests/test_master_optimizer.py` - Integration test
- [ ] Documentation for each optimizer

---

## Success Criteria

### Must Have ✅
1. Tree optimizer finds valid paths with good value
2. Item optimizer selects appropriate items within budget
3. Genetic algorithm improves fitness over generations
4. Master optimizer produces builds better than seed
5. Optimized builds meet all constraints
6. CLI works end-to-end
7. Optimization completes in <10 minutes
8. Result imports into actual PoB

### Nice to Have 🎯
1. Pareto frontier optimization
2. Parallel evaluation (4+ cores)
3. Optimization completes in <5 minutes
4. Visual progress tracking
5. Build comparison tools

---

## Performance Targets

| Operation | Target | Stretch Goal |
|-----------|---------|--------------|
| Tree optimization | <2 min | <30s |
| Item optimization | <1 min | <15s |
| Full GA (100 gens) | <10 min | <5 min |
| Fast optimization | <2 min | <1 min |

---

## Common Issues & Solutions

### Issue: GA doesn't improve after generation 20
**Solution:** Check these:
- Is population diverse enough? (add diversity metric)
- Is mutation rate too low? (try 0.2-0.3)
- Is fitness function working? (log fitness values)
- Are invalid builds filtered? (count invalid builds per gen)

### Issue: Tree optimization produces disconnected nodes
**Solution:** Always validate connectivity after mutations:
```python
def is_tree_connected(nodes, tree_graph, start_node):
    subgraph = tree_graph.subgraph(nodes | {start_node})
    return nx.is_connected(subgraph)
```

### Issue: Optimization is too slow
**Solutions:**
1. Use heuristics instead of PoB calls for tree optimization
2. Cache PoB results (LRU cache)
3. Reduce population size (50 → 20)
4. Reduce generations (100 → 50)
5. Parallelize population evaluation

### Issue: All builds converge to same solution
**Solution:** Increase mutation rate and add diversity preservation:
```python
# Keep diverse builds in population
diversity_threshold = 0.8
if similarity(build1, build2) > diversity_threshold:
    # Replace with random build
    population[i] = create_random_individual(seed)
```

---

## Testing Strategy

```bash
# Unit tests
pytest tests/test_tree_optimizer.py -v
pytest tests/test_item_optimizer.py -v
pytest tests/test_genetic.py -v

# Integration test (slow!)
pytest tests/test_master_optimizer.py -v -s

# CLI test
python -m src.cli --skill Cyclone --budget 5000000 --strategy fast

# Profile performance
python -m cProfile -o profile.stats -m src.cli --skill Cyclone
python -m pstats profile.stats
```

---

## Algorithm Comparison

| Algorithm | Speed | Quality | Constraints | Best For |
|-----------|-------|---------|-------------|----------|
| Greedy Tree | Fast | Good | Easy | Quick iterations |
| Greedy Items | Fast | Good | Easy | Budget optimization |
| Genetic Algorithm | Slow | Best | Hard | Final optimization |
| Hybrid | Medium | Excellent | Medium | Production use |

**Recommendation:** Use hybrid strategy for best results.

---

## Next Steps

Once Phase 4 is complete:
1. **Validate extensively:** Test with multiple skills and budgets
2. **Benchmark vs meta builds:** Compare with poe.ninja top builds
3. **Profile and optimize:** Find bottlenecks, speed up slow parts
4. **Move to Phase 5:** Polish, testing, and documentation

**Phase 5 Preview:** We'll add a full CLI, create extensive tests, benchmark against real builds, and write complete documentation.

---

## Quick Reference

```bash
# Quick optimization test
python -m src.cli --skill Cyclone --budget 5000000 --strategy fast

# Thorough optimization
python -m src.cli --skill Cyclone --budget 50000000 --strategy thorough --output my_build.xml

# Test genetic algorithm
python -c "
from src.optimizer.genetic import GeneticBuildOptimizer
from src.models.build_templates import create_cyclone_slayer
seed = create_cyclone_slayer()
ga = GeneticBuildOptimizer(calc, data, constraints)
best = ga.optimize(seed)
print(f'Best fitness: {best.fitness}')
"
```

---

## Resources

- **DEAP Documentation:** https://deap.readthedocs.io/
- **Genetic Algorithms Tutorial:** https://www.geneticalgorithms.com/
- **NetworkX Algorithms:** https://networkx.org/documentation/stable/reference/algorithms/
- **scipy.optimize:** https://docs.scipy.org/doc/scipy/reference/optimize.html

---

**Ready for the most exciting part?** Start Day 1: Implementing tree optimization!

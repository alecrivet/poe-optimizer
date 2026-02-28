# Troubleshooting Guide

This guide helps you diagnose and fix common issues with the PoE Build Optimizer.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Import/Export Problems](#importexport-problems)
3. [Optimization Issues](#optimization-issues)
4. [Accuracy Problems](#accuracy-problems)
5. [Performance Problems](#performance-problems)
6. [Visualization Errors](#visualization-errors)
7. [Error Messages](#error-messages)
8. [Getting Help](#getting-help)

---

## Installation Issues

### "Module not found" errors

**Symptom:**
```
ModuleNotFoundError: No module named 'lupa'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install requirements
pip install -r requirements.txt

# Verify installation
python -c "import lupa; print('lupa OK')"
```

### Submodule not initialized

**Symptom:**
```
FileNotFoundError: PathOfBuilding/Data/3_0/TreeData.json not found
```

**Solution:**
```bash
# Initialize submodules
git submodule update --init --recursive

# Verify
ls PathOfBuilding/Data/3_0/TreeData.json
```

### LuaJIT not found

**Symptom:**
```
RuntimeError: Could not find LuaJIT library
```

**Solution:**

**Linux:**
```bash
sudo apt-get install luajit libluajit-5.1-dev
```

**MacOS:**
```bash
brew install luajit
```

**Windows:**
- Download LuaJIT from https://luajit.org/download.html
- Add to PATH or place in project directory

### Python version mismatch

**Symptom:**
```
SyntaxError: invalid syntax (type hints)
```

**Solution:**
```bash
# Check Python version (need 3.9+)
python --version

# If < 3.9, install newer Python
# Then create new venv with correct version
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Import/Export Problems

### Invalid PoB code

**Symptom:**
```
ValueError: Invalid base64 encoding
```

**Cause:** PoB code is corrupted or incomplete

**Solution:**
1. Re-copy the code from Path of Building
2. Ensure no extra spaces or newlines
3. Code should start with characters like `eNq9...`

```python
# Verify code format
pob_code = pob_code.strip()  # Remove whitespace
assert pob_code.startswith('eN'), "Invalid PoB code format"
```

### Decode fails with XML error

**Symptom:**
```
xml.etree.ElementTree.ParseError: mismatched tag
```

**Cause:** Build uses unsupported features or PoB version mismatch

**Solution:**
1. Verify build works in Path of Building
2. Try exporting a simpler build first
3. Check PoB version compatibility

```python
# Debug XML structure
from src.pob.codec import decode_pob_code
try:
    xml = decode_pob_code(pob_code)
    print("Decode successful")
    print(f"XML length: {len(xml)}")
except Exception as e:
    print(f"Decode failed: {e}")
```

### Encoded build doesn't import to PoB

**Symptom:** Optimized build code doesn't load in Path of Building

**Cause:** XML modification broke PoB compatibility

**Solution:**
1. Verify the optimized XML is valid:
```python
from src.pob.xml_parser import parse_pob_xml
stats = parse_pob_xml(optimized_xml)
print(f"Parsed stats: {stats}")
```

2. Compare with original:
```python
from src.visualization.tree_diff import visualize_tree_diff
visualize_tree_diff(original_xml, optimized_xml, "diff.txt")
```

3. Try importing to PoB and check error messages

---

## Optimization Issues

### No improvements found

**Symptom:**
```
Best improvement: +0.00%
```

**Possible Causes:**

**1. Build is already optimal**
```python
# Verify by trying different objectives
for obj in ['dps', 'life', 'ehp', 'balanced']:
    result = optimizer.optimize(build_xml, objective=obj)
    print(f"{obj}: {result.optimized_stats.dps_change_percent:+.2f}%")
```

**2. Relative calculator not working**
```python
# Test relative calculator
python tests/test_relative_calculator.py
```

**3. Tree graph not loaded**
```python
# Verify tree graph
from src.pob.tree_parser import load_passive_tree
tree = load_passive_tree()
print(f"Tree loaded: {len(tree.nodes)} nodes")
```

**4. Max iterations too low**
```python
# Increase iterations
optimizer = GreedyTreeOptimizer(max_iterations=100)
```

### Optimization makes build worse

**Symptom:** DPS decreases instead of increases

**Possible Causes:**

**1. Objective mismatch**
- You optimized for Life but expected DPS to increase
- Solution: Use correct objective

**2. Relative calculator inaccuracy**
- ~5-10% accuracy means some optimizations may be wrong
- Solution: Verify in Path of Building

**3. Build-specific mechanics**
- Complex interactions (Timeless Jewels, cluster jewels)
- Solution: Use constraints to preserve important nodes

```python
# Preserve specific nodes
from src.pob.modifier import get_passive_tree_summary
original_nodes = get_passive_tree_summary(build_xml)['allocated_nodes']
important_nodes = [12345, 67890]  # Your critical nodes

# After optimization, verify they're still there
optimized_nodes = get_passive_tree_summary(optimized_xml)['allocated_nodes']
for node in important_nodes:
    if node not in optimized_nodes:
        print(f"WARNING: Critical node {node} was removed!")
```

### Genetic algorithm doesn't converge

**Symptom:** Fitness keeps oscillating, never stabilizes

**Possible Causes:**

**1. Mutation rate too high**
```python
# Reduce mutation rate
optimizer = GeneticTreeOptimizer(mutation_rate=0.1)  # Instead of 0.2
```

**2. Population too small**
```python
# Increase population
optimizer = GeneticTreeOptimizer(population_size=50)  # Instead of 30
```

**3. Not enough generations**
```python
# Increase generations
optimizer = GeneticTreeOptimizer(generations=100)  # Instead of 50
```

**Solution: Check convergence explicitly**
```python
result = optimizer.optimize(build_xml, objective='dps')

# Plot convergence
from src.visualization.evolution_plot import plot_convergence_analysis
plot_convergence_analysis(result.best_fitness_history)
```

### Constraint violations

**Symptom:**
```
ConstraintViolation: Too many points: 120 > 116
```

**Solution:**
```python
# Check constraints before optimization
from src.optimizer.constraints import ConstraintSet
constraints = ConstraintSet(
    point_budget=PointBudgetConstraint.from_level(95)
)

if not constraints.validate(build_xml):
    print("Original build violates constraints:")
    for v in constraints.get_violations(build_xml):
        print(f"  - {v}")

# After optimization
if not constraints.validate(optimized_xml):
    print("Optimized build violates constraints!")
    # May need to adjust max_points_change
    optimizer = GeneticTreeOptimizer(max_points_change=5)
```

---

## Accuracy Problems

### Stats don't match Path of Building

**Symptom:** Optimizer says +10% DPS, but PoB shows only +5%

**Cause:** Relative calculator uses approximation

**Expected Accuracy:**
- ±5-10% for most stats
- Higher error for complex builds (multiple conversion chains, etc.)

**Verification Process:**
1. Import optimized build to Path of Building
2. Check actual stats
3. If difference > 10%, investigate

```python
# Check relative calculator accuracy
from src.pob.relative_calculator import RelativeCalculator

calc = RelativeCalculator()
result = calc.evaluate_relative_change(original_xml, modified_xml)

print(f"Estimated DPS change: {result.dps_change_percent:+.2f}%")
print(f"Estimated Life change: {result.life_change_percent:+.2f}%")

# Import to PoB and compare with actual stats
```

**Solutions:**

**1. Use PoB as ground truth:**
Always verify final results in Path of Building

**2. Run full calculation (slow but accurate):**
```python
# If you have Lua setup working
# (This is not currently implemented, but shows the concept)
# from src.pob.caller import evaluate_build_full
# actual_stats = evaluate_build_full(build_xml)
```

**3. Accept approximation for optimization:**
The relative calculator is accurate enough for ranking and selection

### Life/EHP calculations seem wrong

**Symptom:** Life optimization doesn't increase life as much as expected

**Possible Causes:**

**1. EHP vs Life confusion**
- EHP includes resistances and other defenses
- Life is just raw HP pool

```python
# Check both
result = optimizer.optimize(build_xml, objective='life')
print(f"Life: {result.optimized_stats.life_change_percent:+.2f}%")
print(f"EHP: {result.optimized_stats.ehp_change_percent:+.2f}%")
```

**2. Percentage vs absolute**
- Optimizer shows percentage improvement
- +10% life on 5000 HP = +500 HP
- +10% life on 3000 HP = +300 HP

**3. Other stats affecting survivability**
- Block, dodge, ES, regen not included in basic Life objective
- Use extended objectives for comprehensive defense

```python
from src.optimizer.extended_objectives import evaluate_extended_objectives
extended = evaluate_extended_objectives(original, optimized, base_eval)
print(f"Life: {extended.life_percent:+.2f}%")
print(f"ES: {extended.es_percent:+.2f}%")
print(f"Block: {extended.block_percent:+.2f}%")
```

---

## Performance Problems

### Optimization is very slow

**Symptom:** Greedy takes > 10 minutes, Genetic takes > 1 hour

**Possible Causes:**

**1. Too many iterations/generations**
```python
# Reduce iterations
optimizer = GreedyTreeOptimizer(max_iterations=30)  # Instead of 150
optimizer = GeneticTreeOptimizer(generations=30)    # Instead of 100
```

**2. Large tree with many nodes**
- More allocated nodes = more combinations to try
- Solution: Accept slower optimization or reduce tree size

**3. Mastery optimization enabled**
- Adds 30-60 seconds
```python
# Disable for testing
optimizer = GreedyTreeOptimizer(optimize_masteries=False)
```

**4. Debug logging enabled**
```python
# Disable verbose logging
import logging
logging.getLogger('src.optimizer').setLevel(logging.WARNING)
```

**Performance Benchmarks:**

| Configuration | Typical Runtime |
|---------------|-----------------|
| Greedy 50 iter | 2-3 minutes |
| Greedy 150 iter | 6-8 minutes |
| Genetic 30 pop, 50 gen | 10-15 minutes |
| Genetic 50 pop, 100 gen | 40-50 minutes |

If your runtime exceeds these significantly:
1. Check CPU usage (should be near 100% on one core)
2. Check memory usage (should be < 2 GB)
3. Close other applications
4. Try on a different machine

### Out of memory

**Symptom:**
```
MemoryError: Unable to allocate array
```

**Solution:**
```python
# Reduce population size
optimizer = GeneticTreeOptimizer(population_size=15)  # Instead of 50

# Or run greedy instead
optimizer = GreedyTreeOptimizer(max_iterations=50)
```

### Optimization freezes/hangs

**Symptom:** No output, no progress, CPU usage drops to 0%

**Possible Causes:**

**1. Deadlock in Lua interaction**
```bash
# Kill process and restart
# Check if luajit is accessible
which luajit
luajit -v
```

**2. Infinite loop in algorithm**
```python
# Enable verbose mode to see where it hangs
optimizer = GreedyTreeOptimizer(verbose=True)
```

**3. Resource exhaustion**
```bash
# Check system resources
top  # Linux/Mac
# Look for Python process using 100% memory
```

---

## Visualization Errors

### Matplotlib not found

**Symptom:**
```
ModuleNotFoundError: No module named 'matplotlib'
```

**Solution:**
```bash
pip install matplotlib numpy
```

### Plotly not found

**Symptom:**
```
ModuleNotFoundError: No module named 'plotly'
```

**Solution:**
```bash
pip install plotly
```

### Plot shows empty/no data

**Symptom:** PNG/HTML file created but plot is blank

**Possible Causes:**

**1. Empty frontier**
```python
if frontier.size() == 0:
    print("Frontier is empty - run optimization first")
```

**2. Empty fitness history**
```python
if not result.best_fitness_history:
    print("No fitness history - optimization didn't run properly")
```

**Solution:**
```python
# Verify data before plotting
print(f"Frontier size: {frontier.size()}")
print(f"Fitness history length: {len(result.best_fitness_history)}")
```

### 3D plot not interactive

**Symptom:** HTML file opens but plot doesn't respond to mouse

**Solution:**
1. Ensure Plotly is installed
2. Try different browser (Chrome/Firefox recommended)
3. Check JavaScript is enabled
4. Use static plot instead:
```python
plot_pareto_frontier_3d(frontier, interactive=False)
```

---

## Error Messages

### "Tree graph not loaded"

**Full error:**
```
RuntimeError: Passive tree graph not loaded. Call load_passive_tree() first.
```

**Solution:**
```python
from src.pob.tree_parser import load_passive_tree

# Load tree graph
tree = load_passive_tree()

# Pass to optimizer
optimizer = GreedyTreeOptimizer()
# Tree is loaded automatically in __init__
```

### "Node X not in tree graph"

**Full error:**
```
KeyError: Node 12345 not found in tree graph
```

**Cause:** Build references node that doesn't exist (old tree version, corrupted data)

**Solution:**
1. Verify build works in Path of Building
2. Check PoB version matches tree data version
3. Re-export build from PoB

### "Mastery database not found"

**Full error:**
```
FileNotFoundError: MasteryEffects.json not found
```

**Solution:**
```bash
# Ensure submodules are initialized
git submodule update --init --recursive

# Verify file exists
ls PathOfBuilding/Data/3_0/MasteryEffects.json
```

### "Invalid objective"

**Full error:**
```
ValueError: Invalid objective 'damage'. Must be one of: dps, life, ehp, balanced
```

**Solution:**
```python
# Use valid objective
valid_objectives = ['dps', 'life', 'ehp', 'balanced']
result = optimizer.optimize(build_xml, objective='dps')  # Not 'damage'
```

### "XML modification failed"

**Full error:**
```
RuntimeError: Failed to modify passive tree: XML structure invalid
```

**Possible Causes:**
1. Corrupted XML
2. Unsupported PoB version
3. Build uses unsupported features

**Debug Steps:**
```python
# 1. Verify XML is valid
import xml.etree.ElementTree as ET
try:
    root = ET.fromstring(build_xml)
    print("XML is valid")
except ET.ParseError as e:
    print(f"XML parse error: {e}")

# 2. Check tree structure
from src.pob.modifier import get_passive_tree_summary
summary = get_passive_tree_summary(build_xml)
print(f"Allocated nodes: {len(summary['allocated_nodes'])}")
print(f"Mastery effects: {len(summary.get('mastery_effects', {}))}")

# 3. Try minimal modification
from src.pob.modifier import modify_passive_tree_nodes
modified = modify_passive_tree_nodes(
    build_xml,
    nodes_to_add=[],
    nodes_to_remove=[]
)
print("Minimal modification successful")
```

---

## Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide**
2. **Search existing GitHub issues:** https://github.com/alecrivet/poe-optimizer/issues
3. **Verify your environment:**
```bash
python --version  # Should be 3.9+
pip list | grep lupa  # Should show lupa installed
ls PathOfBuilding/Data/3_0/TreeData.json  # Should exist
```

4. **Create minimal reproducible example:**
```python
# Minimal example that reproduces the issue
from src.pob.codec import decode_pob_code
from src.optimizer.tree_optimizer import GreedyTreeOptimizer

pob_code = "eNq9..."  # Your build code
build_xml = decode_pob_code(pob_code)

optimizer = GreedyTreeOptimizer(max_iterations=10)
result = optimizer.optimize(build_xml, objective='dps')  # Error occurs here
```

### Reporting Bugs

When opening a GitHub issue, include:

1. **Environment information:**
```bash
python --version
pip list
uname -a  # Linux/Mac
# Or
systeminfo  # Windows
```

2. **Build code (if relevant):**
```
PoB code: eNq9...
```

3. **Full error message:**
```
Traceback (most recent call last):
  File "...", line X, in <module>
    ...
Error: ...
```

4. **Steps to reproduce:**
```
1. Clone repo
2. Install dependencies
3. Run: python examples/integration/example_1_quick_optimization.py
4. Error appears at line 45
```

5. **Expected vs actual behavior:**
```
Expected: DPS improvement of +5%
Actual: DPS decreased by -2%
```

### Debugging Tips

**Enable debug logging:**
```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Test individual components:**
```bash
# Test codec
python -c "from src.pob.codec import decode_pob_code, encode_pob_code; print('Codec OK')"

# Test tree parser
python -c "from src.pob.tree_parser import load_passive_tree; tree = load_passive_tree(); print(f'Tree: {len(tree.nodes)} nodes')"

# Test relative calculator
python tests/test_relative_calculator.py

# Test optimizer
python tests/test_optimizer.py
```

**Use Python debugger:**
```python
import pdb; pdb.set_trace()  # Add before problematic line
```

**Check intermediate results:**
```python
# After each step, verify results
print(f"Step 1: {result}")
assert result is not None, "Result should not be None"
```

### Community Support

- **GitHub Issues:** https://github.com/alecrivet/poe-optimizer/issues
- **GitHub Discussions:** (If enabled)
- **PoE Forums:** (Link when available)

### Professional Support

This is an open-source project. For commercial support or custom development:
- Check CONTRIBUTING.md for contribution guidelines
- Consider sponsoring the project
- Contact maintainers via GitHub

---

## Known Issues

### Timeless Jewels Not Supported

**Status:** Known limitation

Timeless Jewels transform passive tree nodes in complex ways that require full PoB calculation engine. Not currently supported.

**Workaround:** Manually optimize around your Timeless Jewel allocation.

### Cluster Jewels Not Supported

**Status:** Known limitation

Cluster Jewels add dynamic nodes to the tree, which requires special handling. Not currently supported.

**Workaround:** Optimize passive tree, then add cluster jewels manually.

### Relative Calculator Accuracy

**Status:** By design

~5-10% accuracy is acceptable for optimization purposes. For exact stats, always verify in Path of Building.

**Workaround:** None needed - this is expected behavior.

### Some Builds Don't Optimize Well

**Status:** Known limitation

Complex builds with many interactions (conversion chains, trigger setups, etc.) may not optimize well due to relative calculator limitations.

**Workaround:** Use greedy optimizer for conservative changes, or optimize manually guided by node impact analysis.

---

## Frequently Encountered Issues

### Issue: "My DPS went down!"

**Likely cause:** Optimized for wrong objective (Life instead of DPS)
**Solution:** Use `objective='dps'`

### Issue: "Optimization takes forever"

**Likely cause:** Too many generations/iterations
**Solution:** Use Quick Test preset (see CONFIGURATION.md)

### Issue: "Import to PoB fails"

**Likely cause:** XML corruption
**Solution:** Re-run optimization, check tree diff

### Issue: "No improvements on already-good build"

**Likely cause:** Build is near-optimal
**Solution:** Try genetic algorithm for <1% improvements

### Issue: "Results vary between runs"

**Likely cause:** Genetic algorithm is stochastic
**Solution:** This is expected - run multiple times and pick best

---

## Quick Reference

### Common Commands

```bash
# Install
pip install -r requirements.txt
git submodule update --init --recursive

# Test
python tests/test_optimizer.py
python tests/test_relative_calculator.py

# Run examples
python examples/integration/example_1_quick_optimization.py

# Debug
python -m pdb examples/integration/example_1_quick_optimization.py
```

### Common Fixes

```python
# Fix: No improvements
optimizer = GreedyTreeOptimizer(max_iterations=100)

# Fix: Too slow
optimizer = GreedyTreeOptimizer(max_iterations=20, optimize_masteries=False)

# Fix: Out of memory
optimizer = GeneticTreeOptimizer(population_size=15)

# Fix: Constraint violations
constraints = ConstraintSet(
    point_budget=PointBudgetConstraint.from_level(character_level)
)
```

---

**Still having issues?** Open a GitHub issue with full details!

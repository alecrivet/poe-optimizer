# Hybrid Optimization Approach

**Insight:** For build optimization, we don't need perfect DPS calculations - we need **relative improvements**!

---

## The Key Realization

When optimizing a build:
- ✅ We care about: "Did this change make it better?"
- ❌ We don't need: "What's the exact DPS?"

**Example:**
- Original build: 3.16M DPS (from XML)
- Add 5 life nodes: HeadlessWrapper says "1.48M DPS"
- Remove those nodes, add 5 DPS nodes: HeadlessWrapper says "1.52M DPS"
- **Conclusion:** DPS nodes > life nodes (even though both numbers are wrong!)

---

## Approach 1: Relative Calculations (Simple Builds)

**For builds HeadlessWrapper CAN calculate:**

1. **Read baseline** from XML (accurate)
2. **Modify** build (add/remove nodes, change gems)
3. **Calculate ratio** with HeadlessWrapper
4. **Extrapolate** real DPS

```python
# Get baseline from XML
baseline_xml_stats = parse_pob_stats(original_xml)
baseline_dps_accurate = baseline_xml_stats['CombinedDPS']  # 3.16M

# Calculate baseline with HeadlessWrapper
baseline_lua_stats = run_lua_evaluator(original_xml)
baseline_dps_lua = baseline_lua_stats['combinedDPS']  # 42K (wrong!)

# Modify build
modified_xml = modify_passive_tree_nodes(original_xml, add_nodes=[...])

# Calculate modified with HeadlessWrapper
modified_lua_stats = run_lua_evaluator(modified_xml)
modified_dps_lua = modified_lua_stats['combinedDPS']  # 45K

# Extrapolate real modified DPS
ratio = modified_dps_lua / baseline_dps_lua  # 45K / 42K = 1.07
estimated_real_dps = baseline_dps_accurate * ratio  # 3.16M * 1.07 = 3.38M
```

**Pros:**
- ✅ Works for all modification types
- ✅ Cross-platform (just LuaJIT)
- ✅ Fast
- ✅ No external dependencies

**Cons:**
- ⚠️ Assumes changes scale linearly (mostly true for passive tree)
- ⚠️ May be inaccurate for complex mechanic changes

---

## Approach 2: Statistical Models (No Calculation)

**For passive tree optimization specifically:**

Build a statistical model of node values:
```python
# Learn from data
life_per_node = analyze_passive_tree_life_nodes()  # ~5 life per node
dps_per_node = analyze_passive_tree_dps_nodes()  # ~2% per node

# Estimate without calculation
def estimate_modification_impact(add_nodes, remove_nodes):
    life_change = sum(life_per_node[n] for n in add_nodes)
    life_change -= sum(life_per_node[n] for n in remove_nodes)

    dps_change_pct = sum(dps_per_node[n] for n in add_nodes)
    dps_change_pct -= sum(dps_per_node[n] for n in remove_nodes)

    return {
        'life_change': life_change,
        'dps_change_pct': dps_change_pct
    }
```

**Pros:**
- ✅ Extremely fast
- ✅ No PoB calculations needed
- ✅ Good enough for passive tree optimization

**Cons:**
- ❌ Can't optimize skill gems or items
- ❌ Doesn't account for interactions

---

## Approach 3: Sampling + GUI Automation (Hybrid)

**For final validation only:**

1. Run optimization with Approach 1 (relative calculations)
2. Get top 10 builds
3. **Use GUI automation ONCE** for each top build
4. Get accurate stats for final comparison

```python
# Optimize using relative calculations (fast, cross-platform)
optimizer = PassiveTreeOptimizer()
top_builds = optimizer.optimize(generations=100)  # Uses Approach 1

# Final validation on top builds (slow, Windows-only, but only 10 builds)
if platform.system() == "Windows":
    automation = PoBAutomation()
    for build in top_builds[:10]:
        accurate_stats = automation.recalculate_build(build.to_pob_code())
        build.accurate_stats = accurate_stats
```

**Pros:**
- ✅ Fast optimization (thousands of evaluations)
- ✅ Accurate final results (10 GUI automations)
- ✅ Best of both worlds

**Cons:**
- ⚠️ Windows-only for final validation
- ⚠️ Complex workflow

---

## Recommendation: Approach 1 (Relative Calculations)

**Why:**
1. **Good enough** - 5-10% error is fine for optimization
2. **Cross-platform** - Works on Mac, Windows, Linux
3. **Fast** - Can evaluate thousands of builds per minute
4. **Simple** - Easy to implement and test

**Implementation:**

```python
# src/pob/relative_calculator.py

class RelativeCalculator:
    """
    Calculate relative build improvements using HeadlessWrapper.

    Accuracy: ~5-10% error, but consistent for comparisons.
    """

    def __init__(self):
        self.pob_calc = PoBCalculator()

    def evaluate_modification(self, original_xml: str, modified_xml: str) -> Dict:
        """
        Evaluate a build modification relative to original.

        Returns:
            {
                'baseline_accurate_dps': float,  # From XML
                'estimated_dps': float,          # Extrapolated
                'dps_change_percent': float,     # % improvement
                'relative_ratio': float,         # Lua modified / Lua baseline
            }
        """
        # Get accurate baseline from XML
        baseline_accurate = get_build_summary(original_xml)

        # Calculate both with Lua
        baseline_lua = self.pob_calc._evaluate_with_lua(original_xml)
        modified_lua = self.pob_calc._evaluate_with_lua(modified_xml)

        # Calculate ratio
        ratio = modified_lua['combinedDPS'] / baseline_lua['combinedDPS']

        # Extrapolate
        estimated_dps = baseline_accurate['combinedDPS'] * ratio

        return {
            'baseline_accurate_dps': baseline_accurate['combinedDPS'],
            'estimated_dps': estimated_dps,
            'dps_change_percent': (ratio - 1) * 100,
            'relative_ratio': ratio,
        }
```

---

## Testing Plan

**Test 1: Does ratio extrapolation work?**
```python
# Use build2
original = decode_pob_code(build2_code)

# Make known modification (add 10% more damage node)
# Should see ~10% DPS increase in ratio
modified = modify_passive_tree_nodes(original, add_nodes=[known_dps_node])

result = calculator.evaluate_modification(original, modified)
assert 1.08 < result['relative_ratio'] < 1.12  # ~10% increase
```

**Test 2: Does it rank changes correctly?**
```python
# Make 3 modifications of different strengths
weak_mod = add_5_life_nodes(original)      # Small change
medium_mod = add_10_dps_nodes(original)    # Medium change
strong_mod = add_20_dps_nodes(original)    # Large change

# Even if absolute numbers are wrong, ranking should be correct
weak_ratio = calculate_ratio(original, weak_mod)
medium_ratio = calculate_ratio(original, medium_mod)
strong_ratio = calculate_ratio(original, strong_mod)

assert weak_ratio < medium_ratio < strong_ratio  # ✓ Ranking correct!
```

---

## Timeline

**Phase 1 (2-3 hours):** Implement RelativeCalculator
**Phase 2 (1-2 hours):** Test with known modifications
**Phase 3 (2-3 hours):** Build simple passive tree optimizer
**Phase 4 (1 hour):** Document limitations

**Total:** ~8 hours to working optimizer!

---

## Limitations & Mitigations

### Limitation 1: Not accurate for absolute DPS
**Mitigation:** Document this clearly. Users can use PoB GUI for final validation.

### Limitation 2: May not work for skill gem swaps
**Mitigation:** Start with passive tree only. Add gem optimization later with GUI automation.

### Limitation 3: Assumes linear scaling
**Mitigation:** Test with various modification sizes, add calibration if needed.

---

## Next Steps

1. Implement `RelativeCalculator`
2. Test with build2 (add/remove nodes, measure ratios)
3. Build simple optimizer using genetic algorithm
4. Celebrate working cross-platform optimizer! 🎉

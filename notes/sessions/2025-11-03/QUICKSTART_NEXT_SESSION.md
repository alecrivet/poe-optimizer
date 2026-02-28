# Quick Start Guide - Next Session

**Date:** 2024-11-03 Evening / 2024-11-04+
**Status:** Relative Calculator Implemented | Ready for Testing

---

## 🎯 Where We Left Off

### ✅ What's Complete

**Phase 1: PoB Integration** ✅
- XML codec (encode/decode PoB codes)
- XML parser (extract pre-calculated stats)
- XML modification (change tree, gems, level)
- All tests passing (19 codec + 5 modifier)

**Phase 2 Progress:**
- ✅ Investigated HeadlessWrapper limitations
- ✅ Tested PostLoad fixes (didn't work)
- ✅ Tested skill selection (works but DPS still wrong)
- ✅ **Implemented RelativeCalculator** (ratio extrapolation approach)

### ⚠️ What We Discovered

**HeadlessWrapper Cannot Calculate Complex Builds:**
- General's Cry + Ground Slam: 28K DPS (should be 3.16M) ❌
- Cyclone: 42K DPS (should be 3.16M) ❌
- Complex mechanics don't calculate properly
- Would take weeks to fix properly

**PoB Desktop Automation Won't Work:**
- PoB is Windows-only ❌
- No native Mac version
- Wine/Crossover possible but complex

### ✅ The Solution: Relative Calculations

**Instead of absolute accuracy, use ratio extrapolation:**

```python
# Get accurate baseline from XML
baseline_xml_dps = 3.16M  # Correct!

# Calculate with Lua (wrong absolute values)
baseline_lua_dps = 42K    # Wrong but consistent
modified_lua_dps = 45K    # Also wrong but consistent

# Use the RATIO (this is accurate!)
ratio = 45K / 42K = 1.07  # 7% improvement

# Extrapolate
estimated_dps = 3.16M * 1.07 = 3.38M  # Good enough!
```

---

## 🚀 Quick Validation

```bash
cd /Users/alec/Documents/Projects/poe-optimizer

# Test relative calculator
PYTHONPATH=$(pwd) python3 test_relative_calculator.py

# Should show:
# - Modifications ranked correctly
# - Ratios make sense (changes in expected direction)
# - Cross-platform (no Windows needed!)
```

---

## 📁 Key Files

**New Implementation:**
- `src/pob/relative_calculator.py` - Ratio extrapolation calculator ✅
- `test_relative_calculator.py` - Test with real modifications ⚠️ (needs testing)

**Previous Work:**
- `src/pob/codec.py` - PoB code encoder/decoder ✅
- `src/pob/xml_parser.py` - Parse pre-calculated stats ✅
- `src/pob/modifier.py` - Modify builds (tree/gems/level) ✅
- `src/pob/automation.py` - PoB automation (won't use, Windows-only)

**Investigation:**
- `notes/sessions/2024-11-03/IMPROVED_HEADLESS_WRAPPER_PLAN.md`
- `notes/sessions/2024-11-03/HYBRID_OPTIMIZATION_APPROACH.md`
- `notes/sessions/2024-11-03/HEADLESS_WRAPPER_INVESTIGATION.md`

**Tests:**
- `src/pob/test_postload.lua` - PostLoad fix test (failed)
- `src/pob/test_main_socket_group.lua` - Skill selection test

---

## 🎯 Next Steps

### Immediate: Test Relative Calculator

1. **Run the test**
   ```bash
   PYTHONPATH=$(pwd) python3 test_relative_calculator.py
   ```

2. **Validate results:**
   - ✅ Removing nodes should decrease stats
   - ✅ Lowering level should decrease stats
   - ✅ Ratios should rank changes correctly
   - ✅ Changes should be in expected direction

3. **If tests pass:**
   - Relative calculator is viable! 🎉
   - Can proceed with optimization algorithms

4. **If tests fail:**
   - Investigate what's wrong
   - May need calibration factor
   - Or try different approach

### Next: Build Optimizer

Once relative calculator works:

1. **Passive Tree Optimizer** (Week 2)
   - Start with simple greedy algorithm
   - Add/remove nodes to maximize objective
   - Use relative calculator for evaluation

2. **Genetic Algorithm** (Week 3-4)
   - Represent builds as chromosomes
   - Mutation: add/remove nodes
   - Fitness: relative calculator score
   - Evolve for 100s of generations

3. **Multi-Objective** (Week 5+)
   - Balance DPS, Life, EHP
   - Pareto frontier
   - Budget constraints

---

## ⚠️ Important Notes

### Relative Calculator Limitations

**What it's good for:**
- ✅ Passive tree optimization
- ✅ Level optimization
- ✅ Gem level/quality tweaks
- ✅ Ranking many modifications quickly

**What it's NOT good for:**
- ❌ Absolute DPS accuracy (5-10% error)
- ❌ Complex mechanic changes (skill swaps)
- ❌ Final validation (use PoB GUI for that)

**Assumption:** Changes scale linearly
- Mostly true for passive tree (+10% node = +10% DPS)
- Less true for mechanics (General's Cry, triggers, etc.)

### Future: Accurate Calculations

**Long-term goals for absolute accuracy:**

**Option 1:** Contribute to PoB
- Fix HeadlessWrapper for complex mechanics
- Add proper skill selection
- Add configuration options
- **Benefit:** Helps entire community
- **Effort:** High (weeks/months)

**Option 2:** Build/Use Web API
- Host PoB calculation service
- Send build XML → Get accurate stats
- **Benefit:** Works for everyone
- **Effort:** Medium (server hosting)

**Option 3:** ML Correction Model
- Train model to predict HeadlessWrapper errors
- Correct the wrong calculations
- **Benefit:** Fast, cross-platform
- **Effort:** Medium (need training data)

---

## 📚 Key Documentation

**Today's Session:**
- `SESSION_SUMMARY.md` - Full session notes (2024-11-03)
- `HYBRID_OPTIMIZATION_APPROACH.md` - Relative calc approach
- `IMPROVED_HEADLESS_WRAPPER_PLAN.md` - HeadlessWrapper investigation

**Previous Sessions:**
- `notes/sessions/2024-11-02/FINAL_SOLUTION.md` - XML parser solution
- `notes/sessions/2024-11-02/session.md` - Phase 1 completion

**Code Organization:**
- `CONTRIBUTING.md` - Never modify PathOfBuilding/

---

## 🎨 Example Usage

```python
from src.pob.codec import decode_pob_code, encode_pob_code
from src.pob.modifier import modify_passive_tree_nodes
from src.pob.relative_calculator import RelativeCalculator

# Load build
with open('examples/build2') as f:
    code = f.read().strip()
original_xml = decode_pob_code(code)

# Create calculator
calc = RelativeCalculator()

# Test modifications
modifications = {
    "Add 5 DPS nodes": modify_passive_tree_nodes(
        original_xml,
        nodes_to_add=[123, 456, 789, 101, 112]
    ),
    "Add 5 life nodes": modify_passive_tree_nodes(
        original_xml,
        nodes_to_add=[234, 567, 890, 123, 456]
    ),
}

# Compare
results = calc.compare_modifications(original_xml, modifications)

# Rank by DPS
ranked = calc.rank_by_objective(results, 'dps')
for name, result in ranked:
    print(f"{name}: {result.estimated_dps:,.0f} DPS ({result.dps_change_percent:+.1f}%)")
```

---

## 🔧 Current Architecture

```
User: "Optimize my build for max DPS"
    ↓
Load build (decode XML)
    ↓
Get accurate baseline from XML stats
    ↓
Generate modifications (add/remove nodes)
    ↓
For each modification:
   ├─ Calculate with Lua (relative ratio)
   ├─ Extrapolate estimated DPS
   └─ Score modification
    ↓
Rank by objective (DPS/Life/EHP)
    ↓
Return top builds
    ↓
User validates in PoB GUI (final accuracy)
```

---

## 📊 Success Criteria

**Relative calculator is working if:**
- ✅ Removing nodes decreases stats
- ✅ Adding DPS nodes increases estimated DPS
- ✅ Adding life nodes increases estimated life
- ✅ Ratios rank changes correctly
- ✅ Changes are in expected direction

**NOT expecting:**
- Perfect absolute accuracy (will have 5-10% error)
- Support for skill mechanic changes
- Complex interaction modeling

---

## 🎯 Project Goals Recap

**Short-term (Next 2 weeks):**
- [x] Phase 1: PoB Integration ✅
- [ ] Phase 2: Relative calculator working
- [ ] Phase 3: Simple passive tree optimizer
- [ ] Phase 4: Genetic algorithm

**Long-term (1-6 months):**
- [ ] Accurate absolute calculations (contribute to PoB?)
- [ ] Multi-objective optimization
- [ ] Web interface
- [ ] Community release

**Ultimate Vision:**
- Brute force optimal builds for any objective
- True absolute accuracy
- Handle all game mechanics
- Help PoE community optimize builds

---

**Session Status:** RelativeCalculator ✅ Implemented | ⚠️ Needs Testing

**Next Action:** Run `python3 test_relative_calculator.py` and validate results

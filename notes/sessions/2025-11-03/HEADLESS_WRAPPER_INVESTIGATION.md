# HeadlessWrapper Investigation - Build Modification Challenge

**Date:** 2024-11-03
**Goal:** Enable build modification and recalculation for optimization

---

## Investigation Summary

### What Works ✅

1. **Skills Load Properly**
   - All 6 socket groups loaded from XML
   - Skills correctly identified (Cyclone, Ground Slam, Blood Rage, etc.)
   - displaySkillListCalcs is populated

2. **BuildOutput() Executes**
   - Can manually trigger `build.calcsTab:BuildOutput()`
   - Calculation engine runs without errors
   - Returns output stats

3. **XML Pre-calculated Stats**
   - XML contains `<PlayerStat>` tags with accurate stats
   - Build 2: CombinedDPS = 3,163,831 ✅
   - Parsing XML stats is fast and reliable

### What Doesn't Work ❌

1. **Lua Calculation Shows Wrong DPS**
   - HeadlessWrapper calculates: 42,403 DPS (Build 2)
   - Expected from XML: 3,163,831 DPS
   - Off by factor of 74x!

2. **Root Cause**
   - Build 2 uses **General's Cry + Ground Slam** (complex mechanic)
   - General's Cry summons mirages that attack with Ground Slam
   - HeadlessWrapper appears to calculate Cyclone's DPS instead
   - Main skill selection not working properly in headless mode

### Debug Evidence

```
=== Checking Output ===
  CombinedDPS: 42403.063813961  ← Wrong skill's DPS
  Life: 1527  ← Also wrong (XML shows 4615)

=== Checking Skill Groups ===
Group 1: Cyclone of Tumult (Body Armour)
Group 3: Ground Slam + General's Cry (Weapon 1)  ← This is the main DPS!
```

---

## The Fundamental Challenge

**HeadlessWrapper Cannot Reliably Recalculate Complex Builds**

Even though we can:
- Load builds from XML ✅
- Trigger calculations ✅
- Access the calculation API ✅

We cannot:
- Force correct main skill selection ❌
- Set all configuration options programmatically ❌
- Match PoB app's calculation accuracy ❌

---

## Solutions for Build Optimization

### Approach A: Hybrid Strategy (RECOMMENDED)

**For Reading Existing Builds:**
- ✅ Use XML pre-calculated stats (fast, accurate)
- Current `PoBCalculator` already does this

**For Modified Builds:**
1. Modify XML (items, tree, gems)
2. Encode to PoB code
3. **Use PoB's export API** or **web service** to recalculate
4. Parse updated stats from re-exported XML

**Pros:**
- Leverages PoB's full calculation engine
- Accurate for all build types
- We only need to implement XML modification

**Cons:**
- Requires PoB instance running (desktop app or web version)
- Slower than pure Lua approach
- More complex integration

### Approach B: XML-Only Modifications

**Strategy:**
- Only modify builds in ways that don't change DPS calculation
- Example modifications:
  - Swap items with similar stats
  - Add/remove passive tree nodes (stats additive)
  - Change gem levels/quality
- **Approximate DPS** using stat changes rather than recalculating

**Pros:**
- No need for PoB recalculation
- Fast optimization iterations
- Simple to implement

**Cons:**
- Less accurate for complex interactions
- Can't optimize skill choices
- Limited to incremental changes

### Approach C: Simplified Build Archetypes

**Strategy:**
- Focus optimization on "simple" builds first
- Avoid:
  - Warcry builds (General's Cry, etc.)
  - Complex totem/mine/trap mechanics
  - Minion builds
- Start with direct attack/cast builds

**Pros:**
- HeadlessWrapper might work for simple builds
- Full end-to-end optimization possible
- Good starting point

**Cons:**
- Limited build coverage
- Miss out on many meta builds
- Still uncertain if HeadlessWrapper works even for simple builds

---

## Recommended Path Forward

### Phase 2A: XML Modification Layer (Days 5-6)

**Implement core build modification functions:**

```python
# src/pob/modifier.py

def modify_passive_tree(xml: str, nodes_to_add: List[int], nodes_to_remove: List[int]) -> str:
    """Add/remove passive tree nodes"""

def modify_item(xml: str, slot: str, new_item: Item) -> str:
    """Replace item in a slot"""

def modify_gem_level(xml: str, socket_group: int, gem: str, level: int) -> str:
    """Change gem level/quality"""

def modify_ascendancy(xml: str, new_ascendancy: str) -> str:
    """Change ascendancy class"""
```

**Test modifications:**
- Modify build → encode → decode → verify XML changes
- DON'T try to recalculate yet

### Phase 2B: PoB Integration Strategy (Days 7-8)

**Decide on recalculation method:**

**Option 1:** Use PoB Desktop App
- AppleScript/automation to import code, export XML
- Most accurate, but requires app running

**Option 2:** Use pob.party Web API
- POST build code, GET calculated stats
- Simple HTTP integration
- Depends on third-party service

**Option 3:** Build Simple Optimizer Without Recalculation
- Use statistical approximations
- "If you add +50 life nodes, Life increases by ~50"
- Good enough for passive tree optimization

---

## Next Steps

1. ✅ Document HeadlessWrapper limitations
2. ⏭ Decide on recalculation strategy (discuss with user)
3. ⏭ Implement XML modification functions
4. ⏭ Test full cycle: read → modify → encode → (recalculate) → verify

---

## Files Modified Today

- `src/pob/evaluator.lua` - Enhanced to trigger BuildOutput()
- `src/pob/debug_calc_trigger.lua` - Debug script to investigate calculation
- `test_lua_calculator.py` - Test to verify Lua vs XML calculations

---

## Key Insight

**Don't fight HeadlessWrapper - work around it!**

We can build a powerful optimizer using:
1. XML parsing (read stats)
2. XML modification (change builds)
3. PoB app/API (recalculate when needed)

This is more reliable than trying to fix HeadlessWrapper's calculation engine.

---

**Status:** Investigation Complete | Ready for Decision on Approach

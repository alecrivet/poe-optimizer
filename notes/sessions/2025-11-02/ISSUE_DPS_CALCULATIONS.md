# Critical Issue: Inaccurate DPS Calculations

**Discovered:** 2024-11-02
**Status:** 🔴 Unresolved - Decision Needed
**Impact:** High - Affects core functionality

---

## The Problem

PoBCalculator severely underreports DPS for real builds:

```
Build 2 Example:
  Expected (PoB app):  3,100,000 DPS
  Actual (our calc):      42,403 DPS
  Error: 73x underreporting
```

## Root Cause

**HeadlessWrapper doesn't initialize skill list:**

```lua
build.skillsTab exists: ✅
build.skillsTab.skillList: ❌ nil
```

Skills from XML are never loaded into PoB's calculation engine, so it falls back to a default/minimal calculation.

## Evidence

1. **Skills ARE in the XML:**
   ```bash
   grep -i "<skill" examples/build2.xml | head -5
   # Shows: Cyclone of Tumult (6L), Ground Slam + General's Cry
   ```

2. **SkillList stays nil:**
   ```bash
   luajit debug_skills.lua build2.xml
   # Output: Number of skills: 0
   ```

3. **HeadlessWrapper comment:**
   ```lua
   -- Line 204-205 in HeadlessWrapper.lua:
   -- "You now have a build without a correct main skill selected,
   --  or any configuration options set. Good luck!"
   ```

## What Works

✅ Codec (encode/decode) - **Perfect**
✅ Basic stats extraction (Life, ES, Resists) - **Working**
✅ Round-trip encode/decode - **Working**
❌ DPS calculations - **Broken**
❌ Skill-specific calculations - **Broken**

## Attempted Fixes

- ✗ Increased OnFrame() calls to 30+
- ✗ Tried to manually call BuildSkillList()
- ✗ Tried to manually call Build()
- ✗ Examined SkillsTab.lua for initialization methods

**None successful.**

## Options Going Forward

### 1. Deep Dive into PoB Source (Hard)
- Investigate PoB's build initialization sequence
- Try to replicate full initialization in headless mode
- Time: Multiple sessions
- Success: Uncertain

### 2. Fork PoB for Better Headless Support (Very Hard)
- Modify HeadlessWrapper properly
- Contribute back to PoB project
- Time: Long
- Success: High (but time-consuming)

### 3. Use PoB Differently (Medium)
- Control PoB desktop app via automation
- Export data differently
- Time: Medium
- Success: Medium

### 4. Skip Accurate DPS (Pivot)
- Use relative DPS for optimization (comparing builds)
- Focus on other stats (Life, ES, Resists)
- Time: Low
- Success: High (but limited)

### 5. Alternative Calculation Source (Unknown)
- Find different tool/API for PoE calculations
- Build our own calculation engine (extremely hard)
- Time: ?
- Success: ?

## Questions to Answer

1. **How critical is accurate DPS for the optimizer?**
   - Can we optimize on relative DPS instead of absolute?
   - Are other stats (survivability) more important?

2. **What's our time budget?**
   - Worth spending days fixing PoB?
   - Or pivot to different approach?

3. **What's the MVP?**
   - Minimum viable build data needed for optimization?
   - Can we iterate and add accurate DPS later?

## Immediate Next Steps

**Decision Point:** Choose one of the options above before proceeding.

**Don't start coding until approach is decided.**

## Debug Scripts Available

For investigation (if continuing with PoB):
- `src/pob/debug_evaluator.lua` - Shows all stats PoB calculates
- `src/pob/debug_build_structure.lua` - Explores build object structure
- `src/pob/debug_skills.lua` - Checks skill loading
- `test_real_builds.py` - Tests with real builds

## Files to Review

- `PathOfBuilding/src/HeadlessWrapper.lua` (initialization)
- `PathOfBuilding/src/Classes/SkillsTab.lua` (skill management)
- `PathOfBuilding/src/Modules/Calcs.lua` (calculations)
- `examples/build2.xml` (real build with 3.1M DPS in PoB app)

---

**Bottom Line:** Codec works great, but DPS calculations are fundamentally broken due to HeadlessWrapper limitations. Need to decide on approach before continuing.

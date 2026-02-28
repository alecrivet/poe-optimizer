# Improved Headless Wrapper Plan

**Goal:** Create a proper headless wrapper that accurately recalculates modified builds without GUI automation.

**Why:**
- ✅ Cross-platform (no Windows-only PoB app needed)
- ✅ Fast (direct Lua calls, no GUI)
- ✅ Accurate (uses full PoB calculation engine)
- ✅ No external dependencies

---

## Root Cause of Current HeadlessWrapper Issues

### What's Missing

The current HeadlessWrapper (`PathOfBuilding/src/HeadlessWrapper.lua`) does this:

```lua
function loadBuildFromXML(xmlText, name)
    mainObject.main:SetMode("BUILD", false, name or "", xmlText)
    runCallback("OnFrame")
end
```

But `Build:Init()` (in `Modules/Build.lua`) does much more:

**Lines 581-583:** Create all tabs
```lua
self.treeTab = new("TreeTab", self)
self.skillsTab = new("SkillsTab", self)
self.calcsTab = new("CalcsTab", self)
```

**Lines 614-649:** Proper initialization sequence
1. Initialize tabs
2. Load XML sections (items, config, skills)
3. Load passive tree LAST (depends on items for jewel sockets)
4. Call `PostLoad()` on all tabs
5. **Call `BuildOutput()` to calculate stats** ← THE KEY!

**Current HeadlessWrapper skips steps 3-5!** That's why skills don't load properly.

---

## The Fix

### Option A: Enhanced Wrapper Function (Recommended)

Create a new function in our Lua code that replicates the full initialization:

```lua
-- src/pob/improved_evaluator.lua

function loadAndCalculateBuild(xmlText, mainSkillGroup)
    -- Load build
    loadBuildFromXML(xmlText, "EvaluatedBuild")

    -- Wait for tabs to initialize
    for i = 1, 3 do
        runCallback("OnFrame")
    end

    -- Ensure all tabs have PostLoad called
    if build.configTab and build.configTab.PostLoad then
        build.configTab:PostLoad()
    end
    if build.skillsTab and build.skillsTab.PostLoad then
        build.skillsTab:PostLoad()
    end
    if build.itemsTab and build.itemsTab.PostLoad then
        build.itemsTab:PostLoad()
    end
    if build.treeTab and build.treeTab.PostLoad then
        build.treeTab:PostLoad()
    end

    -- Select main skill if specified
    if mainSkillGroup and build.skillsTab.socketGroupList[mainSkillGroup] then
        build.mainSocketGroup = mainSkillGroup
    end

    -- Trigger calculations
    build.buildFlag = true
    if build.calcsTab and build.calcsTab.BuildOutput then
        build.calcsTab:BuildOutput()
    end

    -- One more frame to finalize
    runCallback("OnFrame")

    -- Return calculated stats
    if build.calcsTab and build.calcsTab.mainOutput then
        return build.calcsTab.mainOutput
    end

    return nil
end
```

### Option B: Patch HeadlessWrapper Directly

Modify `PathOfBuilding/src/HeadlessWrapper.lua` itself:

**Pros:** One place to fix
**Cons:** Modifies external submodule (violates CONTRIBUTING.md)

---

## Implementation Plan

### Phase 1: Investigation (1-2 hours)

1. **Test PostLoad requirement**
   ```lua
   -- Does calling PostLoad fix skill loading?
   loadBuildFromXML(xml)
   for i = 1, 3 do runCallback("OnFrame") end

   -- Try PostLoad calls
   if build.skillsTab.PostLoad then
       build.skillsTab:PostLoad()
   end

   -- Check if skillList is populated
   print("Skills loaded:", build.skillsTab.socketGroupList ~= nil)
   ```

2. **Test mainSocketGroup selection**
   ```lua
   -- Can we select which skill to calculate?
   build.mainSocketGroup = 3  -- Ground Slam group from build2
   build.buildFlag = true
   build.calcsTab:BuildOutput()

   -- Check if DPS changes
   print("DPS:", build.calcsTab.mainOutput.CombinedDPS)
   ```

3. **Identify minimal initialization sequence**
   - Which PostLoad calls are actually needed?
   - How many OnFrame calls?
   - What other flags/properties must be set?

### Phase 2: Implementation (2-3 hours)

1. Create `src/pob/improved_evaluator.lua`
2. Implement enhanced build loading
3. Add main skill selection
4. Add configuration options support (boss, etc.)

### Phase 3: Testing (1-2 hours)

1. Test with build2 (complex General's Cry)
2. Verify correct DPS (3.16M not 42K)
3. Test skill selection (can we calculate different skills?)
4. Test with modified builds

### Phase 4: Integration (1 hour)

1. Update `PoBCalculator` to use improved evaluator
2. Remove `automation.py` (no longer needed)
3. Update documentation
4. Add tests

---

## Expected Benefits

### Accuracy
- ✅ Correct DPS for complex builds (General's Cry, totems, minions)
- ✅ Can select which skill to calculate
- ✅ Can apply configuration options

### Performance
- ✅ Fast (~1-2 seconds per evaluation)
- ✅ No GUI overhead
- ✅ Can batch calculations

### Portability
- ✅ Works on Mac, Windows, Linux
- ✅ No external apps needed
- ✅ Just LuaJIT + our code

### Maintainability
- ✅ Our code stays in `src/pob/`
- ✅ Don't modify PathOfBuilding submodule
- ✅ Easy to update when PoB updates

---

## Risks & Mitigation

### Risk 1: PostLoad isn't enough
**Mitigation:** May need to dig deeper into tab initialization

### Risk 2: Some builds still calculate wrong
**Mitigation:** Add more debug output, compare with GUI calculations

### Risk 3: Configuration options complex
**Mitigation:** Start with default config, add options incrementally

---

## Quick Validation Test

**Before investing hours, let's test if PostLoad fixes skill loading:**

```lua
-- test_postload.lua
dofile("HeadlessWrapper.lua")

local xml = io.open("../../examples/build2.xml"):read("*all")
loadBuildFromXML(xml, "Test")

for i = 1, 5 do
    runCallback("OnFrame")
end

-- Try PostLoad
print("Before PostLoad:")
print("  skillsTab exists:", build.skillsTab ~= nil)
print("  socketGroupList exists:", build.skillsTab and build.skillsTab.socketGroupList ~= nil)
print("  socketGroupList count:", build.skillsTab and #build.skillsTab.socketGroupList or 0)

if build.skillsTab and build.skillsTab.PostLoad then
    print("\nCalling skillsTab:PostLoad()...")
    build.skillsTab:PostLoad()
end

if build.calcsTab and build.calcsTab.PostLoad then
    print("Calling calcsTab:PostLoad()...")
    build.calcsTab:PostLoad()
end

build.buildFlag = true
build.calcsTab:BuildOutput()

print("\nAfter PostLoad + BuildOutput:")
print("  CombinedDPS:", build.calcsTab.mainOutput.CombinedDPS)
print("  Life:", build.calcsTab.mainOutput.Life)
```

**If this shows correct DPS (3.16M), we're 90% done!**

---

## Next Steps

1. Run quick validation test
2. If successful → Implement improved evaluator
3. If not → Investigate what else is needed
4. Remove automation.py approach
5. Update documentation

---

**Time Estimate:** 4-8 hours total
**Confidence:** High (we have the source code and know what's missing)
**Payoff:** Proper cross-platform recalculation, no PoB app needed!

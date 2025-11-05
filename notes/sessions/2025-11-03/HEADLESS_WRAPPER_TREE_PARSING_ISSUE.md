# HeadlessWrapper Passive Tree Parsing Issue

**Date:** 2024-11-05
**Status:** ROOT CAUSE IDENTIFIED
**Severity:** CRITICAL - Blocks all passive tree optimization

---

## 🔴 The Problem

**Symptom:** Node removal doesn't change DPS/Life calculations in HeadlessWrapper.

**Root Cause:** HeadlessWrapper is NOT parsing the passive tree from XML.

## 📊 Evidence

### Test Results (debug_tree_parsing.py)

```
1. XML Analysis - Original:
   Nodes in XML: 127

2. HeadlessWrapper Analysis - Original:
   tree.allocNodes count: 0          ❌ Should be 127
   spec.allocNodes count: 1           ❌ Should be 127
   Sample from spec: 58833            (only sees starting class node)

3. Modified Build (removed 5 nodes):
   Nodes in XML: 122

4. HeadlessWrapper Analysis - Modified:
   tree.allocNodes count: 0           ❌ Still 0
   spec.allocNodes count: 1           ❌ Still 1

Diagnosis:
   ❌ PROBLEM: HeadlessWrapper sees SAME node count
      → HeadlessWrapper is NOT parsing tree changes from XML
      → This explains why stats don't change
```

### Code Flow Analysis

**HeadlessWrapper.lua:196**
```lua
function loadBuildFromXML(xmlText, name)
    mainObject.main:SetMode("BUILD", false, name or "", xmlText)
    runCallback("OnFrame")
end
```

**Build.lua:59-95 (Build:Init)**
```lua
function buildMode:Init(dbFileName, buildName, buildXML, convertBuild, importLink)
    -- ...
    if buildXML then
        if self:LoadDB(buildXML, "Unnamed build") then
            self:CloseBuild()
            return
        end
        self.modFlag = true
    end
    -- ...
end
```

**Build.lua:1820-1858 (LoadDB)**
```lua
function buildMode:LoadDB(xmlText, fileName)
    -- Parse the XML
    local dbXML, errMsg = common.xml.ParseXML(xmlText)

    -- Load Build section first
    for _, node in ipairs(dbXML[1]) do
        if type(node) == "table" and node.elem == "Build" then
            self:Load(node, self.dbFileName)
            break
        end
    end

    -- Store other sections for later processing
    for _, node in ipairs(dbXML[1]) do
        if type(node) == "table" then
            t_insert(self.xmlSectionList, node)
        end
    end
end
```

**Build.lua:614-649 (Continue Init after LoadDB)**
```lua
-- Load sections from xmlSectionList
-- Defer passive tree loading until after items
local deferredPassiveTrees = { }
for _, node in ipairs(self.xmlSectionList) do
    local saver = self.savers[node.elem] or self.legacyLoaders[node.elem]
    if saver then
        if saver == self.treeTab then
            t_insert(deferredPassiveTrees, node)
        else
            if saver:Load(node, self.dbFileName) then
                self:CloseBuild()
                return
            end
        end
    end
end

-- Load deferred passive trees
for _, node in ipairs(deferredPassiveTrees) do
    if self.treeTab:Load(node, self.dbFileName) then
        self:CloseBuild()
        return
    end
end

-- Call PostLoad on all savers
for _, saver in pairs(self.savers) do
    if saver.PostLoad then
        saver:PostLoad()
    end
end

-- Build calculation outputs
self.calcsTab:BuildOutput()
```

---

## 🔍 Analysis

### What SHOULD Happen

1. `loadBuildFromXML(xml, name)` called
2. `SetMode("BUILD", false, name, xml)` called
3. `OnFrame()` processes mode change
4. `Build:Init(false, name, xml)` called
5. `Build:LoadDB(xml)` parses XML, stores sections in `xmlSectionList`
6. Tabs are created (treeTab, skillsTab, etc.)
7. Each section loaded by calling `saver:Load(node)`
8. **Tree section loaded last** (deferred)
9. `PostLoad()` called on all savers
10. `BuildOutput()` called to calculate stats
11. **Result:** `build.tree.allocNodes` should have 127 nodes

### What's ACTUALLY Happening

Looking at the evidence:
- `tree.allocNodes` has 0 nodes
- `spec.allocNodes` has 1 node (just starting class node)

**Hypothesis:** The tree section is not being loaded properly from XML, OR the tree initialization is happening before the XML sections are processed.

### Possible Causes

1. **Timing Issue:** Tree needs more frames to fully initialize after Init()
2. **Spec Not Created:** `build.spec` might not be created properly in headless mode
3. **Tree Data Not Linked:** Tree might be loaded but not linked to `build.tree.allocNodes`
4. **Headless Stub:** Tree loading might be stubbed out for headless mode

---

## 🛠️ Investigation Steps

### Step 1: Check if Tree XML Section Exists ✅

The XML definitely has a `<Tree>` section with `<Spec nodes="...">`.

### Step 2: Check if treeTab:Load() is Called

Need to add debug output to see if:
- `treeTab:Load()` is called
- What data it receives
- If it successfully parses the tree spec

### Step 3: Check Spec Object Creation

Need to verify:
- Is `build.spec` created?
- Is it the right type?
- Does it have `allocNodes`?

### Step 4: Check Tree Object

Need to verify:
- Is `build.tree` created?
- Does it have the passive tree data?
- How is `tree.allocNodes` supposed to be populated?

---

## 💡 Potential Fixes

### Option A: Extended Initialization

Maybe HeadlessWrapper needs more OnFrame() callbacks to fully initialize.

**Test:**
```lua
-- evaluator.lua
for i = 1, 10 do  -- Try more frames
    runCallback("OnFrame")
end
```

### Option B: Manual Tree Loading

Maybe we need to explicitly load the tree in headless mode.

**Test:**
```lua
-- After loadBuildFromXML
if build.treeTab and build.treeTab.Load then
    -- Manually load tree section
    for _, node in ipairs(build.xmlSectionList) do
        if node.elem == "Tree" or node.elem == "Spec" then
            build.treeTab:Load(node, nil)
        end
    end
end
```

### Option C: Force Tree Rebuild

Maybe the tree needs to be explicitly rebuilt after loading.

**Test:**
```lua
-- After loadBuildFromXML
if build.treeTab and build.treeTab.Build then
    build.treeTab:Build()
end
```

### Option D: Check Spec Initialization

Maybe `build.spec` needs explicit initialization.

**Test:**
```lua
-- Check what build.spec is
print("build.spec type:", type(build.spec))
print("build.spec exists:", build.spec ~= nil)
if build.spec then
    print("build.spec.allocNodes count:", countNodes(build.spec.allocNodes))
end
```

---

## 🎯 Next Actions

1. **Create debug evaluator that checks tree loading steps:**
   - Does `treeTab:Load()` get called?
   - Does `build.spec` exist?
   - What's in `build.xmlSectionList`?
   - How many Tree/Spec sections are found?

2. **Test extended initialization:**
   - Try 10+ OnFrame() calls
   - Try explicit `BuildOutput()` call
   - Try calling tree rebuild methods

3. **If all else fails:**
   - Option 1: Fix HeadlessWrapper tree loading (deep dive into TreeTab.lua)
   - Option 2: Abandon ratio extrapolation, use pre-calculated XML stats only
   - Option 3: Build our own minimal tree parser

---

## 📝 Current Workaround

**For now:** Use pre-calculated XML stats only (no Lua calculation).

This works for:
- ✅ Comparing builds with pre-calculated stats
- ✅ Reading builds from PoB desktop

This DOESN'T work for:
- ❌ Evaluating modifications (modified XMLs have no pre-calculated stats)
- ❌ Optimization (need to evaluate many modifications)

---

## 🚨 Impact

**CRITICAL:** Without working tree parsing, we cannot:
- Test passive tree modifications
- Rank tree optimizations
- Use relative calculator for optimization
- Achieve the project's core goal

**This MUST be fixed for the project to proceed.**

---

## 📚 Related Files

- `debug_tree_parsing.py` - Test that reveals the issue
- `debug_node_removal.py` - Verifies XML modifications work
- `src/pob/evaluator_debug.lua` - Debug evaluator with tree info
- `PathOfBuilding/src/HeadlessWrapper.lua:196` - loadBuildFromXML
- `PathOfBuilding/src/Modules/Build.lua:59` - Build:Init
- `PathOfBuilding/src/Modules/Build.lua:1820` - Build:LoadDB
- `PathOfBuilding/src/Modules/Build.lua:614-649` - Section loading

---

**Status:** Investigation in progress
**Priority:** P0 - Blocking
**Assigned:** Next session continuation

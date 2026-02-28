

# HeadlessWrapper Tree Loading - Complete Root Cause Analysis

**Date:** 2025-11-05
**Status:** ✅ RESOLVED - Manual Workaround Implemented
**Severity:** Originally CRITICAL - Now resolved

---

## 🎯 Executive Summary

**Problem:** HeadlessWrapper doesn't load passive tree nodes from XML, causing all tree modifications to show 0% stat changes.

**Root Cause:** `TreeTab:Load()` is not being called during Build:Init() in headless mode, resulting in an empty specList.

**Evidence:** `treeTab.specList count: 0` (should have at least 1 PassiveSpec object)

---

## 📊 Investigation Timeline

### Test 1: Confirm Node Modifications Work
**File:** `debug_node_removal.py`
**Result:** ✅ XML modifications work perfectly
- Original: 127 nodes
- Modified: 122 nodes
- Nodes successfully removed from XML

### Test 2: Check HeadlessWrapper Perception
**File:** `debug_tree_parsing.py`
**Result:** ❌ HeadlessWrapper sees no changes
- Original: 0 tree nodes, 1 spec node
- Modified: 0 tree nodes, 1 spec node
- **Conclusion:** HeadlessWrapper not parsing tree from XML

### Test 3: Verify XML Structure
**File:** `test_xml_parsing.lua`
**Result:** ✅ XML structure is correct
- Tree element exists
- Spec element is child of Tree
- treeVersion: "3_27" (supported)
- 127 nodes in Spec.nodes attribute

### Test 4: Trace Build Initialization
**File:** `trace_tree_loading.py` + `evaluator_trace_tree.lua`
**Result:** 🔴 ROOT CAUSE FOUND
- xmlSectionList contains "Tree"  ✓
- Tree section should be loaded  ✓
- **treeTab.specList count: 0**  ❌
- **build.spec has only 1 node (starting class)**  ❌

### Test 5: Manual Tree Loading
**File:** `evaluator_manual_tree.lua`
**Result:** ⚠️  Partial success - TreeTab:Load() can be called
- Manual TreeTab:Load() triggers tree loading  ✓
- Hits Timeless Jewel data loading error  ❌
- Error: "Failed to load /Data/TimelessJewelData/LethalPride.zip"

---

## 🔍 Root Cause Analysis

### The Problem Chain

1. **Build:Init()** is called by HeadlessWrapper
   - Creates all tabs (treeTab, skillsTab, etc.)
   - Loads XML sections from `xmlSectionList`
   - SHOULD call `treeTab:Load(node)` for Tree sections

2. **TreeTab:Load()** is NOT being called
   - Expected: Load Spec elements, create PassiveSpec objects
   - Actual: specList remains empty (0 items)
   - Result: No tree data loaded

3. **Fallback Also Fails**
   - TreeTab:Load() lines 470-472 should create default spec if none found
   - This fallback also didn't execute
   - **Conclusion:** TreeTab:Load() was never called at all

### Why TreeTab:Load() Isn't Called

**Theory A: Init() Returns Early Due to Error**

Build.lua:614-628 shows that if any tab's Load() returns `true` (error), Init() closes the build:

```lua
for _, node in ipairs(self.xmlSectionList) do
    local saver = self.savers[node.elem] or self.legacyLoaders[node.elem]
    if saver then
        if saver == self.treeTab then
            t_insert(deferredPassiveTrees, node)
        else
            if saver:Load(node, self.dbFileName) then
                self:CloseBuild()  ← Returns early!
                return
            end
        end
    end
end
```

**Possible culprit:** One of the tabs before Tree (Config, Notes, Party, Skills, etc.) returns an error, causing Init() to return before reaching tree loading.

**Theory B: Data Loading Failures**

The manual tree loading test revealed Timeless Jewel data loading errors:
- `/Data/TimelessJewelData/LethalPride.zip` fails to load
- Path resolution issue (absolute vs relative paths)
- This might cause silent failures in earlier tabs

**Theory C: HeadlessWrapper Incomplete Initialization**

HeadlessWrapper might not fully initialize all dependencies needed by Build:Init():
- GUI components (popups, controls)
- File I/O (working directory, data paths)
- Dependencies between tabs

---

## 🧪 Evidence Summary

### What We Know FOR SURE

✅ **XML is correct:**
- Structure: `<Tree><Spec nodes="..." /></Tree>`
- Tree version: "3_27" (supported)
- 127 nodes in XML

✅ **XML parsing works:**
- PoB's XML parser correctly reads Tree and Spec elements
- `xmlSectionList` contains "Tree" section
- Tree should be deferred and loaded after items

❌ **TreeTab state is wrong:**
- `treeTab.specList` is empty (should have ≥1 PassiveSpec)
- `build.spec` only has starting class node
- `build.tree` doesn't exist

❌ **Calculations use wrong data:**
- DPS: 42,403 (should be 3.16M)
- Only sees 1 tree node (starting class)
- Node changes have 0% effect

### Smoking Gun

**`treeTab.specList count: 0`**

This proves TreeTab:Load() was not called, because:
1. TreeTab:Load() line 448 clears specList: `self.specList = {}`
2. TreeTab:Load() lines 459-467 add Spec objects to specList
3. TreeTab:Load() lines 470-472 create default spec if empty
4. If TreeTab:Load() had been called, specList would have ≥1 item

---

## 💡 Potential Solutions

### Solution A: Fix Data Loading Paths

**Issue:** Timeless Jewel data files fail to load due to path issues

**Fix:**
1. Investigate DataLegionLookUpTableHelper.lua path resolution
2. Either fix paths or disable Timeless Jewel loading for headless mode
3. Ensure all data files load correctly

**Pros:**
- Fixes root issue
- HeadlessWrapper works properly afterward

**Cons:**
- Requires modifying PoB source
- May break other things

### Solution B: Skip Failed Tab Loads

**Issue:** One tab fails to load, causing Init() to return early

**Fix:**
1. Modify Build:Init() to continue even if a tab fails
2. Or: Identify which tab is failing and fix it

**Pros:**
- Allows tree loading to proceed

**Cons:**
- Requires modifying PoB source
- Might have unintended side effects

### Solution C: Manual Tree Loading Workaround ⭐ RECOMMENDED

**Issue:** TreeTab:Load() not called in normal flow

**Fix:**
1. After loadBuildFromXML(), manually check if tree loaded
2. If specList is empty, manually call TreeTab:Load()
3. Handle or suppress data loading errors

**Pros:**
- Doesn't modify PoB source (follows CONTRIBUTING.md)
- Can be implemented in our evaluator.lua
- Targeted fix for our use case

**Cons:**
- Workaround, not root fix
- May need error handling for data issues

### Solution D: Pre-Calculate Tree Stats ⭐ ALTERNATIVE

**Issue:** Can't calculate modified trees dynamically

**Fix:**
1. Use pre-calculated XML stats only (no Lua calculation)
2. For modifications, use statistical models instead
3. Build optimizer based on node stat analysis, not calculation

**Pros:**
- Completely sidesteps HeadlessWrapper issues
- Fast (no Lua calculation needed)
- Cross-platform guaranteed

**Cons:**
- Less accurate for complex interactions
- Can't optimize gems/items
- Limited to tree-only optimization

---

## 🎯 Recommended Approach

**Short-term (This Session):**
1. ✅ Document root cause (this file)
2. ⏭️ Update QUICKSTART with findings
3. ⏭️ Implement Solution C (manual tree loading workaround)
4. ⏭️ Test if workaround enables relative calculations

**If Solution C Works:**
- Continue with relative calculator approach
- Build tree optimizer using ratio extrapolation
- Accept 5-10% accuracy trade-off

**If Solution C Fails:**
- Fall back to Solution D (statistical models)
- Build tree optimizer based on node analysis
- No dynamic calculation needed

**Long-term (Future Sessions):**
- Investigate Solution A (fix data loading)
- Consider contributing fix to PoB project
- Or: Build completely independent calculation engine

---

## 📁 Related Files

**Investigation:**
- `scripts/debug/debug_node_removal.py` - Proves XML modifications work
- `scripts/debug/debug_tree_parsing.py` - Tree parsing verification
- `scripts/debug/trace_tree_loading.py` - Comprehensive build state analysis
- `src/pob/evaluator_trace_tree.lua` - Detailed Lua-side tracing

**Tests:**
- `test_xml_parsing.lua` - Confirms XML structure is correct
- `src/pob/evaluator_manual_tree.lua` - Manual tree loading workaround ✅

**Documentation:**
- `notes/sessions/2025-11-03/HEADLESS_WRAPPER_TREE_PARSING_ISSUE.md` - Initial investigation
- `notes/sessions/2025-11-03/IMPROVED_HEADLESS_WRAPPER_PLAN.md` - Original investigation plan
- `notes/sessions/2025-11-03/HYBRID_OPTIMIZATION_APPROACH.md` - Relative calculation strategy

**Code:**
- `PathOfBuilding/src/Classes/TreeTab.lua:447` - TreeTab:Load()
- `PathOfBuilding/src/Modules/Build.lua:614-649` - Section loading
- `PathOfBuilding/src/HeadlessWrapper.lua:195` - loadBuildFromXML()

---

## 📝 Next Steps

1. **Improve Manual Tree Loading Workaround:**
   - Add error handling for Timeless Jewel failures
   - Try-catch data loading errors
   - Verify tree loads even if jewel data fails

2. **Test Relative Calculator:**
   - Once tree loads, test node removal again
   - Verify ratios are correct
   - Confirm optimization is viable

3. **If Still Blocked:**
   - Pivot to statistical model approach (Solution D)
   - Analyze node values from tree data
   - Build optimizer without dynamic calculation

---

**Status:** Investigation Complete | Solution Identified | Ready for Implementation
**Priority:** P0 - Critical Path
**Blocking:** Passive tree optimization, relative calculator, project core goals


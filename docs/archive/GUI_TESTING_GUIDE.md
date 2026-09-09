# Desktop GUI Testing Guide

This guide helps you test the PyQt6 Desktop GUI for the PoE Build Optimizer.

## Prerequisites

1. **Display/Graphics Environment**
   - Windows, macOS, or Linux with X11/Wayland
   - Cannot run in headless/SSH-only environments

2. **Python & Dependencies**
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows

   # Install GUI dependencies
   pip install PyQt6 PyQt6-WebEngine
   ```

3. **Test Build Code**
   - Have a Path of Building code ready to test
   - Recommend using `examples/build1` or your own build

---

## Launching the GUI

```bash
python run_gui.py
```

**Expected:** A window titled "Path of Exile Build Optimizer v0.4.0" opens

**If it fails:**
- Check error message for missing dependencies
- On Linux: May need `libxcb-xinerama0` - install with: `sudo apt-get install libxcb-xinerama0`
- On Linux: May need display server - check `echo $DISPLAY` returns something like `:0`

---

## Test Plan

### Test 1: GUI Launches Successfully

**Steps:**
1. Run `python run_gui.py`
2. Verify window opens

**Expected Results:**
- ✅ Window opens with title "Path of Exile Build Optimizer v0.4.0"
- ✅ Window is approximately 1400x900 pixels
- ✅ Left panel (input/config) and right panel (results) are visible
- ✅ All UI elements render correctly

**Known Issues:**
- None yet

---

### Test 2: PoB Code Input

**Steps:**
1. Copy a PoB build code (from examples/build1 or PoB)
2. Click "Paste from Clipboard" button
3. Verify code appears in input text area

**Expected Results:**
- ✅ Text area is populated with PoB code
- ✅ Code starts with "eN" (base64 encoding)
- ✅ No errors displayed

**Alternative:**
- Manually paste code into text area with Ctrl+V

**Common Issues:**
- Empty clipboard → Button does nothing (expected)
- Invalid characters → Will error on next step (load build)

---

### Test 3: Load Build

**Steps:**
1. Paste PoB code (Test 2)
2. Click "Load Build" button
3. Wait for processing (1-3 seconds)

**Expected Results:**
- ✅ "Build Information" panel populates with:
  - Character Level (e.g., "90")
  - Class (e.g., "Ranger")
  - Ascendancy (e.g., "Deadeye")
  - Passive Points (e.g., "112")
  - Mastery Effects (e.g., "3")
  - Total DPS (e.g., "1,250,000")
  - Life (e.g., "5,200")
  - Energy Shield (e.g., "0")
  - Mana (e.g., "842")
- ✅ "Start Optimization" button becomes enabled (green)
- ✅ Progress label shows "Build loaded successfully"
- ✅ Results table "Original" column populates with stats
- ✅ Success dialog appears: "Build loaded successfully!"

**Common Issues:**

**Issue:** "Invalid base64 encoding"
- **Cause:** PoB code is corrupted or incomplete
- **Fix:** Re-copy code from Path of Building

**Issue:** "Failed to load build: XML parse error"
- **Cause:** Build uses unsupported features or PoB version mismatch
- **Fix:** Try a simpler build first

**Issue:** Button doesn't enable
- **Cause:** Error during loading (check console for traceback)
- **Fix:** Check logs, verify PathOfBuilding submodule is initialized

---

### Test 4: Optimizer Configuration

**Steps:**
1. Test Algorithm Selector:
   - Select "Greedy (Fast)"
   - Verify greedy settings appear (Max Iterations)
   - Select "Genetic (Thorough)"
   - Verify genetic settings appear (Population, Generations)

2. Test Objective Selector:
   - Select "DPS"
   - Select "Life"
   - Select "EHP"
   - Select "Balanced"

3. Test Parameter Controls:
   - **Greedy:** Change "Max Iterations" (default 50)
   - **Genetic:** Change "Population" (default 30)
   - **Genetic:** Change "Generations" (default 50)
   - Toggle "Optimize Masteries" checkbox

**Expected Results:**
- ✅ Greedy settings show/hide when algorithm changes
- ✅ Genetic settings show/hide when algorithm changes
- ✅ Spin boxes accept values in valid ranges:
  - Max Iterations: 10-500
  - Population: 10-100
  - Generations: 10-200
- ✅ Checkbox toggles correctly

---

### Test 5: Run Greedy Optimization

**Steps:**
1. Load a build (Test 3)
2. Select "Greedy (Fast)" algorithm
3. Select "DPS" objective
4. Set "Max Iterations" to 20 (for faster test)
5. Check "Optimize Masteries"
6. Click "Start Optimization"

**Expected Results:**
- ✅ "Start Optimization" button disables (becomes gray)
- ✅ "Load Build" button disables
- ✅ Progress bar starts filling (0% → 100%)
- ✅ Progress label shows: "Optimization in progress..."
- ✅ UI remains responsive (can resize window, switch tabs)
- ✅ **After 30-60 seconds:**
  - Progress bar reaches 100%
  - Progress label: "Optimization complete!"
  - Success dialog: "Optimization completed successfully!"
  - Buttons re-enable
  - "Optimized Build Output" populates with new PoB code
  - Results table "Optimized" column populates
  - Improvement summary shows (e.g., "DPS: +5.3%")

**Performance:**
- 20 iterations: ~30-60 seconds
- 50 iterations: ~2-3 minutes

**Common Issues:**

**Issue:** Optimization never completes
- **Cause:** Infinite loop or hung process
- **Fix:** Close window, check console for errors, report bug

**Issue:** "Optimization failed: [error]"
- **Cause:** Backend error (tree graph, relative calculator, etc.)
- **Fix:** Check error message, verify dependencies, report bug

**Issue:** Progress bar doesn't update
- **Cause:** Progress signals not working (greedy doesn't emit progress currently)
- **Expected:** Progress bar may stay at 0% until completion (this is a known limitation for greedy algorithm)

---

### Test 6: Run Genetic Optimization

**Steps:**
1. Load a build (Test 3)
2. Select "Genetic (Thorough)" algorithm
3. Select "DPS" objective
4. Set "Population" to 15 (smaller for faster test)
5. Set "Generations" to 20 (smaller for faster test)
6. Check "Optimize Masteries"
7. Click "Start Optimization"
8. Switch to "Evolution" tab to watch progress

**Expected Results:**
- ✅ Same as Test 5, plus:
- ✅ Progress bar updates with each generation (5%, 10%, 15%, ...)
- ✅ Progress label shows generation progress:
  - "Generation 1: Best +2.5%, Avg +1.2%"
  - "Generation 5: Best +4.8%, Avg +3.5%"
  - etc.
- ✅ Evolution tab shows generation-by-generation log:
  ```
  Gen 1: Best = +2.50%, Avg = +1.20%
  Gen 2: Best = +3.10%, Avg = +2.10%
  Gen 3: Best = +3.80%, Avg = +2.60%
  ...
  ```

**Performance:**
- 15 pop × 20 gen: ~3-5 minutes
- 30 pop × 50 gen: ~15-20 minutes

**Common Issues:**

**Issue:** Progress doesn't update
- **Cause:** Background thread signals not connecting
- **Fix:** Check console for errors, restart application

**Issue:** Evolution tab is empty
- **Cause:** Text append not working or thread not emitting
- **Fix:** Check console, verify genetic optimizer is running

---

### Test 7: Results Comparison

**Steps:**
1. Complete optimization (Test 5 or 6)
2. Switch to "Results" tab
3. Review stats table

**Expected Results:**
- ✅ Table shows 10 rows of stats:
  - DPS (Original vs Optimized)
  - Life (Original vs Optimized)
  - EHP (Original vs Optimized)
  - Energy Shield
  - Mana
  - Armour
  - Evasion
  - Block %
  - Points Used
  - Level
- ✅ Optimized values differ from original
- ✅ Improvement summary shows positive changes (e.g., "+8.5% DPS")

**Validation:**
- Import both original and optimized builds to Path of Building
- Verify stats match (within ~5-10% due to relative calculator)

---

### Test 8: Copy Optimized Build

**Steps:**
1. Complete optimization (Test 5 or 6)
2. Click "Copy to Clipboard" button
3. Open Path of Building
4. Click "Import/Export Build"
5. Paste from clipboard
6. Click "Import"

**Expected Results:**
- ✅ Success dialog: "Optimized build code copied to clipboard!"
- ✅ PoB imports build without errors
- ✅ Passive tree shows different nodes than original
- ✅ Stats improved (approximately matching GUI results)

**Common Issues:**

**Issue:** PoB import fails
- **Cause:** Corrupted output code
- **Fix:** Re-run optimization, check for XML errors

**Issue:** Stats don't match GUI
- **Cause:** Relative calculator accuracy (~5-10% error)
- **Expected:** Some variance is normal - use PoB as ground truth

---

### Test 9: Build Details Tab

**Steps:**
1. Load a build
2. Switch to "Build Details" tab
3. Review character info, gear, and gems

**Expected Results:**
- ✅ Character section shows:
  - Level and class
  - Ascendancy
- ⚠️ Gear section shows: "Equipment parsing coming soon..." (placeholder)
- ⚠️ Gems section shows: "Gem parsing coming soon..." (placeholder)

**Known Limitations:**
- Gear and gem parsing not yet implemented
- Will be added in future update

---

### Test 10: Passive Tree Tab

**Steps:**
1. Load a build
2. Switch to "Passive Tree" tab

**Expected Results:**
- ⚠️ Shows: "Passive Tree Visualization (Coming Soon)"
- This is a placeholder for future tree canvas

**Known Limitations:**
- Tree visualization not yet implemented
- Will be added next

---

### Test 11: UI Responsiveness

**Steps:**
1. During optimization (Test 5 or 6), try:
   - Resizing window
   - Switching tabs
   - Hovering over UI elements
   - Scrolling text areas

**Expected Results:**
- ✅ UI remains responsive during optimization
- ✅ Window can be resized
- ✅ Tabs switch instantly
- ✅ No freezing or lag

**Common Issues:**

**Issue:** UI freezes during optimization
- **Cause:** Optimization running in main thread (should be in background)
- **Fix:** Bug - report this, should never happen

---

### Test 12: Multiple Optimizations

**Steps:**
1. Complete optimization (Test 5)
2. Click "Start Optimization" again (without reloading)
3. Wait for completion

**Expected Results:**
- ✅ Second optimization runs on previously optimized build
- ✅ May find additional improvements (or none)
- ✅ Results update correctly

**Use Case:**
- Iterative refinement: Greedy → Genetic → Greedy again

---

### Test 13: Algorithm Comparison

**Steps:**
1. Load a build
2. Run greedy optimization (20 iterations)
3. Note the DPS improvement
4. Click "Load Build" again (resets to original)
5. Run genetic optimization (15 pop, 20 gen)
6. Compare results

**Expected Results:**
- ✅ Genetic should find ≥ greedy improvement (usually 1-3% better)
- ✅ Genetic takes longer (~5× slower)

**Example:**
- Greedy: +5.3% DPS in 1 minute
- Genetic: +7.1% DPS in 5 minutes

---

### Test 14: Error Handling

**Test 14a: Empty Input**
1. Click "Load Build" without pasting code

**Expected:** Warning dialog: "Please paste a PoB code first"

**Test 14b: Invalid Code**
1. Paste random text (e.g., "hello world")
2. Click "Load Build"

**Expected:** Error dialog: "Failed to load build: Invalid base64 encoding"

**Test 14c: Optimize Without Loading**
1. Launch GUI
2. Click "Start Optimization" (button should be disabled)

**Expected:** Button is disabled, nothing happens

---

## Performance Benchmarks

| Configuration | Expected Runtime | Memory Usage |
|---------------|------------------|--------------|
| Greedy 20 iter | 30-60 sec | ~100 MB |
| Greedy 50 iter | 2-3 min | ~100 MB |
| Genetic 15/20 | 3-5 min | ~150 MB |
| Genetic 30/50 | 15-20 min | ~200 MB |

---

## Known Issues & Limitations

### Not Yet Implemented:
1. ✅ **Passive Tree Visualization** - Placeholder only
2. ✅ **Animated GA Visualization** - Placeholder only
3. ✅ **Gear Parsing** - Shows "coming soon"
4. ✅ **Gem Parsing** - Shows "coming soon"
5. ✅ **"Open in PoB" button** - Not functional yet

### Known Bugs:
1. **Greedy progress bar** - Doesn't update during optimization (stays at 0%)
   - Reason: Greedy optimizer doesn't emit progress signals
   - Workaround: Progress bar jumps to 100% when complete

2. **Relative calculator accuracy** - Results may vary from PoB by 5-10%
   - Reason: Approximate calculations for speed
   - Workaround: Always verify in PoB

### Platform-Specific Issues:

**Linux:**
- May need: `sudo apt-get install libxcb-xinerama0 libxcb-cursor0`
- X11 required (Wayland may have issues)

**macOS:**
- PyQt6 should work out of the box
- May need Rosetta on M1/M2 (arm64)

**Windows:**
- Should work without issues
- May need Visual C++ Redistributable

---

## Bug Reporting

If you find a bug:

1. **Check console output:**
   ```bash
   python run_gui.py 2>&1 | tee gui_log.txt
   ```

2. **Gather information:**
   - OS and version
   - Python version: `python --version`
   - PyQt6 version: `pip show PyQt6`
   - PoB code that caused issue
   - Steps to reproduce
   - Console output / error messages

3. **Report on GitHub:**
   - Open issue: https://github.com/alecrivet/poe-optimizer/issues
   - Include all information from step 2
   - Attach `gui_log.txt` if available

---

## Advanced Testing

### Test with Various Builds:

1. **Simple melee build** (few nodes, no conversion)
2. **Complex spell build** (many auras, conversion chains)
3. **Minion build** (may have accuracy issues)
4. **Low-life build** (ES, reservations)
5. **Block build** (test extended objectives)

### Stress Testing:

1. **Maximum iterations:** Greedy 500 iterations
2. **Large population:** Genetic 100 pop × 100 gen
3. **Multiple tabs open:** Switch rapidly during optimization
4. **Rapid clicking:** Click "Start Optimization" rapidly (should be prevented)

### Integration Testing:

1. **Greedy → Genetic pipeline:**
   - Run greedy first
   - Copy result
   - Paste as new input
   - Run genetic

2. **Objective comparison:**
   - Run same build with DPS, Life, EHP, Balanced
   - Compare trade-offs

---

## Success Criteria

✅ **Minimum Viable Product (MVP):**
- GUI launches without errors
- Can load PoB builds
- Can run greedy optimization (2-3 min)
- Can run genetic optimization (15-20 min)
- Results display correctly
- Can copy optimized build to clipboard
- Improvements visible in Path of Building

✅ **Future Features:**
- Passive tree visualization
- Animated genetic algorithm
- Gear and gem parsing
- Better progress tracking for greedy

---

## Feedback

After testing, please provide feedback on:

1. **Usability:** Is the UI intuitive?
2. **Performance:** Are runtimes acceptable?
3. **Accuracy:** Do results match PoB?
4. **Features:** What's missing? What's most important?
5. **Bugs:** Any crashes or errors?

---

## Next Steps After Testing

Once you've tested the MVP:

1. **Report bugs:** Open GitHub issues
2. **Request features:** What would make it more useful?
3. **Test tree visualization:** Next major feature
4. **Try different builds:** Find edge cases

Happy testing! 🎮⚡

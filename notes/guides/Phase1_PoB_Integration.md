# Phase 1: PoB Integration & Interface
## Week 1 - Get Python Talking to Path of Building

### Overview
**Goal:** Create the bridge between Python and Path of Building's calculation engine. By the end of this phase, you'll be able to generate a build in Python, send it to PoB, and get accurate calculation results back.

**Time Estimate:** 5 days
**Priority:** Critical - Everything else depends on this

---

## Prerequisites

### Software Requirements
- Python 3.9+ installed
- Lua 5.1 or LuaJIT installed
- Git (already have PoB source)
- PathOfBuilding source (already in `/PathOfBuilding`)

### Key Files to Examine
- `PathOfBuilding/HeadlessWrapper.lua` - Already exists! Start here
- `PathOfBuilding/Launch.lua` - PoB initialization
- `PathOfBuilding/Modules/CalcDefence.lua` - Defense calculations
- `PathOfBuilding/Modules/CalcOffence.lua` - Damage calculations
- `PathOfBuilding/Export/` - Export format examples

---

## Day 1-2: Understand & Enhance PoB Headless Mode

### Tasks

#### 1. Examine Existing HeadlessWrapper
```bash
# Read the existing headless wrapper
cat PathOfBuilding/HeadlessWrapper.lua
```

**Claude Code Prompt:**
> "Read PathOfBuilding/HeadlessWrapper.lua and explain how it works. Does it already support loading builds from XML files? Can it output calculation results as JSON? What modifications do we need to make it work for our optimizer?"

#### 2. Test HeadlessWrapper with Sample Build
**Claude Code Prompt:**
> "Find or create a minimal valid PoB build XML file. Try running: `lua PathOfBuilding/HeadlessWrapper.lua test_build.xml` and document what happens. If it doesn't work, explain what's missing."

#### 3. Modify HeadlessWrapper for Our Needs
We need the wrapper to:
- Accept build XML file as command-line argument
- Load and initialize PoB's calculation engine
- Run full build calculations
- Output key stats as JSON: DPS, EHP, Life, ES, Resistances, Attributes
- Exit cleanly with appropriate error codes

**Claude Code Prompt:**
> "Modify PathOfBuilding/HeadlessWrapper.lua to accept a build XML file path as argument, run PoB calculations, and output results as JSON to stdout. Include these stats: totalDPS, combinedDPS, totalEHP, life, energyShield, fireRes, coldRes, lightningRes, chaosRes, strength, dexterity, intelligence. Handle errors gracefully."

**Expected Output Format:**
```json
{
  "success": true,
  "stats": {
    "dps": 5000000,
    "combinedDPS": 5500000,
    "ehp": 150000,
    "life": 5000,
    "energyShield": 0,
    "fireRes": 75,
    "coldRes": 75,
    "lightningRes": 75,
    "chaosRes": -60,
    "strength": 150,
    "dexterity": 80,
    "intelligence": 60
  }
}
```

---

## Day 2-3: Python Subprocess Wrapper

### Tasks

#### 1. Create Project Structure
```bash
mkdir -p src/pob tests examples
touch src/__init__.py
touch src/pob/__init__.py
```

#### 2. Implement PoBCalculator Class

**Claude Code Prompt:**
> "Create src/pob/caller.py with a PoBCalculator class. Requirements:
> - __init__ method that validates PathOfBuilding directory exists
> - evaluate_build(build_xml: str) method that:
>   1. Writes XML to a temporary file
>   2. Calls lua PathOfBuilding/HeadlessWrapper.lua via subprocess
>   3. Parses JSON output
>   4. Returns dict with all stats
>   5. Cleans up temp file
> - Include proper error handling for:
>   - Invalid XML
>   - PoB process timeout (30 seconds)
>   - JSON parsing errors
>   - File I/O errors
> - Add logging for debugging"

**File Location:** `src/pob/caller.py`

**Key Methods:**
- `__init__(pob_path="./PathOfBuilding")`
- `evaluate_build(build_xml: str) -> dict`
- `_validate_pob_installation() -> bool`

#### 3. Create Unit Tests

**Claude Code Prompt:**
> "Create tests/test_pob_caller.py with basic tests:
> 1. Test that PoBCalculator initializes correctly
> 2. Test with a minimal valid build (just a level 90 Duelist with Cyclone)
> 3. Test that invalid XML raises appropriate error
> 4. Test timeout handling with a mock that takes too long
> Use pytest as the test framework."

---

## Day 4: PoB Code Decoder/Encoder

PoB import codes are base64-encoded, zlib-compressed XML. We need to decode existing builds and encode our generated ones.

### Tasks

#### 1. Implement Decoder

**Claude Code Prompt:**
> "Create src/pob/codec.py with functions to decode and encode PoB import codes. Include:
> - decode_pob_code(code: str) -> str: Decode base64+zlib to XML
> - encode_pob_code(xml: str) -> str: Encode XML to base64+zlib
> - Handle URL encoding/decoding
> - Include error handling for malformed codes
> - Add docstrings with examples"

**File Location:** `src/pob/codec.py`

#### 2. Test with Real Builds

**Claude Code Prompt:**
> "Find 3 popular build codes from poe.ninja for different skills (Cyclone, Spectral Throw, Lightning Strike). Create tests/test_codec.py that:
> 1. Decodes each build successfully
> 2. Validates the XML is well-formed
> 3. Saves decoded XML to examples/ directory
> 4. Tests round-trip: decode -> encode -> decode produces identical XML"

**Save Examples:**
- `examples/cyclone_slayer.xml`
- `examples/spectral_throw_raider.xml`
- `examples/lightning_strike_champion.xml`

---

## Day 5: Integration Testing & Validation

### Tasks

#### 1. End-to-End Test with Real Builds

**Claude Code Prompt:**
> "Create tests/test_integration.py that:
> 1. Takes the 3 example builds from examples/
> 2. Uses PoBCalculator to evaluate each one
> 3. Compares results with what poe.ninja shows (within 5% tolerance)
> 4. Prints a comparison table showing:
>    - Build name
>    - Our calculated DPS vs expected DPS
>    - Our calculated Life vs expected Life
>    - Pass/Fail status
> 5. If any fail, help debug what's wrong"

#### 2. Performance Benchmarking

**Claude Code Prompt:**
> "Create tests/test_performance.py that measures:
> 1. Average time to evaluate a single build
> 2. Time to evaluate 10 builds sequentially
> 3. Memory usage during evaluation
> Target: <5 seconds per build evaluation
> Print results in a readable format"

#### 3. Create Documentation

**Claude Code Prompt:**
> "Create docs/phase1_integration.md documenting:
> 1. How the PoB integration works (architecture diagram in markdown)
> 2. How to use PoBCalculator with code examples
> 3. Common errors and troubleshooting steps
> 4. Performance characteristics
> 5. Limitations and known issues"

---

## Deliverables Checklist

- [ ] `PathOfBuilding/HeadlessWrapper.lua` - Modified to output JSON
- [ ] `src/pob/caller.py` - PoBCalculator class
- [ ] `src/pob/codec.py` - Encode/decode functions
- [ ] `tests/test_pob_caller.py` - Unit tests
- [ ] `tests/test_codec.py` - Codec tests
- [ ] `tests/test_integration.py` - Integration tests
- [ ] `tests/test_performance.py` - Performance tests
- [ ] `examples/` - 3+ real build XMLs
- [ ] Documentation complete

---

## Success Criteria

### Must Have ✅
1. Can decode any valid PoB code to XML
2. Can evaluate any valid build XML and get results in <5 seconds
3. Results match Path of Building desktop app (within 5%)
4. Error handling works for all edge cases
5. All tests pass

### Nice to Have 🎯
1. Evaluation time <2 seconds per build
2. Can process builds in parallel (multiple subprocesses)
3. Caching layer for repeated evaluations

---

## Common Issues & Solutions

### Issue: "lua: command not found"
**Solution:** Install Lua 5.1 or LuaJIT
```bash
# macOS
brew install lua@5.1

# Ubuntu
apt-get install lua5.1

# Windows
# Download from lua.org or use LuaForWindows
```

### Issue: "HeadlessWrapper.lua: module not found"
**Solution:** PoB modules have path dependencies. Run from PoB root directory:
```python
subprocess.run(
    ['lua', 'HeadlessWrapper.lua', temp_file],
    cwd='./PathOfBuilding'  # Important!
)
```

### Issue: Build evaluation returns zeros
**Solution:** Check that:
1. XML has all required sections (Build, Tree, Items, Skills)
2. Build has at least one active skill gem
3. Character level is set correctly
4. Passive tree has starting node allocated

### Issue: Process hangs
**Solution:** Always use timeout:
```python
subprocess.run(..., timeout=30)
```

---

## Next Steps

Once Phase 1 is complete:
1. **Verify everything works:** Run all tests and ensure 100% pass rate
2. **Document any issues:** Note any limitations or bugs for later
3. **Move to Phase 2:** Begin implementing data access layer to read PoB's game data

**Phase 2 Preview:** We'll parse passive tree, items, and gems directly from PoB's Lua data files using the `lupa` library.

---

## Quick Reference Commands

```bash
# Test headless wrapper manually
lua PathOfBuilding/HeadlessWrapper.lua examples/cyclone_slayer.xml

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_pob_caller.py -v

# Check code coverage
pytest --cov=src tests/

# Performance benchmark
python -m tests.test_performance
```

---

## Resources

- **PoB GitHub:** https://github.com/PathOfBuildingCommunity/PathOfBuilding
- **PoB Discord:** Join for technical questions about PoB internals
- **poe.ninja:** https://poe.ninja/builds - Source for real build examples
- **Lua 5.1 Reference:** https://www.lua.org/manual/5.1/

---

**Ready to start?** Begin with Day 1, Task 1: Examining the HeadlessWrapper!

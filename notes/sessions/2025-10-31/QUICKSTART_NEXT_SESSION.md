# Quick Start Guide - Next Session

## 🎯 Where We Left Off

**Date:** 2024-10-31
**Phase:** Phase 1 (PoB Integration) - Day 3
**Status:** ✅ Days 1-3 completed, ready for Days 3-4

### What's Working Now
- ✅ Python can call PoB's calculation engine via Lua
- ✅ Can evaluate build XML and get accurate stats (DPS, Life, EHP, resistances, etc.)
- ✅ All 13 unit tests passing
- ✅ End-to-end integration demo working

## 🚀 Next Tasks: PoB Code Codec (Days 3-4)

**Goal:** Implement encoder/decoder for PoB import codes (base64-compressed XML)

### Tasks to Complete
1. **Create `src/pob/codec.py`** with:
   - `decode_pob_code(code: str) -> str` - Decode PoB import code to XML
   - `encode_pob_code(xml: str) -> str` - Encode XML to PoB import code
   - Handle URL encoding/decoding
   - Error handling for malformed codes

2. **Find real builds from poe.ninja:**
   - Get 3 popular builds (Cyclone, Spectral Throw, Lightning Strike, etc.)
   - Decode their import codes
   - Save XMLs to `examples/` directory

3. **Create `tests/test_codec.py`:**
   - Test decode with real PoB codes
   - Test encode produces valid codes
   - Test round-trip: decode → encode → decode produces identical XML
   - Test error handling

## 🔧 Quick Setup Commands

```bash
# Navigate to project
cd /Users/alec/Documents/Projects/poe-optimizer

# Activate virtual environment
source venv/bin/activate

# Verify PoB integration still works
python demo_pob_integration.py

# Run existing tests
pytest tests/test_pob_caller.py -v

# When ready, create new test file
touch tests/test_codec.py
```

## 📚 Key Context

### PoB Import Code Format
PoB import codes are:
1. XML string
2. Compressed with zlib
3. Encoded as base64
4. URL-encoded (optional, for sharing in URLs)

Example decode flow:
```python
import base64
import zlib
from urllib.parse import unquote

def decode_pob_code(code):
    code = unquote(code)  # URL decode if needed
    compressed = base64.b64decode(code)
    xml = zlib.decompress(compressed).decode('utf-8')
    return xml
```

Example encode flow is the reverse.

### Where to Find Real Builds
- **poe.ninja:** https://poe.ninja/builds
  - Click on popular builds
  - Look for PoB import link/code
  - Usually in format: `https://pobb.in/XXXXXX` or raw code starting with `eN`

### File Locations
- **Existing code:** `src/pob/caller.py`, `src/pob/evaluator.lua`
- **Tests:** `tests/test_pob_caller.py` (reference for test structure)
- **Phase guide:** `notes/guides/Phase1_PoB_Integration.md` (lines 127-159)
- **Session notes:** `notes/sessions/2024-10-31/session2.md`

## 💡 Important Notes

### Lua Environment (Already Set Up)
- LuaJIT installed via Homebrew
- lua-utf8 module installed via LuaRocks for Lua 5.1
- Evaluator script configured to load PoB runtime modules

**Don't reinstall these unless there's an error!**

### Testing Strategy
1. Start with `decode_pob_code()` - easier to test
2. Get real PoB codes from poe.ninja
3. Decode them and verify XML is valid
4. Use `PoBCalculator` to evaluate decoded builds
5. Then implement `encode_pob_code()`
6. Test round-trip encoding/decoding

### Claude Code Prompt (When Ready)
> "Create src/pob/codec.py with functions to decode and encode PoB import codes. PoB codes are base64-encoded, zlib-compressed XML. Include:
> - decode_pob_code(code: str) -> str: Decode base64+zlib to XML, handle URL encoding
> - encode_pob_code(xml: str) -> str: Encode XML to base64+zlib
> - Proper error handling for malformed codes
> - Docstrings with examples"

## 🎯 Success Criteria for Next Session

- [ ] Can decode any valid PoB import code to XML
- [ ] Can encode XML back to valid PoB import code
- [ ] Round-trip encoding works (decode → encode → decode = same XML)
- [ ] Have 3+ real build examples in `examples/` directory
- [ ] All tests passing (codec + existing tests)

## 🐛 Known Issues / Gotcas

### Issue: PoB prints debug output to stdout
**Already handled in `PoBCalculator.evaluate_build()`** - filters JSON from debug messages

### Issue: Builds take 1-2 seconds to evaluate
**Normal** - PoB loads passive tree data on first evaluation. This is fine for now.

### Issue: Some builds might fail evaluation
**Expected** - If build uses items/mechanics PoB doesn't support, it may error. Document these as known limitations.

## 📖 Reference Links

- **Phase 1 Guide:** Day 3-4 section (PoB Code Decoder/Encoder)
- **PoB Import Code Format:** Base64(zlib(XML))
- **poe.ninja:** https://poe.ninja/builds
- **PoB Pastebin alternative:** https://pobb.in/

## 🎬 Quick Validation

Before starting, verify everything still works:

```bash
# Should see PoB integration demo output
python demo_pob_integration.py

# Should see 13 tests passing
pytest tests/test_pob_caller.py -v
```

If either fails, check:
1. Virtual environment is activated
2. LuaJIT is available: `luajit -v`
3. PathOfBuilding submodule is present: `ls PathOfBuilding/src/HeadlessWrapper.lua`

## 📝 Session Documentation Template

When done, update session notes:
1. Copy this file to `session3.md` (or next number)
2. Document what was accomplished
3. Note any new issues discovered
4. Update progress checklist
5. Commit with descriptive message

---

**Last Updated:** 2024-10-31
**Ready for:** Phase 1, Days 3-4 (PoB Codec Implementation)

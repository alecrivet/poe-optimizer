# Contributing to PoE Optimizer

## Repository Structure

### PathOfBuilding Submodule - **DO NOT MODIFY**

**IMPORTANT:** The `PathOfBuilding/` directory is a Git submodule pointing to the official Path of Building repository. **We must NEVER modify files in this directory.**

**Rules:**
- ❌ **NEVER** create files in `PathOfBuilding/`
- ❌ **NEVER** modify existing files in `PathOfBuilding/`
- ❌ **NEVER** commit changes to `PathOfBuilding/`
- ✅ **ONLY** read files from `PathOfBuilding/` for reference

**Why?**
- It's an external dependency we pull from GitHub
- We want to be able to update to newer PoB versions easily
- Our code should be completely separate from theirs

### Our Code - Where to Put Things

**Python Code:**
- `src/pob/` - Our Python wrappers for PoB
  - `caller.py` - PoBCalculator wrapper
  - `codec.py` - PoB import code encoder/decoder
  - `xml_parser.py` - Parse stats from PoB XML
  - `*.lua` - Our Lua scripts that call PoB (kept separate from PoB's code)

**Tests:**
- `tests/` - All test files
  - `test_pob_caller.py`
  - `test_codec.py`

**Examples:**
- `examples/` - Example builds, XMLs, etc.

**Documentation:**
- `notes/` - Session notes, guides, etc.

## PathOfBuilding Integration

We integrate with PoB by:
1. **Reading** their source files (HeadlessWrapper.lua, etc.)
2. **Running** LuaJIT from their `src/` directory as working directory
3. **Calling** our own Lua scripts (in `src/pob/`) which load their code
4. **Parsing** XML that PoB generates

We do NOT:
- Modify their files
- Add files to their directory
- Commit changes to the submodule

## Git Workflow

The PathOfBuilding submodule should:
- Point to a specific commit of the official PoB repo
- Only be updated intentionally when we want to upgrade PoB versions
- Never show local modifications

Check PathOfBuilding status:
```bash
git status PathOfBuilding/
# Should show: nothing to commit (clean)
# OR: ? PathOfBuilding (if not initialized yet)
```

If it shows modifications:
```bash
cd PathOfBuilding
git status  # Check what changed
git checkout .  # Discard any accidental changes
```

## Code Organization Principles

1. **Separation of Concerns:** Our code in `src/`, their code in `PathOfBuilding/`
2. **Minimal Coupling:** Only depend on PoB's public interfaces
3. **Upgrade Path:** Should be able to update PoB without breaking our code
4. **Independence:** Our code should work with any compatible PoB version

## Before Committing

Always check:
```bash
git status
```

Make sure NO files from `PathOfBuilding/` appear as modified or staged!

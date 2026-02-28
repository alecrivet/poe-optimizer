# Feature Backlog

Future enhancements and features for consideration in upcoming releases.

---

## v0.7 - Polish & Performance

### High Priority
- [ ] Comprehensive test coverage expansion
- [ ] Performance benchmarking and optimization
- [ ] Edge case handling and bug fixes
- [ ] CI/CD pipeline setup

### Medium Priority
- [ ] Shell completion (bash/zsh/fish)
- [ ] Configuration file support (`~/.poe-optimizer/config.json`)
- [ ] Progress bar improvements and ETA calculations

### Low Priority
- [ ] Verbose logging mode with debug output
- [ ] Build validation warnings (conflicting keystones, etc.)

---

## v0.8 - Advanced Features

### Account Import from PoE API
**Status:** Deferred from v0.7
**Estimated Effort:** 8-12 hours
**Priority:** Medium

Allow users to import builds directly from their PoE account instead of requiring PoB codes.

**Implementation:**
- Add `src/pob/account_importer.py` module
- HTTP client for GGG's character-window API
- Authentication via POESESSID cookie
- CLI command: `poe-optimizer import-account PlayerName#1234 --character "CharName"`

**API Endpoints:**
- `character-window/get-characters` - List account characters
- `character-window/get-passive-skills` - Fetch passive tree
- `character-window/get-items` - Fetch items and skills

**Considerations:**
- Requires handling private accounts (POESESSID)
- Error handling for 401/403/404 responses
- Rate limiting and retry logic
- Case sensitivity quirks in GGG API
- Multi-realm support (PC/Xbox/PS4/CN/TW)

**Benefits:**
- Convenient for users (no manual export)
- Auto-refresh builds from league
- Batch import multiple characters

**Drawbacks:**
- Fragile (API changes could break)
- Authentication complexity
- Additional HTTP dependency

**CLI Examples:**
```bash
# Public account
poe-optimizer import-account PlayerName#1234 --character "MyChar"

# Private account (requires POESESSID)
poe-optimizer import-account PlayerName#1234 \
  --character "MyChar" \
  --session "your-poesessid-cookie"

# List characters first
poe-optimizer list-characters PlayerName#1234

# Import and optimize in one step
poe-optimizer import-account PlayerName#1234 \
  --character "MyChar" | poe-optimizer optimize -
```

---

## v1.0 - Production Ready

### Item Optimization
- [ ] Equipment upgrade suggestions
- [ ] Rare item crafting targets
- [ ] Unique item recommendations
- [ ] Budget constraints

### Gem Optimization
- [ ] Gem link optimization
- [ ] Support gem selection
- [ ] Awakened gem upgrade paths
- [ ] Alternative quality suggestions

### Advanced Constraints
- [ ] Attribute requirement satisfaction
- [ ] Jewel socket allocation strategy
- [ ] Cluster jewel generation/optimization
- [ ] Anointment optimization

---

## Future Considerations

### Web Interface
- [ ] Browser-based GUI alternative
- [ ] Build sharing platform integration
- [ ] Visual passive tree editor
- [ ] Real-time optimization preview

### Community Features
- [ ] Build database/sharing
- [ ] Meta build analysis
- [ ] League starter recommendations
- [ ] Build archetype templates

### Machine Learning
- [ ] Learn from successful builds (poe.ninja)
- [ ] Predictive build recommendations
- [ ] Meta-game adaptation

---

## Declined / Won't Implement

None yet.

---

**Note:** This backlog is subject to change based on user feedback and project priorities.

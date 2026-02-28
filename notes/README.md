# Development Notes

This directory contains session notes, decisions, and references to help maintain context across development sessions.

## Directory Structure

```
notes/
├── README.md                    # This file
├── SESSION_TEMPLATE.md          # Template for daily sessions
├── guides/                      # Implementation guides
│   ├── POE_Build_Optimizer_Guide_v2.md  # Master guide
│   ├── Phase1_PoB_Integration.md
│   ├── Phase2_Data_Access.md
│   ├── Phase3_Build_Representation.md
│   ├── Phase4_Optimization_Algorithms.md
│   ├── Phase5_Polish_Testing.md
│   └── Phase6_Advanced_Features.md
├── sessions/                    # Daily session logs
│   └── YYYY-MM-DD/
│       ├── session.md           # Main session notes
│       ├── code-snippets.md     # Useful code from session
│       └── debug-log.md         # Debugging notes
├── references/                  # Long-term reference docs
│   ├── pob-api.md              # PoB API documentation
│   ├── lua-bridge.md           # Python-Lua integration notes
│   └── architecture.md         # System architecture notes
├── decisions/                   # Architecture decision records
│   ├── 001-use-pob-submodule.md
│   ├── 002-genetic-algorithm.md
│   └── ...
└── todos/                       # Todo lists and task tracking
    ├── phase1-tasks.md
    ├── phase2-tasks.md
    └── ...
```

## Usage

### Starting a New Session

1. Create a new session directory:
   ```bash
   mkdir -p notes/sessions/$(date +%Y-%m-%d)
   ```

2. Copy the template:
   ```bash
   cp notes/SESSION_TEMPLATE.md notes/sessions/$(date +%Y-%m-%d)/session.md
   ```

3. Fill in the session notes as you work

### Recording Decisions

When making an important architectural or implementation decision:

1. Create a new decision record in `decisions/`
2. Use format: `NNN-short-title.md`
3. Include: Context, Decision, Rationale, Consequences

Example:
```markdown
# Use PathOfBuilding as Git Submodule

**Date:** 2024-10-31
**Status:** Accepted

## Context
We need to use PoB's calculation engine while respecting their license...

## Decision
Add PathOfBuilding as a git submodule...

## Rationale
- Proper attribution
- Easy updates
- Clear separation

## Consequences
- Need to document submodule workflow
- Must pull submodule when cloning
```

### Adding References

Long-term documentation that doesn't fit in session notes:
- API documentation
- Integration guides
- Performance notes
- Common commands

### Managing Todos

Use `todos/` for tracking tasks across sessions:
- Phase-specific task lists
- Bug tracking
- Feature requests
- Investigation topics

## Tips

### Quick Navigation
```bash
# Go to today's session
cd notes/sessions/$(date +%Y-%m-%d)

# List all sessions
ls -1 notes/sessions/

# Search all notes
grep -r "search term" notes/
```

### Session Recovery
If you need to resume work after context loss:
1. Read most recent session notes
2. Check decisions made
3. Review last commands run
4. Look at "Next Session" tasks

### What to Document
- **Always document:**
  - Commands that worked
  - Failed attempts and why
  - Key decisions
  - Blockers encountered
  - Tests run and results

- **Don't document:**
  - Code that's already in version control
  - Obvious steps
  - Temporary experiments

## Integration with Git

Session notes are tracked in git to:
- Provide history of development
- Share context with collaborators
- Enable time-travel debugging

Commit notes at the end of each session:
```bash
git add notes/
git commit -m "docs: Session notes for $(date +%Y-%m-%d)"
```

## Context Compression Strategy

When sessions get long or context fills up:
1. Summarize completed work in session notes
2. Extract key decisions to decision records
3. Move useful code snippets to references
4. Archive old session directories

This keeps the most relevant information easily accessible.

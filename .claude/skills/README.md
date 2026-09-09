# Custom Claude Code Skills

This directory contains custom skills (commands) for common development workflows.

## Available Skills

### `/commit` - Smart Git Commits
Create conventional commit messages with proper formatting.

**Usage:**
```
/commit
```

**Features:**
- Analyzes staged changes and checks the submodule is untouched
- Ensures the README changelog covers the change
- Creates a conventional commit message (feat/fix/perf/docs/etc.)
- Uses the session's attribution trailer
- Never pushes unless asked

---

### `/doc` - Documentation
Document code, features, or update README files.

**Usage:**
```
/doc path/to/file.py
/doc feature "account import"
/doc update README
```

**Features:**
- Adds docstrings to functions/classes
- Creates feature documentation
- Updates README with current API
- Maintains consistent style

---

### `/test` - Run Tests
Run test suite with coverage analysis.

**Usage:**
```
/test
/test tests/test_jewel_registry.py
/test --coverage 80
```

**Features:**
- Runs pytest with coverage
- Analyzes failures
- Reports coverage gaps
- Suggests fixes

---

### `/pr` - Create Pull Request
Create a pull request with proper description.

**Usage:**
```
/pr
/pr "Add feature X"
```

**Features:**
- Analyzes branch changes
- Generates PR description
- Creates PR via GitHub CLI
- Returns PR URL

---

### `/review` - Code Review
Review recent changes for quality issues.

**Usage:**
```
/review
/review src/pob/jewel/
/review --staged
```

**Features:**
- Identifies bugs and security issues
- Checks performance problems
- Reviews style and best practices
- Provides actionable feedback

---

### `/summary` - Change Summary
Summarize changes in current branch or since last commit.

**Usage:**
```
/summary
/summary --since HEAD~5
/summary --branch feature/jewel-support
```

**Features:**
- Lists commits and file changes
- Categorizes changes by type
- Highlights breaking changes
- Shows line count statistics

---

### `/refactor` - Code Refactoring
Refactor code while maintaining functionality.

**Usage:**
```
/refactor path/to/file.py
/refactor --extract-method function_name
```

**Features:**
- Reduces complexity
- Removes duplication
- Improves naming
- Maintains behavior
- Runs tests to verify

---

### `/quick` - Quick Fixes
Fast fixes for common issues.

**Usage:**
```
/quick fix imports
/quick add docstrings
/quick type hints
/quick format
```

**Features:**
- Fixes import statements
- Adds missing docstrings
- Adds type annotations
- Fixes formatting
- Minimal, focused changes

---

### `/refresh` - Reload Context
Refresh Claude's memory after compaction or new session.

**Usage:**
```
/refresh
```

**Features:**
- Reads CLAUDE.md, docs/BACKLOG.md and active plans in docs/plans/
- Reviews git state and recent commits
- Runs the fast (no-PoB) tests
- Summarizes version, working tree, active plans, next step
- Use after `/compact` or when starting a new session

---

## How to Use

1. Type `/` in Claude Code to see available skills
2. Select a skill or type its name
3. Follow the prompts
4. Claude will execute the workflow

## Creating New Skills

Skills are JSON files with this structure:

```json
{
  "name": "skill-name",
  "description": "Short description",
  "instructions": "Detailed instructions for Claude",
  "match": {
    "type": "usage"
  }
}
```

Place new skills in `.claude/skills/` directory.

## Tips

- The conventions these skills follow live in `CLAUDE.md` and `docs/DEVELOPMENT.md`; the skills are thin prompts.
- Use `/refresh` after compaction or starting a new session
- Use `/commit` after every logical change
- Run `/test` before committing; the full suite spawns luajit workers and takes ~4 minutes
- Use `/review` (or the built-in `/code-review`) before creating PRs; carry open findings into `docs/BACKLOG.md`
- `/quick` for minor fixes, `/refactor` for major improvements
- `/summary` before PR creation

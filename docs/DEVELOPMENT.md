# Development Guide

How this project is developed, with Claude Code (or any coding agent) as the
primary implementer and a human directing the work. This replaces the
2025-era session-notes system (`notes/`) and the per-release planning docs
(now in `docs/archive/`).

## Principles

1. **Evidence before change.** Every plan states what was measured or read
   that motivates it. Performance claims in docs are reproduced numbers, not
   estimates (see the history in `docs/PERFORMANCE.md` for why: the previous
   docs claimed ~100 ms per evaluation while the real figure was 3-5 s, and the
   batch path had been returning results for the wrong candidate).
2. **Small, verified steps.** Change one thing, run the tests that cover it,
   move on. The full suite runs before a commit.
3. **Plans are files, not chat.** Anything larger than a bug fix gets a plan in
   `docs/plans/`. Plans are updated as work proceeds and archived when done, so
   a new session (or a fresh agent after context compaction) can pick up from
   the file alone.
4. **The submodule is read-only.** `PathOfBuilding/` is never modified. We
   drive it from our own Lua (`src/pob/*.lua`) and Python.
5. **The changelog is part of the change.** `README.md` `## Changelog` is
   updated before every push.

## Session lifecycle

### 1. Orient (every session, and after `/compact`)

```bash
git status && git log --oneline -10
cat CLAUDE.md
cat docs/BACKLOG.md
ls docs/plans/            # anything active?
```

The `/refresh` skill in `.claude/skills/` does this and summarises. Memories
recalled by the harness are hints about past state; verify anything that names
a file, flag or number before relying on it.

### 2. Plan

Copy `docs/plans/TEMPLATE.md` to `docs/plans/<yyyy-mm>-<slug>.md`. A plan has:

- **Goal** and the user-visible outcome.
- **Evidence**: measurements, file references, failing tests.
- **Design**: the approach, with alternatives considered and rejected.
- **Interface contracts**: exact signatures / protocol lines that other
  streams or later steps depend on. (This is what made the v0.8 five-stream
  parallel effort work; see `docs/archive/v0.8-parallel-tasks.md`.)
- **File ownership**: which files each stream or step may modify. Two agents
  never own the same file. Integration files (`tree_optimizer.py`,
  `genetic_optimizer.py`, `src/cli/commands/*.py`) are integrated serially
  after the streams finish.
- **Verification**: the tests and benchmark commands that prove it works.
- **Status log**: dated entries as work proceeds.

Skip the plan for one-file fixes; put the reasoning in the commit message.

### 3. Implement

- Work in the venv: `venv/bin/python3`, `venv/bin/pytest`.
- For the evaluation hot path, benchmark first (`docs/PERFORMANCE.md`,
  "Reproducing the numbers") and again after.
- Prefer extending the session protocol (`LOAD`/`SET`/`DELTA`) over adding
  new full-reload paths.
- Keep the legacy paths working until they are deliberately removed; tests
  cover both.

### 4. Parallel agents

Use parallel subagents (or `git worktree` per agent) only when the plan lists
independent streams with disjoint file ownership and explicit interface
contracts. Each stream:

- gets its own prompt containing the goal, contracts, owned files, and the
  test command for its files;
- must leave its tests green;
- reports back what it changed and any contract deviations.

The orchestrating session then integrates serially, runs the full suite, and
updates the plan's status log. Do not fan out for work that touches shared
files or whose design is still open.

### 5. Verify

```bash
venv/bin/pytest tests/ -q                 # full suite
venv/bin/pytest tests/test_worker_pool.py tests/test_incremental_optimizer.py -q   # hot path
venv/bin/python3 -m src.cli.main optimize tests/fixtures/builds/cyclone_slayer.xml --iterations 5
```

For the web UI, `scripts/ui_walkthrough.py` drives the page through a full
run in headless Chromium (Playwright; `venv/bin/playwright install chromium`
once) and saves screenshots. Look at them. Two of the three real bugs in
the first front-end build were only visible in a screenshot.

Tests needing luajit + the submodule carry the `needs_pob` skip marker. New
behaviour on the Lua side needs a protocol test in `tests/test_worker_pool.py`;
new optimizer behaviour needs a unit test that runs without PoB plus, where
practical, one end-to-end test.

### 6. Review and ship

- Run `/code-review` (or the `/review` skill) on the diff. Fix what is
  clearly right; put the rest in `docs/BACKLOG.md` under "Open review
  findings" with an ID so it can be referenced from commits.
- Update `README.md` changelog and, if user-facing, `docs/USER_GUIDE.md`.
- Conventional commit (`feat:`, `fix:`, `docs:`, `perf:`, `test:`,
  `refactor:`, `chore:`), subject under 72 characters, body says why.
- Push only when the user asks.
- When a plan is complete, move it to `docs/archive/` and add a one-line
  summary at the top saying what shipped and in which version.

## Skills and memory

`.claude/skills/` contains project slash commands (`/refresh`, `/commit`,
`/test`, `/review`, `/pr`, `/summary`, `/refactor`, `/quick`, `/doc`). They
are thin prompts; the real conventions live in this file and `CLAUDE.md`.

The harness's auto-memory stores durable facts about the user and project.
Things the repo already records (structure, history, this guide) do not belong
there; non-obvious constraints and decisions do.

## Harness scripts: fail on EOF

Any ad-hoc script that reads a subprocess pipe in a loop must exit when
`readline()` returns empty. A loop that ignores EOF spins at 100% CPU
forever once the child dies (this happened twice on 2026-09-09 and cooked
the machine for an hour). `PoBWorker` handles this; one-off harnesses must
too.

## Code conventions

- Python 3.9+, `black` line length 100, `isort` profile black.
- Type hints on public functions. Dataclasses for records.
- Logging via `logging.getLogger(__name__)`; no `print` in library code.
- Errors: raise specific exceptions (`IncrementalCalculatorError`,
  `WorkerProtocolError`, `PoBCalculatorError`); do not swallow exceptions
  silently in library code (open finding S5-003 tracks the remaining cases).
- Lua evaluators: one JSON line out per request line in; all PoB console
  output goes to stderr.
- No emojis or Unicode symbols in code, CLI output, or docs unless requested.

## Repository layout

```
CLAUDE.md               agent entry point
README.md               user-facing overview + changelog
docs/                   current docs (see docs/README.md)
docs/plans/             active plans (+ TEMPLATE.md)
docs/archive/           completed plans, old reviews
notes/                  2025 session logs and phase guides (historical)
src/                    package (see docs/ARCHITECTURE.md)
tests/                  pytest suite; fixtures in tests/fixtures/builds
scripts/                benchmarks, demos, debug helpers
PathOfBuilding/         submodule, read-only
```

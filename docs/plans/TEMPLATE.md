# Plan: <short title>

**Status:** draft | active | blocked | done (vX.Y.Z)
**Owner:** <person or agent session>
**Created:** YYYY-MM-DD
**Last updated:** YYYY-MM-DD

## Goal

One paragraph: what changes for the user when this is done.

## Evidence

What was measured, read, or observed that motivates this. Link files with
line numbers, paste benchmark output, name failing tests.

## Design

The chosen approach. Alternatives considered and why they were rejected.

## Interface contracts

Exact signatures, protocol lines, data shapes that other steps or streams
depend on. Write them here before implementing so parallel work can proceed
against the contract.

```python
def example(build_xml: str) -> RelativeEvaluation: ...
```

## Work breakdown and file ownership

| Step / stream | Owns (may modify) | Depends on | Verification |
|---|---|---|---|
| A. ... | `src/pob/foo.py`, `tests/test_foo.py` | - | `venv/bin/pytest tests/test_foo.py` |
| B. ... | ... | A contract | ... |
| Integration | `src/optimizer/tree_optimizer.py`, `src/cli/commands/optimize.py` | A, B | full suite + CLI run |

Two streams never own the same file. Integration files are touched only in
the serial integration step.

## Verification

Commands that prove the goal is met (tests, benchmark, CLI run) and the
expected numbers.

## Status log

- YYYY-MM-DD: created.

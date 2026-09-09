# Documentation index

Start with `../CLAUDE.md` for the project overview and conventions.

## Current

| Doc | What it covers |
|---|---|
| `ARCHITECTURE.md` | Modules, data flow, the `LOAD`/`SET`/`DELTA` worker protocol, ratio extrapolation, constraints |
| `DEVELOPMENT.md` | The agentic workflow: orient, plan, implement, parallel streams, verify, review, ship |
| `PERFORMANCE.md` | Measured timings, what made v0.9 slow, remaining levers, how to benchmark |
| `BACKLOG.md` | Open work, known issues, open review findings |
| `USER_GUIDE.md` | Installing and using the CLI |
| `TROUBLESHOOTING.md` | Symptoms and fixes (worker pool section is current; older sections are Python-API era) |
| `CONFIGURATION.md` | Optimizer parameters (Python API; CLI flags are in `USER_GUIDE.md`) |
| `CONTRIBUTING.md` | Submodule rule and contribution basics |
| `GENETIC_ALGORITHM_EXPLAINED.md`, `MULTI_OBJECTIVE_EXPLAINED.md` | Concept explainers (algorithms, not current wiring) |
| `plans/` | Active plans; `plans/TEMPLATE.md` is the format |

## Archive (`archive/`)

Completed plans and reviews, kept for history. Do not use them to learn the
current state of the code.

| Doc | Outcome |
|---|---|
| `CLI_IMPLEMENTATION_PLAN.md` | shipped in v0.6 |
| `IMPLEMENTATION_SUMMARY.md` | jewel support plan, shipped in v0.6 |
| `JEWEL_SOCKET_OPTIMIZATION_PLAN.md` | shipped in v0.7/v0.8 |
| `v0.8-planning.md`, `v0.8-parallel-tasks.md` | five-stream parallel-agent plan, shipped in v0.8; still the best example of interface contracts + file ownership |
| `CODE_REVIEW_PLAN.md`, `CODE_REVIEW_FINDINGS.md` | v0.9 review; open findings are tracked in `BACKLOG.md` |
| `GUI_TESTING_GUIDE.md` | shelved PyQt GUI (v0.5) |

`../notes/` holds the 2025 session logs and phase guides from the first
weeks of the project (historical).

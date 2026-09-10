# Backlog

Open work, known issues, and open review findings. One list, kept current.
Shipped items move to the README changelog; completed plans move to
`docs/archive/`. Last refreshed: 2026-09-09 (v0.10.0).

## Next up

### Optimizer quality
- [ ] **Recovery-aware objective.** EHP ignores leech, regen and recovery,
      which is why keystones are now protected. A "sustain" term (PoB's
      LifeLeechGainRate / EnergyShieldLeechGainRate / regen outputs are in
      the worker stats already) folded into Balanced would let keystone
      changes be judged honestly.
- [ ] **Constraint objectives in the greedy loop.** `--min-life` / `--min-ehp`
      are parsed but not enforced during candidate selection; `dps` runs on the
      fixture trade -9% life for +42% DPS. Filter candidates whose extrapolated
      life/EHP fall below the floor (data is already in `DeltaEvaluation`).
- [ ] **Candidate pruning.** Skip removals whose `removed` count exceeds the
      point slack, and cache single-node delta results across iterations
      (most are unchanged after a swap elsewhere). See `docs/PERFORMANCE.md`.
- [ ] **Two-step additions.** Allow adding a notable two nodes away (PoB's
      `node.path` already handles pathing; the cost is two points) so swaps
      can reach notables behind a travel node.
- [ ] **Genetic operators on node sets.** Individuals are still XML strings
      mutated through `modify_passive_tree_nodes`; initial random variation
      produces many -100% individuals. Operate on node sets with connectivity
      repair instead.
- [ ] **Multi-objective via the session.** `MultiObjectiveOptimizer` is not
      wired to the worker pool or the CLI (`multi` algorithm uses the old
      calculator). Finding S2-008.

### Engine accuracy
- [ ] **Timeless jewel LUTs.** PoB prints `Missing LUT: Lethal Pride` (120x
      per load, still on v2.67.2). `readLUT` returns nothing for notables whose
      index is past `sizeNotable` in `NodeIndexMapping`; confirm whether the
      desktop app does the same for this build before treating it as a
      headless bug (finding S3-005).
- [ ] **Abyss timeless jewels in `DELTA`.** Socket-keyed conquests are only
      rebuilt on `SET`; a `DELTA` that changes Zorath's socket-to-start path is
      approximate until committed. Fine for greedy (commits each move); worth
      a `SET`-based re-check of the winner if this ever matters.
- [ ] **Timeless socket recommendations** (`timeless_value.py`) do not cover
      Abyss jewels (no radius LUT); `get_affected_nodes` returns empty for them.
- [ ] **Mastery database gaps.** `Mastery node 19750/6968/9471 not found in
      database` on the fixture; effect ids valid in PoB are flagged invalid.
      Parse masteries from PoB's `tree.lua` the way PoB does instead of regex.
- [ ] **Gem optimizer accuracy.** Headless absolute stats are off for
      accuracy/crit-dependent gems; `FullDPS` is 0 because imported builds
      have `includeInFullDPS="nil"`. Options: auto-flag skill groups, filter
      accuracy/crit gems, or move gem swaps onto the session protocol
      (`SET`-style item override). See `src/optimizer/gem_optimizer.py`.

### Import fidelity
- [ ] **Config rulebook maintenance.** `config_rules.py` transcribes
      poe.ninja's full rule list (92 rules, 2026-09). Not covered: the
      Vixen's Entrapment / Doom Blast overlap rules, Soul Mantle
      self-curse, "Disable EHP gain on block / suppress" (a PoB option
      we don't set), and Searing Exarch implicit charge sources (item text
      varies). Re-check the page each league and diff against RULES.
- [ ] **Charges the owner didn't assume.** On the fixture the rules enable
      power (charge on block) and endurance (charge on melee crit) that the
      build's owner left off; the UI toggle covers it, but a confidence tier
      ("always" vs "sometimes") shown as pre-unticked chips would be better.
- [ ] **Headless vs desktop gap.** The fixture evaluates to 4.14M DPS
      headless vs 3.55M in the XML's PlayerStats with the same config. Not
      explained by config presence (checked 2026-09-09). Candidates: stale
      PlayerStats in the export, FullDPS/skill selection, pantheon handling.

### Tooling
- [ ] CI: GitHub Actions running the non-PoB unit tests on push; a nightly
      job with the submodule + luajit for the integration tests.
- [ ] `poe-optimizer optimize --report`: write the per-iteration candidate
      table (top N with deltas) next to the output so results can be audited.
- [ ] Shell completion and a config file (`~/.poe-optimizer/config.json`).

## v1.0 themes (unchanged)

- Item upgrade suggestions and budget constraints.
- Gem link / support selection (partially started: `gem_optimizer.py`).
- Attribute requirement satisfaction, anointments, cluster jewel generation.

## Open review findings

From the v0.9 six-session review (`docs/archive/CODE_REVIEW_FINDINGS.md`).
Fixed since: S1-001, S1-003, S1-004, S1-005, S1-006 (worker reader rewritten
in v0.10), S2-001, S2-002, S2-004, S2-005, S2-006, S3-001, S3-002, S3-003,
S3-004, S3-006, S4-001, S4-003, S4-005, S5-001, S5-004, S5-005.

| ID | Sev | Summary | Notes |
|---|---|---|---|
| S2-003 | Med | ~400 lines duplicated between `tree_optimizer.py` and `genetic_optimizer.py` (mastery, jewel swaps, ToH, cluster) | extract a `CandidateGenerator` shared by both |
| S4-002 | Med | `BatchCalculator` / `RelativeCalculator` duplication | both are legacy now; consider deleting `BatchCalculator` once gem optimizer uses the session |
| S2-008 | Med | Multi-objective optimizer not integrated | see "Next up" |
| S5-003 | Med | Broad `except Exception: pass` in CLI | |
| S1-002 | Med | Regex parsing of PoB `tree.lua` is fragile | ties to mastery DB gaps above |
| S3-005 | Med | Timeless jewel data path resolution fails silently | see "Engine accuracy" |
| S4-004 | Med | Synergy detection O(n^2) with 3n evaluations per pair | unused by the incremental path |
| S2-007 | Med | O(n^2) Pareto dominance | only matters if S2-008 is done |
| S1-007, S4-006, S6-003 | Low | Module-level singletons (`_tree_parser`, `_mastery_db`, `_loader_cache`) | |
| S2-009 | Low | Optimizer files too large | do with S2-003 |
| S2-010, S6-001, S5-006 | Low | Emojis / Unicode in output | |
| S3-007 | Low | Cluster "Steiner tree" is a greedy heuristic | documented, no action |
| S4-007 | Low | Hard-coded keyword dicts in `build_context.py` | |
| S5-002 | Low | `sys.path.insert` hack in `cli/main.py` | |
| S6-002 | Low | `tree_diff` prints unconditionally | |

## Known limitations (user-facing)

- Optimises an existing tree; not validated from an empty tree.
- Items, gems, flasks and config are fixed during a run.
- Ascendancy choices are never changed.
- Jewel contents and timeless seeds are not optimised (socket placement is,
  opt-in).
- Results are PoB hover values for the headless engine; verify the final
  build in PoB desktop.

## Declined

- Desktop GUI (PyQt, v0.5): shelved; `src/gui/` kept for reference only.

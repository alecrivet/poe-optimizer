# Code Review Findings

This document tracks technical debt, concerns, and improvement opportunities discovered during the code review.

---

## Summary

| Severity | Count |
|----------|-------|
| High | 3 |
| Medium | 22 |
| Low | 17 |
| **Total** | **42** |

---

## Session 1: Core Architecture & Data Flow

**Files Reviewed:**
- `src/pob/codec.py`
- `src/pob/xml_parser.py`
- `src/pob/tree_parser.py`
- `src/pob/caller.py`
- `src/pob/worker_pool.py`

### Findings

#### [S1-001] BFS uses inefficient list.pop(0) - Medium

**File:** `src/pob/tree_parser.py:128-135`

**Description:** The BFS implementation uses `queue.pop(0)` which is O(n) for each pop operation. For large graphs (~1500 nodes), this adds unnecessary overhead.

**Current Code:**
```python
queue = [start_node]
while queue:
    current = queue.pop(0)  # O(n) operation
```

**Recommendation:** Use `collections.deque` for O(1) popleft:
```python
from collections import deque
queue = deque([start_node])
while queue:
    current = queue.popleft()  # O(1) operation
```

**Affected Methods:**
- `is_path_connected()`
- `get_shortest_path()`
- `shortest_path_length()`

---

#### [S1-002] Regex parsing of Lua is fragile - Medium

**File:** `src/pob/tree_parser.py:312-346`

**Description:** The tree parser uses regex to extract node data from PoB's Lua files. This approach is fragile and could break if PoB changes their format.

**Concerns:**
- No formal Lua parser, relies on string patterns
- Format changes in PoB updates could silently break parsing
- Complex regex patterns are hard to maintain

**Recommendation:** Consider using a proper Lua parser library (e.g., `lupa` or `slpp`) or caching parsed tree data as JSON.

---

#### [S1-003] Worker pool lock held during evaluation - High

**File:** `src/pob/worker_pool.py:156-202`

**Description:** The `PoBWorker.evaluate()` method holds its lock for the entire evaluation duration (up to 30s timeout). This prevents concurrent health checks and could cause contention.

**Current Code:**
```python
def evaluate(self, build_xml: str, timeout: float = 30.0) -> EvaluationResult:
    # ...
    with self.lock:  # Lock held for entire evaluation
        # ... 30+ seconds of work
```

**Impact:** While the pool uses round-robin, a slow evaluation blocks that worker entirely.

**Recommendation:** Use finer-grained locking or consider async I/O.

---

#### [S1-004] Dead workers not auto-restarted - Medium

**File:** `src/pob/worker_pool.py`

**Description:** When a worker dies (crashes, timeout), it's marked as dead but never restarted. Over time, the pool can degrade to fewer workers.

**Current Behavior:**
- Worker dies → `_is_dead = True`
- Pool skips dead workers in round-robin
- No mechanism to restart or replace dead workers

**Recommendation:** Add a health check loop that restarts dead workers, or restart on-demand when all workers are dead.

---

#### [S1-005] Type hint uses lowercase `any` - Low

**File:** `src/pob/xml_parser.py:53`

**Description:** Type hint uses `any` instead of `Any` from typing module.

**Current Code:**
```python
def get_build_summary(xml: str) -> Dict[str, any]:
```

**Recommendation:**
```python
from typing import Any
def get_build_summary(xml: str) -> Dict[str, Any]:
```

---

#### [S1-006] No timeout mechanism using select/poll - Medium

**File:** `src/pob/worker_pool.py:166-195`

**Description:** The worker read loop uses a busy-wait pattern checking elapsed time, rather than using `select()` or `poll()` for proper I/O timeout handling.

**Current Code:**
```python
start_time = time.time()
while time.time() - start_time < timeout:
    line = self.process.stdout.readline()  # Blocking!
    if not line:
        continue
```

**Impact:** `readline()` can block indefinitely if the worker hangs without producing output.

**Recommendation:** Use `select.select()` with timeout, or non-blocking I/O with `fcntl`.

---

#### [S1-007] Singleton pattern with module-level mutable state - Low

**File:** `src/pob/tree_parser.py:453-461`

**Description:** Uses module-level `_tree_parser` variable for singleton pattern. While functional, this can make testing harder and isn't thread-safe for initialization.

**Current Code:**
```python
_tree_parser: Optional[TreeParser] = None

def get_tree_parser() -> TreeParser:
    global _tree_parser
    if _tree_parser is None:
        _tree_parser = TreeParser()
    return _tree_parser
```

**Recommendation:** Consider using a proper singleton pattern with locking, or dependency injection for better testability.

---

## Session 2: Optimizer Core

**Files Reviewed:**
- `src/optimizer/tree_optimizer.py` (1134 lines)
- `src/optimizer/genetic_optimizer.py` (1543 lines)
- `src/optimizer/multi_objective_optimizer.py` (449 lines)
- `src/optimizer/extended_objectives.py` (330 lines)
- `src/optimizer/constraints.py` (356 lines)

### Findings

#### [S2-001] Constraints defined but never used - High

**File:** `src/optimizer/constraints.py` + `tree_optimizer.py` + `genetic_optimizer.py`

**Description:** The constraints module defines `PointBudgetConstraint`, `AttributeConstraint`, and `JewelSocketConstraint`, but these are never imported or used in either optimizer. Builds can violate point budgets or attribute requirements without any warning.

**Impact:** Optimizer may produce invalid builds that:
- Exceed available skill points for character level
- Fail to meet gem attribute requirements
- Break build functionality

**Recommendation:** Integrate constraint validation into optimizers:
- Add `constraints` parameter to `optimize()` methods
- Validate candidates before evaluation
- Either reject invalid candidates or apply repair strategies

---

#### [S2-002] Import references non-existent function - High

**File:** `src/optimizer/extended_objectives.py:15`

**Description:** The file imports `parse_pob_xml` from `xml_parser`, but that module only exports `parse_pob_stats`, `get_build_summary`, and `get_all_stats`.

**Current Code:**
```python
from ..pob.xml_parser import parse_pob_xml
```

**Impact:** Extended objectives will crash at runtime when used.

**Recommendation:** Change to correct import:
```python
from ..pob.xml_parser import parse_pob_stats
```

---

#### [S2-003] Massive code duplication between optimizers - Medium

**Files:** `src/optimizer/tree_optimizer.py` + `src/optimizer/genetic_optimizer.py`

**Description:** Both files contain nearly identical code for:
- Mastery optimization (`_optimize_masteries_for_tree`)
- Jewel swap generation (`_generate_jewel_swap_candidates` / `_mutate_jewel_swap`)
- Thread of Hope handling
- Cluster optimization
- Component initialization (tree graph, mastery db, socket discovery)

**Lines of duplication:** ~400+ lines

**Recommendation:** Extract shared functionality into:
- Base optimizer class
- Shared utility module (`optimizer/utils.py`)
- Component manager class

---

#### [S2-004] Individual class repeatedly parses XML - Medium

**File:** `src/optimizer/genetic_optimizer.py:140-152`

**Description:** `Individual.get_allocated_nodes()`, `get_mastery_effects()`, and `get_point_count()` all call `get_passive_tree_summary()` which parses XML each time.

**Current Code:**
```python
def get_allocated_nodes(self) -> Set[int]:
    summary = get_passive_tree_summary(self.xml)  # Parses XML every call
    return set(summary['allocated_nodes'])

def get_point_count(self) -> int:
    return len(self.get_allocated_nodes())  # Parses AGAIN
```

**Impact:** With population of 30 individuals and 50 generations, this can result in thousands of redundant XML parses.

**Recommendation:** Cache parsed summary on first access:
```python
@property
def _summary(self) -> Dict:
    if not hasattr(self, '_cached_summary'):
        self._cached_summary = get_passive_tree_summary(self.xml)
    return self._cached_summary
```

---

#### [S2-005] Magic numbers throughout optimizer code - Medium

**Files:** `src/optimizer/tree_optimizer.py`, `src/optimizer/genetic_optimizer.py`

**Description:** Hardcoded values without clear rationale:

| Location | Value | Purpose |
|----------|-------|---------|
| `tree_optimizer.py:680` | `[:20]` | Limit nodes to try removing |
| `tree_optimizer.py:709` | `[:20]` | Limit neighbors to try adding |
| `genetic_optimizer.py:822` | `1-5` | Random changes for variation |
| `genetic_optimizer.py:848` | `> 50` | Minimum tree size for removal |
| `genetic_optimizer.py:628-632` | `10, 0.1` | Convergence threshold |

**Recommendation:** Extract to named constants or configuration:
```python
MAX_CANDIDATES_PER_TYPE = 20
MIN_TREE_SIZE = 50
CONVERGENCE_WINDOW = 10
CONVERGENCE_THRESHOLD = 0.1
```

---

#### [S2-006] repair_constraint_violations() not implemented - Medium

**File:** `src/optimizer/constraints.py:329-355`

**Description:** Function exists but just logs a warning and returns `None`.

**Current Code:**
```python
def repair_constraint_violations(...) -> Optional[str]:
    # For now, just return None (repair not implemented)
    logger.warning("Constraint repair not yet implemented")
    return None
```

**Impact:** Even if constraints were integrated, there's no recovery mechanism for invalid candidates.

**Recommendation:** Either implement repair or remove the function to avoid confusion.

---

#### [S2-007] O(n²) Pareto dominance comparison - Medium

**File:** `src/optimizer/multi_objective_optimizer.py:252-262`

**Description:** All-pairs comparison for Pareto ranking.

**Current Code:**
```python
for i in range(n):
    for j in range(i + 1, n):
        if individuals[i].score.dominates(individuals[j].score):
            ...
```

**Impact:** With population of 100, this is 4,950 comparisons per generation. Not critical for current population sizes but will scale poorly.

**Note:** This is standard NSGA-II behavior, but worth noting for larger populations.

---

#### [S2-008] Multi-objective optimizer not integrated with main optimizers - Medium

**File:** `src/optimizer/multi_objective_optimizer.py`

**Description:** The `ParetoFrontier`, `calculate_pareto_ranks()`, and related functions are standalone. Neither `GreedyTreeOptimizer` nor `GeneticTreeOptimizer` use them for multi-objective optimization.

**Impact:** Users cannot perform true multi-objective optimization through the CLI - only single objective or naive "balanced" averaging.

**Recommendation:** Add multi-objective mode to `GeneticTreeOptimizer` that:
- Uses `ParetoIndividual` instead of `Individual`
- Selects based on rank + crowding distance
- Returns `ParetoFrontier` instead of single best

---

#### [S2-009] Very long files should be split - Low

**Files:**
- `src/optimizer/tree_optimizer.py` (1134 lines)
- `src/optimizer/genetic_optimizer.py` (1543 lines)

**Description:** Files exceed reasonable single-file size, making navigation difficult.

**Recommendation:** Split into:
- `optimizer/base.py` - Shared base class and utilities
- `optimizer/greedy.py` - Greedy optimizer
- `optimizer/genetic.py` - Genetic optimizer
- `optimizer/mutations.py` - Mutation operators
- `optimizer/jewel_ops.py` - Jewel-related operations

---

#### [S2-010] Emojis in format_pareto_frontier output - Low

**File:** `src/optimizer/multi_objective_optimizer.py:394-395`

**Description:** Uses emojis (🎯, 📊) in output formatting. May not render correctly in all terminals.

**Current Code:**
```python
lines.append(f"\n🎯 Extreme Points:")
...
lines.append(f"\n📊 All Solutions (sorted by DPS):")
```

**Recommendation:** Use plain text markers or make emoji optional via parameter.

---

## Session 3: Jewel System

**Files Reviewed:**
- `src/pob/jewel/base.py` (192 lines)
- `src/pob/jewel/registry.py`
- `src/pob/jewel/radius_calculator.py`
- `src/pob/jewel/socket_optimizer.py` (689 lines)
- `src/pob/jewel/timeless.py` (497 lines)
- `src/pob/jewel/timeless_data.py`
- `src/pob/jewel/thread_of_hope.py` (300 lines)
- `src/pob/jewel/cluster.py`
- `src/pob/jewel/cluster_optimizer.py` (481 lines)
- `src/pob/jewel/cluster_subgraph.py`

### Findings

#### [S3-001] Duplicate JewelSocket class definition - Medium

**Files:** `src/pob/jewel/base.py:43` + `src/pob/jewel/socket_optimizer.py:26`

**Description:** `JewelSocket` is defined in both files with different attributes:

**base.py version:**
```python
@dataclass
class JewelSocket:
    node_id: int
    position_x: float = 0.0
    position_y: float = 0.0
    radius: Optional[JewelRadius] = JewelRadius.LARGE
    is_cluster_socket: bool = False
    is_abyss_socket: bool = False
```

**socket_optimizer.py version:**
```python
@dataclass
class JewelSocket:
    node_id: int
    socket_type: SocketType
    is_allocated: bool = False
    is_outer_rim: bool = False
    distance_from_start: Optional[int] = None
    position: Optional[Tuple[float, float]] = None
```

**Impact:** Confusing which class to use; the two versions have different semantics.

**Recommendation:** Merge into single class or rename to distinguish (e.g., `JewelSocketInfo` vs `JewelSocketState`).

---

#### [S3-002] INNER_JEWEL_SOCKETS is placeholder - Low

**File:** `src/pob/jewel/base.py:137-139`

**Description:** The constant is declared but never populated:

```python
INNER_JEWEL_SOCKETS = {
    # There are many - will be populated from tree data
}
```

**Impact:** Dead code that could confuse developers or cause runtime issues if used.

**Recommendation:** Either populate with actual data or remove entirely.

---

#### [S3-003] Magic numbers in cluster socket classification - Medium

**File:** `src/pob/jewel/socket_optimizer.py:188-197`

**Description:** Cluster socket type classification uses hardcoded ID ranges:

```python
if node_id >= 65536:
    if node_id < 70000:
        return SocketType.LARGE_CLUSTER
    elif node_id < 75000:
        return SocketType.MEDIUM_CLUSTER
    else:
        return SocketType.SMALL_CLUSTER
```

**Impact:** These thresholds may not correctly identify cluster socket types; cluster node IDs use bit encoding (documented in cluster.py:46-55).

**Recommendation:** Use the actual bit encoding from `CLUSTER_NODE_MIN_ID` and the documented ID structure:
```python
# [index:4][size:2][large_socket:3][medium_socket:2][signal:1]
```

---

#### [S3-004] Test code left in production module - Low

**File:** `src/pob/jewel/timeless.py:486-497`

**Description:** Contains `if __name__ == "__main__":` test block:

```python
if __name__ == "__main__":
    # Test with build2.xml
    with open("examples/build2.xml", "r") as f:
        xml = f.read()

    jewels = parse_timeless_jewels(xml)
    print(f"Found {len(jewels)} timeless jewel(s):")
    ...
```

**Impact:** Not harmful but inconsistent with other modules; test code should live in tests/.

**Recommendation:** Move to a proper test file or remove.

---

#### [S3-005] Timeless jewel binary data path resolution - Medium

**File:** `src/pob/jewel/timeless_data.py`

**Description:** The binary data loader relies on finding PoB installation path which may fail in various environments. No graceful fallback if files are missing.

**Current behavior:** Returns empty transformations if data files not found, but doesn't warn loudly.

**Recommendation:** Add explicit warning/logging when timeless data cannot be loaded, or bundle essential data with package.

---

#### [S3-006] Inconsistent outer rim socket definitions - Medium

**Files:** `src/pob/jewel/base.py:132-134` + `src/pob/jewel/socket_optimizer.py:101-113`

**Description:** Two different sets of outer socket IDs:

**base.py:**
```python
OUTER_JEWEL_SOCKETS = {
    26725, 36634, 33989, 41263, 60735, 61834,
}
```

**socket_optimizer.py:**
```python
OUTER_RIM_SOCKETS = {
    2491, 6230, 7960, 12613, 26725, 33631, 36634,
    41263, 46519, 54127, 61419,
}
```

**Impact:** Only partial overlap (26725, 36634, 41263 appear in both). Could lead to incorrect socket classification.

**Recommendation:** Consolidate into single source of truth, ideally loaded from tree data.

---

#### [S3-007] cluster_subgraph uses Steiner tree but greedy approximation - Low

**File:** `src/pob/jewel/cluster_subgraph.py`

**Description:** The minimum allocation algorithm claims to find minimum Steiner tree but uses a greedy BFS approach, which is a heuristic. The optimal Steiner tree problem is NP-hard.

**Impact:** May not find truly minimal allocations in edge cases. For typical cluster sizes this is likely acceptable.

**Note:** This is documented in comments; no action needed unless proven problematic.

---

## Session 4: Mastery & Build Context

**Files Reviewed:**
- `src/pob/build_context.py` (874 lines)
- `src/pob/mastery_optimizer.py` (666 lines)
- `src/pob/mastery_synergy.py` (174 lines)
- `src/pob/modifier.py` (418 lines)
- `src/pob/batch_calculator.py` (274 lines)
- `src/pob/relative_calculator.py` (307 lines)

### Findings

#### [S4-001] Hardcoded tree version - Medium

**Files:** `src/pob/mastery_optimizer.py:547`, `src/pob/build_context.py:634`

**Description:** Both files hardcode the tree version:

```python
def load_mastery_database(pob_path: str = "./PathOfBuilding", tree_version: str = "3_27") -> MasteryDatabase:
    tree_file = Path(pob_path) / "src" / "TreeData" / tree_version / "tree.lua"
```

**Impact:** Won't adapt to new PoE versions; requires code changes every 3-4 months.

**Recommendation:** Detect latest tree version dynamically or read from config:
```python
def get_latest_tree_version(pob_path: str) -> str:
    tree_data = Path(pob_path) / "src" / "TreeData"
    versions = sorted([d.name for d in tree_data.iterdir() if d.is_dir()])
    return versions[-1] if versions else "3_27"
```

---

#### [S4-002] Code duplication between calculators - Medium

**Files:** `src/pob/batch_calculator.py` + `src/pob/relative_calculator.py`

**Description:** Both calculator classes have nearly identical code for:
- `evaluate_modification()` method structure
- Ratio calculations
- Percent change calculations
- `use_lua_fallback` logic

**Lines duplicated:** ~80 lines

**Current structure:**
```python
# batch_calculator.py
from .relative_calculator import RelativeEvaluation  # Uses the dataclass

class BatchCalculator:  # No inheritance
    def evaluate_modification(self, ...) -> RelativeEvaluation:
        # Nearly identical implementation

# relative_calculator.py
class RelativeCalculator:  # No inheritance
    def evaluate_modification(self, ...) -> RelativeEvaluation:
        # Nearly identical implementation
```

**Recommendation:** Extract common logic to base class or mixin:
```python
class BaseCalculator(ABC):
    def _calculate_ratios(self, baseline, modified) -> Tuple[float, float, float]:
        ...
    def _build_evaluation(self, ...) -> RelativeEvaluation:
        ...
```

---

#### [S4-003] Duplicate balanced objective weights - Low

**Files:** `src/pob/mastery_optimizer.py:392-397`, `src/pob/mastery_synergy.py:146-151`

**Description:** The "balanced" objective uses the same hardcoded weights in multiple places:

```python
# mastery_optimizer.py
elif objective == 'balanced':
    return (
        result.dps_change_percent * 0.4 +
        result.life_change_percent * 0.3 +
        result.ehp_change_percent * 0.3
    )

# mastery_synergy.py (identical code)
elif objective == 'balanced':
    return (
        result.dps_change_percent * 0.4 +
        result.life_change_percent * 0.3 +
        result.ehp_change_percent * 0.3
    )
```

**Recommendation:** Define once as constant or utility function:
```python
BALANCED_WEIGHTS = {'dps': 0.4, 'life': 0.3, 'ehp': 0.3}

def calculate_balanced_score(result) -> float:
    return sum(getattr(result, f'{k}_change_percent') * v for k, v in BALANCED_WEIGHTS.items())
```

---

#### [S4-004] Synergy detection is O(n²) with 3n evaluations per pair - Medium

**File:** `src/pob/mastery_synergy.py:51-136`

**Description:** `detect_synergies()` evaluates each mastery effect individually, then evaluates all pairs:

```python
# First: n individual evaluations
for node_id, effect_id in mastery_effects.items():
    modified_xml = modify_passive_tree_nodes(...)
    result = calculator.evaluate_modification(...)
    individual_scores[effect_id] = ...

# Then: C(n,2) = n*(n-1)/2 pair evaluations
for (eff1, eff2) in combinations(effect_ids, 2):
    combined_xml = modify_passive_tree_nodes(...)
    combined_result = calculator.evaluate_modification(...)
```

**Impact:** With 10 masteries: 10 + 45 = 55 evaluations (~5.5s with worker pool). With 20 masteries: 20 + 190 = 210 evaluations (~21s).

**Recommendation:** Add early exit or sampling strategy; batch individual evaluations.

---

#### [S4-005] No validation of mastery effect IDs - Medium

**File:** `src/pob/modifier.py:106-107`

**Description:** When adding mastery effects, there's no validation that the effect ID is valid for the given node:

```python
# 2. Add new mastery effects
mastery_effects.update(mastery_effects_to_add)  # No validation
```

**Impact:** Invalid effect IDs will be written to XML and may cause PoB errors or silent failures.

**Recommendation:** Validate against mastery database before applying:
```python
from .mastery_optimizer import get_mastery_database
db = get_mastery_database()
for node_id, effect_id in mastery_effects_to_add.items():
    valid_effects = {e.effect_id for e in db.get_available_effects(node_id)}
    if effect_id not in valid_effects:
        raise BuildModificationError(f"Invalid effect {effect_id} for mastery {node_id}")
```

---

#### [S4-006] Another singleton with module-level mutable state - Low

**File:** `src/pob/mastery_optimizer.py:655-665`

**Description:** Same pattern as S1-007:

```python
_mastery_db: Optional[MasteryDatabase] = None

def get_mastery_database(reload: bool = False) -> MasteryDatabase:
    global _mastery_db
    if _mastery_db is None or reload:
        _mastery_db = load_mastery_database()
    return _mastery_db
```

**Impact:** Not thread-safe; can cause issues in multi-threaded contexts.

**Recommendation:** Use thread-safe singleton or dependency injection.

---

#### [S4-007] Large keyword dictionaries should be externalized - Low

**File:** `src/pob/build_context.py:33-112`

**Description:** ~80 lines of hardcoded keyword dictionaries (KEYSTONE_NAMES, DAMAGE_TYPE_GEMS, ATTACK_GEMS, SPELL_GEMS, MECHANIC_GEMS, SKILL_DAMAGE_HINTS).

**Impact:** Difficult to update when new skills/keystones are added; mixes data with code.

**Recommendation:** Move to external YAML/JSON file:
```yaml
# data/build_keywords.yaml
keystones:
  "Resolute Technique": resolute_technique
  "Chaos Inoculation": ci
damage_type_gems:
  fire: ["Combustion", "Immolate", ...]
```

---

## Session 5: CLI & Integration

**Files Reviewed:**
- `src/cli/main.py` (101 lines)
- `src/cli/commands/optimize.py` (278 lines)
- `src/cli/commands/analyze.py` (116 lines)
- `src/cli/commands/jewels.py` (301 lines)
- `src/cli/commands/account.py` (277 lines)
- `src/cli/utils.py` (247 lines)
- `src/ggg/client.py` (270 lines)
- `src/ggg/converter.py` (425 lines)

### Findings

#### [S5-001] Version string duplicated - Low

**Files:** `src/cli/main.py:29`, `src/ggg/client.py:38`

**Description:** Version is hardcoded in multiple places:

```python
# main.py
VERSION = "0.9.0"

# client.py (in user agent)
user_agent: str = "poe-optimizer/0.9.0 (https://github.com/...)"
```

**Impact:** When version changes, must update in multiple files.

**Recommendation:** Use single source of truth (e.g., `__version__` in `__init__.py` or `pyproject.toml`).

---

#### [S5-002] sys.path manipulation in installed package - Low

**File:** `src/cli/main.py:22-24`

**Description:** Uses `sys.path.insert(0, ...)` to find imports:

```python
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

**Impact:** This is a workaround for improper package installation. Works but fragile.

**Recommendation:** Proper package installation should make this unnecessary. Consider using relative imports or proper entry points.

---

#### [S5-003] Broad exception catching hides errors - Medium

**Files:** Multiple files in CLI

**Description:** Many places catch broad `Exception` and continue silently:

```python
# jewels.py:100-101
except Exception as e:
    output.progress(f"Warning: Could not load tree data for analysis: {e}")

# optimize.py:146-148
except Exception:
    pass  # Jewel parsing is optional
```

**Impact:** Real errors may be silently swallowed. Debug difficulty increases.

**Recommendation:** Catch specific exceptions or at minimum log the full traceback in debug mode.

---

#### [S5-004] GGG client session never explicitly closed - Medium

**File:** `src/ggg/client.py:76-77`

**Description:** Creates a `requests.Session` but has no `close()` method or context manager:

```python
def __init__(...):
    ...
    self._session = requests.Session()  # Never closed
```

**Impact:** Resource leak in long-running processes; connections may not be properly released.

**Recommendation:** Add `close()` method and `__enter__/__exit__` for context manager:
```python
def close(self):
    self._session.close()

def __enter__(self):
    return self

def __exit__(self, *args):
    self.close()
```

---

#### [S5-005] TODO in production code - Low

**File:** `src/ggg/converter.py:218`

**Description:** Unfinished feature flagged with TODO:

```python
# TODO: Map jewel_data to socket assignments
```

**Impact:** Imported characters may not have jewel socket information.

**Recommendation:** Either implement or document the limitation clearly.

---

#### [S5-006] Unicode symbols may not render in all terminals - Low

**File:** `src/cli/utils.py:194-203`

**Description:** Uses Unicode checkmarks and symbols:

```python
def success(self, message: str):
    click.secho(f"✓ {message}", fg="green")

def error(self, message: str):
    click.secho(f"✗ {message}", fg="red", err=True)
```

**Impact:** May display as boxes or garbage in terminals without Unicode support.

**Recommendation:** Add option to use ASCII fallbacks (`[OK]`, `[ERROR]`, etc.).

---

## Session 6: Visualization & Utilities

**Files Reviewed:**
- `src/visualization/evolution_plot.py` (347 lines)
- `src/visualization/frontier_plot.py` (356 lines)
- `src/visualization/tree_diff.py` (305 lines)
- `src/pob/tree_positions.py` (379 lines)

### Findings

#### [S6-001] Emojis in tree_diff output - Low

**File:** `src/visualization/tree_diff.py:73-127`

**Description:** Uses emojis extensively in text output:

```python
report_lines.append("📊 Summary:")
...
report_lines.append("✅ NODES ADDED:")
...
report_lines.append("❌ NODES REMOVED:")
...
report_lines.append("🎯 MASTERY CHANGES:")
```

**Impact:** Same issue as S2-010 and S5-006 - may not render in all terminals.

**Recommendation:** Add `--ascii` flag or detect terminal capabilities.

---

#### [S6-002] tree_diff unconditionally prints to console - Low

**File:** `src/visualization/tree_diff.py:191`

**Description:** Always prints report to console in addition to file:

```python
with open(output_file, 'w') as f:
    f.write(report)
...
# Also print to console
print(report)  # Always prints
```

**Impact:** No way to suppress console output; pollutes logs in automated pipelines.

**Recommendation:** Add parameter to control console printing:
```python
def visualize_tree_diff(..., print_to_console: bool = True):
```

---

#### [S6-003] Another global cache singleton - Low

**File:** `src/pob/tree_positions.py:349`

**Description:** Same pattern as S1-007 and S4-006:

```python
_loader_cache: Dict[str, TreePositionLoader] = {}

def get_position_loader(tree_version: str = "3_27") -> TreePositionLoader:
    if tree_version not in _loader_cache:
        _loader_cache[tree_version] = TreePositionLoader(tree_version)
    return _loader_cache[tree_version]
```

**Impact:** Not thread-safe; testing difficulty.

**Note:** Lower priority since this is read-only cached data.

---

## Priority Matrix

| ID | Severity | Effort | Priority |
|----|----------|--------|----------|
| S2-002 | High | Low | 1 |
| S2-001 | High | Medium | 2 |
| S1-003 | High | Medium | 3 |
| S2-004 | Medium | Low | 4 |
| S2-005 | Medium | Low | 5 |
| S3-006 | Medium | Low | 6 |
| S3-001 | Medium | Low | 7 |
| S4-005 | Medium | Low | 8 |
| S1-004 | Medium | Medium | 9 |
| S4-001 | Medium | Low | 10 |
| S2-003 | Medium | High | 11 |
| S4-002 | Medium | Medium | 12 |
| S1-006 | Medium | Medium | 13 |
| S1-001 | Medium | Low | 14 |
| S2-006 | Medium | Medium | 15 |
| S2-007 | Medium | Medium | 16 |
| S3-003 | Medium | Medium | 17 |
| S3-005 | Medium | Medium | 18 |
| S4-004 | Medium | Medium | 19 |
| S2-008 | Medium | High | 20 |
| S1-002 | Medium | High | 21 |
| S2-009 | Low | High | 22 |
| S2-010 | Low | Low | 23 |
| S1-005 | Low | Low | 24 |
| S1-007 | Low | Medium | 25 |
| S3-002 | Low | Low | 26 |
| S3-004 | Low | Low | 27 |
| S4-003 | Low | Low | 28 |
| S4-006 | Low | Medium | 29 |
| S4-007 | Low | Medium | 30 |
| S3-007 | Low | N/A | 31 |
| S5-003 | Medium | Low | 32 |
| S5-004 | Medium | Low | 33 |
| S5-001 | Low | Low | 34 |
| S5-002 | Low | Medium | 35 |
| S5-005 | Low | Low | 36 |
| S5-006 | Low | Low | 37 |
| S6-001 | Low | Low | 38 |
| S6-002 | Low | Low | 39 |
| S6-003 | Low | Medium | 40 |

---

## Notes

### Session 1: Core Architecture
- Overall: Well-structured code with good separation of concerns
- Primary concern: Worker pool reliability under load
- The XML stats extraction strategy is smart - avoids Lua overhead in most cases

### Session 2: Optimizer Core
- Overall: Feature-rich but needs refactoring to reduce duplication
- Critical bug: S2-002 will crash extended objectives at runtime
- Design gap: Constraints exist but aren't used
- Multi-objective support is incomplete (standalone, not integrated)
- Both optimizers are well-documented with clear algorithms

### Session 3: Jewel System
- Overall: Well-designed registry pattern with good separation by jewel type
- Strong: Timeless jewel binary data loading is sophisticated and correct
- Strong: Cluster subgraph correctly models nested cluster structure
- Strong: Thread of Hope optimizer considers pathing efficiency
- Concern: Multiple duplicate/inconsistent socket definitions
- Concern: Some magic numbers in cluster socket classification
- The jewel system is the most modular part of the codebase

### Session 4: Mastery & Build Context
- Overall: Solid implementation with good heuristic fallbacks
- Strong: BuildContext provides comprehensive build analysis
- Strong: Ratio-based extrapolation is clever workaround for HeadlessWrapper limitations
- Strong: Batch evaluation provides significant performance improvement (~6x)
- Concern: Significant code duplication between BatchCalculator and RelativeCalculator
- Concern: Tree version hardcoded - will need updates each league
- The mastery optimizer correctly handles both calculator-based and heuristic selection

### Session 5: CLI & Integration
- Overall: Clean Click-based CLI with good command structure
- Strong: InputHandler supports multiple input formats (XML, PoB code, stdin)
- Strong: OutputHandler provides consistent JSON/console output
- Strong: GGG API client has proper rate limiting and error handling
- Strong: Command aliases (opt, stats, acc) improve usability
- Concern: Silent exception catching in several places
- Concern: Version scattered across multiple files
- The GGG → PoB converter handles complex item formats well

### Session 6: Visualization & Utilities
- Overall: Good optional dependency handling (matplotlib/plotly)
- Strong: Evolution plots provide useful GA insights (convergence, distribution)
- Strong: 3D Pareto frontier visualization with interactive Plotly option
- Strong: Tree position calculation correctly handles orbit system
- Concern: Consistent emoji usage issue across visualization modules
- The tree diff report is useful for understanding optimization changes

---

## Review Complete

**Total Findings: 42**
- High: 3 (2 in optimizer core, 1 in worker pool)
- Medium: 22
- Low: 17

**Critical Issues (Fix Immediately):**
1. **S2-002**: Broken import in extended_objectives.py - will crash at runtime
2. **S2-001**: Constraints module is completely disconnected - builds may violate limits
3. **S1-003**: Worker pool lock held for full evaluation duration - reliability risk

**High-Value Improvements:**
- Extract ~400+ lines of duplicated code between optimizers (S2-003)
- Integrate constraints into optimization loop (S2-001)
- Add dead worker auto-restart (S1-004)
- Cache XML parsing in genetic algorithm Individual class (S2-004)

**Tech Debt Patterns Identified:**
1. **Singleton singletons**: 4 instances of module-level mutable state (S1-007, S4-006, S5-001, S6-003)
2. **Inconsistent terminal output**: Emojis used in 3+ places without fallback (S2-010, S5-006, S6-001)
3. **Hardcoded tree version**: At least 3 places hardcode "3_27" (S4-001)
4. **Duplicate class definitions**: JewelSocket defined twice, outer rim sockets in two places (S3-001, S3-006)

**Architecture Strengths:**
- Clean separation between pob/, optimizer/, cli/, visualization/
- Good use of dataclasses throughout
- Graceful degradation for optional dependencies
- Comprehensive CLI with multiple input formats
- Sophisticated jewel system with proper registry pattern

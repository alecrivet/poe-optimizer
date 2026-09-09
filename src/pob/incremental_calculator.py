"""
Incremental Calculator - evaluate passive-tree changes without reloading PoB.

The build (items, gems, config) is loaded into every worker once. After that:

* ``evaluate_deltas``  - score many add/remove/mastery changes against the
  current base tree (~0.2 s each, spread across workers).
* ``commit``           - make a new tree the base for later deltas (~0.5 s).
* ``evaluate_trees``   - score arbitrary complete trees (genetic algorithm).
* ``evaluate_xmls``    - full-reload scoring for candidates that change
  items/jewels, not just the tree (~3-5 s each, parallel).

All results are ``RelativeEvaluation`` objects whose *baseline* is the
current base tree and whose *change percent* is therefore the marginal
effect of the candidate. Absolute numbers are extrapolated from the accurate
pre-calculated stats in the original XML, exactly as the other calculators do.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence, Set

from .calculator_utils import BuildStats, extract_build_stats
from .modifier import get_passive_tree_summary
from .relative_calculator import RelativeEvaluation
from .worker_pool import EvaluationResult, PoBWorkerPool, TreeDelta
from .xml_parser import get_build_summary

logger = logging.getLogger(__name__)


class IncrementalCalculatorError(RuntimeError):
    pass


class IncrementalCalculator:
    """
    Session-based calculator on top of ``PoBWorkerPool``.

    Example:
        >>> with IncrementalCalculator(num_workers=8) as calc:
        ...     calc.load(build_xml)
        ...     results = calc.evaluate_deltas({
        ...         "remove 123": TreeDelta(remove=[123]),
        ...         "add 456": TreeDelta(add=[456]),
        ...     })
        ...     best = max(results.items(), key=lambda kv: kv[1].dps_change_percent)
        ...     calc.commit(results_nodes[best[0]], masteries)
    """

    def __init__(self, num_workers: Optional[int] = None, calibration_factor: float = 1.0):
        self.pool = PoBWorkerPool(num_workers=num_workers)
        self.calibration_factor = calibration_factor
        self._started = False

        self.original_xml: Optional[str] = None
        self.original_accurate: Optional[BuildStats] = None  # from XML PlayerStats
        self.original_lua: Optional[BuildStats] = None       # Lua baseline of original tree
        self.current_lua: Optional[BuildStats] = None        # Lua stats of committed base tree
        self.current_nodes: Set[int] = set()
        self.current_masteries: Dict[int, int] = {}
        self.current_points: Optional[int] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> int:
        if self._started:
            return self.pool.get_stats()["alive_workers"]
        count = self.pool.start()
        self._started = True
        return count

    def shutdown(self):
        self.pool.shutdown()
        self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False

    @property
    def num_workers(self) -> int:
        return len(self.pool.workers) if self._started else self.pool.num_workers

    # ------------------------------------------------------------------ #
    # Session
    # ------------------------------------------------------------------ #

    def load(self, build_xml: str) -> RelativeEvaluation:
        """
        Load ``build_xml`` on all workers and make its tree the base.

        Returns a no-change evaluation of the original build (useful as the
        "before" record in optimisation results).
        """
        if not self._started:
            self.start()

        result = self.pool.load_session(build_xml)
        if not result.success:
            raise IncrementalCalculatorError(f"Failed to load build: {result.error}")

        summary = get_passive_tree_summary(build_xml)
        self.original_xml = build_xml
        self.original_accurate = extract_build_stats(get_build_summary(build_xml))
        self.original_lua = extract_build_stats(result.stats)
        self.current_lua = self.original_lua
        self.current_nodes = set(result.nodes) if result.nodes else set(summary["allocated_nodes"])
        self.current_masteries = dict(summary["mastery_effects"])
        self.current_points = result.points_used

        if self.original_accurate.dps == 0 and self.original_accurate.life == 0:
            logger.warning(
                "Build XML has no pre-calculated stats; absolute numbers will be "
                "Lua estimates rather than PoB desktop values."
            )
            self.original_accurate = self.original_lua

        logger.info(
            f"Session loaded: {len(self.current_nodes)} nodes, "
            f"Lua DPS {self.original_lua.dps:,.0f}, XML DPS {self.original_accurate.dps:,.0f}"
        )
        return self._evaluation(self.current_lua, self.current_lua)

    def commit(self, nodes: Sequence[int], masteries: Optional[Dict[int, int]] = None) -> RelativeEvaluation:
        """
        Make ``nodes``/``masteries`` the base tree on all workers.

        Returns the evaluation of the new base relative to the *previous* base.
        """
        self._require_session()
        if masteries is None:
            masteries = self.current_masteries
        result = self.pool.set_tree(nodes, masteries)
        if not result.success:
            raise IncrementalCalculatorError(f"Failed to commit tree: {result.error}")

        previous = self.current_lua
        self.current_lua = extract_build_stats(result.stats)
        self.current_nodes = set(result.nodes) if result.nodes else set(int(n) for n in nodes)
        self.current_masteries = {int(k): int(v) for k, v in masteries.items()}
        self.current_points = result.points_used
        return self._evaluation(previous, self.current_lua)

    def reload(self, build_xml: str) -> RelativeEvaluation:
        """
        Replace the session build entirely (e.g. after a jewel/item change).

        The evaluation returned compares the new build to the previous base
        tree. The original accurate baseline is kept so that absolute numbers
        stay comparable across the whole optimisation run.
        """
        self._require_session()
        previous = self.current_lua
        original_accurate = self.original_accurate
        original_lua = self.original_lua

        result = self.pool.load_session(build_xml)
        if not result.success:
            raise IncrementalCalculatorError(f"Failed to reload build: {result.error}")

        summary = get_passive_tree_summary(build_xml)
        self.current_lua = extract_build_stats(result.stats)
        self.current_nodes = set(result.nodes) if result.nodes else set(summary["allocated_nodes"])
        self.current_masteries = dict(summary["mastery_effects"])
        self.current_points = result.points_used
        self.original_accurate = original_accurate
        self.original_lua = original_lua
        return self._evaluation(previous, self.current_lua)

    def evaluate_current_vs_original(self) -> RelativeEvaluation:
        """Evaluation of the committed base tree relative to the original build."""
        self._require_session()
        return self._evaluation(self.original_lua, self.current_lua, baseline_is_original=True)

    # ------------------------------------------------------------------ #
    # Evaluation
    # ------------------------------------------------------------------ #

    def evaluate_deltas(self, deltas: Dict[str, TreeDelta]) -> Dict[str, "DeltaEvaluation"]:
        """
        Evaluate named deltas against the base tree in parallel.

        Failed candidates are logged and omitted from the result.
        """
        self._require_session()
        names = list(deltas.keys())
        results = self.pool.evaluate_deltas([deltas[n] for n in names])
        out: Dict[str, DeltaEvaluation] = {}
        for name, result in zip(names, results):
            if not result.success:
                logger.debug(f"Delta '{name}' failed: {result.error}")
                continue
            out[name] = DeltaEvaluation(
                evaluation=self._evaluation(self.current_lua, extract_build_stats(result.stats)),
                nodes=set(result.nodes) if result.nodes else None,
                points_used=result.points_used,
                raw=result,
            )
        return out

    def evaluate_trees(
        self,
        trees: Dict[str, Sequence[int]],
        masteries: Optional[Dict[str, Optional[Dict[int, int]]]] = None,
    ) -> Dict[str, "DeltaEvaluation"]:
        """
        Evaluate arbitrary complete trees (SET on each worker).

        After this call the workers no longer share a base tree; ``commit`` (or
        ``load``) must be called before ``evaluate_deltas`` is used again.
        """
        self._require_session()
        names = list(trees.keys())
        mast = [masteries.get(n) if masteries else None for n in names]
        results = self.pool.evaluate_trees([trees[n] for n in names], mast)
        out: Dict[str, DeltaEvaluation] = {}
        for name, result in zip(names, results):
            if not result.success:
                logger.debug(f"Tree '{name}' failed: {result.error}")
                continue
            out[name] = DeltaEvaluation(
                evaluation=self._evaluation(self.current_lua, extract_build_stats(result.stats)),
                nodes=set(result.nodes) if result.nodes else set(int(n) for n in trees[name]),
                points_used=result.points_used,
                raw=result,
            )
        return out

    def evaluate_xmls(self, xmls: Dict[str, str]) -> Dict[str, "DeltaEvaluation"]:
        """
        Full-reload evaluation of complete build XMLs (items/jewels may differ).

        Slow (~3-5 s per build) but parallel across workers. Workers that ran
        a full reload have lost the session tree; the pool restores it lazily
        on the next session call, so prefer ``evaluate_deltas`` when only the
        tree changes.
        """
        self._require_session()
        names = list(xmls.keys())
        results = self.pool.evaluate_batch([xmls[n] for n in names])
        out: Dict[str, DeltaEvaluation] = {}
        for name, result in zip(names, results):
            if not result.success:
                logger.debug(f"XML candidate '{name}' failed: {result.error}")
                continue
            out[name] = DeltaEvaluation(
                evaluation=self._evaluation(self.current_lua, extract_build_stats(result.stats)),
                nodes=None,
                points_used=result.points_used,
                raw=result,
            )
        # Full reloads replaced the session build on those workers; put the
        # committed base back so later deltas are consistent.
        self._resync_workers()
        return out

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _require_session(self):
        if self.original_xml is None or self.current_lua is None:
            raise IncrementalCalculatorError("No build loaded; call load() first")

    def _resync_workers(self):
        """Re-establish the session build + committed tree on every worker."""
        result = self.pool.load_session(self.original_xml)
        if not result.success:
            raise IncrementalCalculatorError(f"Failed to resync workers: {result.error}")
        if self.current_nodes:
            result = self.pool.set_tree(sorted(self.current_nodes), self.current_masteries)
            if not result.success:
                raise IncrementalCalculatorError(f"Failed to resync tree: {result.error}")

    def _ratio(self, old: float, new: float) -> float:
        return new / old if old else 1.0

    def _evaluation(
        self,
        baseline_lua: BuildStats,
        modified_lua: BuildStats,
        baseline_is_original: bool = False,
    ) -> RelativeEvaluation:
        """
        Build a RelativeEvaluation comparing ``modified_lua`` to ``baseline_lua``.

        Absolute values are extrapolated from the original build's accurate
        stats using each tree's ratio to the original Lua baseline, so numbers
        stay on the PoB-desktop scale throughout a run.
        """
        acc = self.original_accurate
        orig = self.original_lua

        def absolute(stats: BuildStats) -> BuildStats:
            if baseline_is_original and stats is orig:
                return acc
            return BuildStats(
                dps=acc.dps * self._ratio(orig.dps, stats.dps),
                life=acc.life * self._ratio(orig.life, stats.life),
                ehp=acc.ehp * self._ratio(orig.ehp, stats.ehp),
            )

        base_abs = absolute(baseline_lua)
        mod_abs = absolute(modified_lua)

        dps_ratio = self._ratio(baseline_lua.dps, modified_lua.dps) * self.calibration_factor
        life_ratio = self._ratio(baseline_lua.life, modified_lua.life)
        ehp_ratio = self._ratio(baseline_lua.ehp, modified_lua.ehp)

        return RelativeEvaluation(
            baseline_dps=base_abs.dps,
            baseline_life=base_abs.life,
            baseline_ehp=base_abs.ehp,
            estimated_dps=base_abs.dps * dps_ratio,
            estimated_life=base_abs.life * life_ratio,
            estimated_ehp=base_abs.ehp * ehp_ratio,
            dps_ratio=dps_ratio,
            life_ratio=life_ratio,
            ehp_ratio=ehp_ratio,
            dps_change_percent=(dps_ratio - 1) * 100,
            life_change_percent=(life_ratio - 1) * 100,
            ehp_change_percent=(ehp_ratio - 1) * 100,
            baseline_lua_dps=baseline_lua.dps,
            modified_lua_dps=modified_lua.dps,
        )


class DeltaEvaluation:
    """Evaluation of one candidate plus the tree state it would produce."""

    __slots__ = ("evaluation", "nodes", "points_used", "raw")

    def __init__(
        self,
        evaluation: RelativeEvaluation,
        nodes: Optional[Set[int]],
        points_used: Optional[int],
        raw: EvaluationResult,
    ):
        self.evaluation = evaluation
        self.nodes = nodes
        self.points_used = points_used
        self.raw = raw

    def __repr__(self) -> str:
        return (
            f"DeltaEvaluation(dps {self.evaluation.dps_change_percent:+.2f}%, "
            f"life {self.evaluation.life_change_percent:+.2f}%, points={self.points_used})"
        )

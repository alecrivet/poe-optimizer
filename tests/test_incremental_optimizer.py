"""
Tests for the incremental calculator and the greedy optimizer's fast path.

Unit tests for candidate generation / filtering run without PoB. The
end-to-end tests need luajit + the PathOfBuilding submodule.
"""

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.optimizer.constraints import ConstraintSet, PointBudgetConstraint
from src.optimizer.tree_optimizer import GreedyTreeOptimizer
from src.pob.incremental_calculator import DeltaEvaluation
from src.pob.modifier import get_passive_tree_summary, set_passive_tree
from src.pob.relative_calculator import RelativeEvaluation
from src.pob.tree_parser import PassiveNode, PassiveTreeGraph
from src.pob.worker_pool import EvaluationResult, TreeDelta

FIXTURE = Path(__file__).parent / "fixtures" / "builds" / "cyclone_slayer.xml"
POB_SRC = Path(__file__).parent.parent / "PathOfBuilding" / "src"

needs_pob = pytest.mark.skipif(
    shutil.which("luajit") is None or not (POB_SRC / "HeadlessWrapper.lua").exists(),
    reason="luajit and the PathOfBuilding submodule are required",
)


def _node(node_id, name="n", node_type="normal", connections=(), is_ascendancy=False, is_mastery=False):
    return PassiveNode(
        node_id=node_id, name=name, stats=[], node_type=node_type,
        connections=list(connections), is_ascendancy=is_ascendancy, is_mastery=is_mastery,
    )


def _eval(dps_pct):
    return RelativeEvaluation(
        baseline_dps=100, baseline_life=100, baseline_ehp=100,
        estimated_dps=100 + dps_pct, estimated_life=100, estimated_ehp=100,
        dps_ratio=1 + dps_pct / 100, life_ratio=1, ehp_ratio=1,
        dps_change_percent=dps_pct, life_change_percent=0, ehp_change_percent=0,
        baseline_lua_dps=100, modified_lua_dps=100 + dps_pct,
    )


def _delta_eval(dps_pct, points, nodes=None):
    return DeltaEvaluation(
        evaluation=_eval(dps_pct), nodes=nodes, points_used=points,
        raw=EvaluationResult(success=True, stats={}),
    )


@pytest.fixture
def optimizer():
    """Greedy optimizer with a tiny synthetic tree and no PoB access."""
    opt = GreedyTreeOptimizer(
        optimize_masteries=False, enable_node_addition=True,
        show_progress=False, use_incremental=True, max_points_change=2,
    )
    graph = PassiveTreeGraph()
    # 1 (class start) - 2 - 3 - 4 ; 3 - 5 (unallocated) ; 9 ascendancy ; 6 mastery neighbour of 2
    graph.add_node(_node(1, "Start", node_type="class_start", connections=[2]))
    graph.add_node(_node(2, "A", connections=[1, 3, 6]))
    graph.add_node(_node(3, "B", connections=[2, 4, 5]))
    graph.add_node(_node(4, "C", connections=[3]))
    graph.add_node(_node(5, "D", connections=[3]))
    graph.add_node(_node(6, "Mastery", node_type="mastery", is_mastery=True, connections=[2]))
    graph.add_node(_node(9, "Asc", is_ascendancy=True, connections=[]))
    opt.tree_graph = graph
    return opt


class TestSetPassiveTree:
    def test_replaces_nodes_and_prunes_orphan_masteries(self):
        xml = FIXTURE.read_text()
        summary = get_passive_tree_summary(xml)
        nodes = sorted(summary["allocated_nodes"])
        masteries = dict(summary["mastery_effects"])
        mastery_node = next(iter(masteries))

        new_nodes = [n for n in nodes if n != mastery_node]
        out = set_passive_tree(xml, new_nodes, masteries)
        new_summary = get_passive_tree_summary(out)
        assert new_summary["allocated_nodes"] == set(new_nodes)
        assert mastery_node not in new_summary["mastery_effects"]
        assert len(new_summary["mastery_effects"]) == len(masteries) - 1


class TestCandidateGeneration:
    def test_removals_skip_start_ascendancy_protected_and_masteries(self, optimizer):
        allocated = {1, 2, 3, 4, 6, 9}
        deltas = optimizer._generate_delta_candidates(allocated, {}, protected={4}, class_starts={1})
        removes = {d.remove[0] for d in deltas.values() if d.remove}
        assert removes == {2, 3}

    def test_additions_are_unallocated_neighbours(self, optimizer):
        allocated = {1, 2, 3}
        deltas = optimizer._generate_delta_candidates(allocated, {}, protected=set(), class_starts={1})
        adds = {d.add[0] for d in deltas.values() if d.add}
        # 4 and 5 are neighbours of 3; the mastery (6) needs mastery optimisation to be added
        assert adds == {4, 5}

    def test_swaps_pair_best_removals_with_best_additions(self, optimizer):
        optimizer.swap_candidates = 1
        deltas = {
            "rm2": TreeDelta(remove=[2]),
            "rm3": TreeDelta(remove=[3]),
            "add4": TreeDelta(add=[4]),
            "add5": TreeDelta(add=[5]),
        }
        evals = {
            "rm2": _delta_eval(-10, 2), "rm3": _delta_eval(-1, 2),
            "add4": _delta_eval(+5, 4), "add5": _delta_eval(+2, 4),
        }
        swaps = optimizer._generate_swap_candidates(deltas, evals, "dps")
        assert len(swaps) == 1
        (name, delta), = swaps.items()
        assert delta.remove == [3] and delta.add == [4]

    def test_filter_rejects_candidates_that_prune_protected_nodes(self, optimizer):
        evals = {
            "keeps_socket": _delta_eval(1, 10, nodes={1, 2, 3, 7}),
            "prunes_socket": _delta_eval(5, 9, nodes={1, 2, 3}),
            "no_node_info": _delta_eval(1, 10, nodes=None),
        }
        kept = optimizer._filter_incremental(
            evals, original_points=10, original_node_count=12,
            allow_point_increase=False, protected={7},
        )
        assert set(kept) == {"keeps_socket", "no_node_info"}

    def test_filter_enforces_point_budget(self, optimizer):
        optimizer.constraints = ConstraintSet(point_budget=PointBudgetConstraint(max_points=10))
        evals = {
            "ok": _delta_eval(1, 10),
            "over_original_no_increase": _delta_eval(1, 11),
            "too_big_change": _delta_eval(1, 7),
            "unknown_points": _delta_eval(1, None),
        }
        kept = optimizer._filter_incremental(evals, original_points=10, original_node_count=12, allow_point_increase=False)
        assert set(kept) == {"ok", "unknown_points"}

        optimizer.constraints = ConstraintSet(point_budget=PointBudgetConstraint(max_points=12))
        kept = optimizer._filter_incremental(evals, original_points=10, original_node_count=12, allow_point_increase=True)
        assert set(kept) == {"ok", "over_original_no_increase", "unknown_points"}


@needs_pob
class TestIncrementalCalculator:
    def test_marginal_semantics_and_commit(self):
        from src.pob.incremental_calculator import IncrementalCalculator

        xml = FIXTURE.read_text()
        summary = get_passive_tree_summary(xml)
        nodes = sorted(summary["allocated_nodes"])

        with IncrementalCalculator(num_workers=2) as calc:
            baseline = calc.load(xml)
            assert baseline.dps_change_percent == 0
            # Absolute numbers are on the XML (PoB desktop) scale
            assert baseline.baseline_dps == pytest.approx(3548894, rel=1e-3)

            results = calc.evaluate_deltas({
                "noop": TreeDelta(),
                "rm": TreeDelta(remove=[nodes[1]]),
            })
            assert results["noop"].evaluation.dps_change_percent == pytest.approx(0, abs=1e-9)
            rm = results["rm"]
            assert rm.evaluation.dps_change_percent < 0
            assert rm.points_used == 117  # removes the node and one dependent

            # Commit the removal: the next no-op is 0% relative to the new base,
            # while current-vs-original reports the accumulated change.
            calc.commit(rm.nodes, summary["mastery_effects"])
            after = calc.evaluate_deltas({"noop": TreeDelta()})["noop"]
            assert after.evaluation.dps_change_percent == pytest.approx(0, abs=1e-9)
            total = calc.evaluate_current_vs_original()
            assert total.dps_change_percent == pytest.approx(rm.evaluation.dps_change_percent, rel=1e-6)
            assert total.baseline_dps == pytest.approx(3548894, rel=1e-3)


@needs_pob
class TestGreedyIncrementalEndToEnd:
    def test_one_iteration_improves_dps_without_adding_points(self):
        xml = FIXTURE.read_text()
        opt = GreedyTreeOptimizer(
            max_iterations=1, min_improvement=0.1, show_progress=False,
            max_workers=4, use_incremental=True,
        )
        try:
            result = opt.optimize(xml, objective="dps", allow_point_increase=False)
        finally:
            opt.shutdown()

        assert result.iterations == 1
        assert result.optimized_stats.dps_change_percent > 0
        assert result.modifications_applied[0]["points_used"] <= 119
        assert not result.constraint_violations
        # The output XML reflects the committed tree
        assert get_passive_tree_summary(result.optimized_xml)["allocated_nodes"] != \
            get_passive_tree_summary(xml)["allocated_nodes"]

"""
Tests for the persistent PoB worker pool and its session protocol.

Most tests need luajit and the PathOfBuilding submodule; they are skipped
when either is missing. Pure-Python tests (request encoding) always run.
"""

import shutil
from pathlib import Path

import pytest

from src.pob.worker_pool import EvaluationResult, PoBWorker, PoBWorkerPool, TreeDelta
from src.pob.modifier import get_passive_tree_summary

FIXTURE = Path(__file__).parent / "fixtures" / "builds" / "cyclone_slayer.xml"
POB_SRC = Path(__file__).parent.parent / "PathOfBuilding" / "src"

needs_pob = pytest.mark.skipif(
    shutil.which("luajit") is None or not (POB_SRC / "HeadlessWrapper.lua").exists(),
    reason="luajit and the PathOfBuilding submodule are required",
)


class TestTreeDelta:
    def test_to_request_only_includes_set_fields(self):
        assert TreeDelta().to_request() == {}
        assert TreeDelta(add=[1, 2]).to_request() == {"add": [1, 2]}
        assert TreeDelta(remove=(3,)).to_request() == {"remove": [3]}
        assert TreeDelta(masteries={10: 20}).to_request() == {"masteries": {"10": 20}}

    def test_is_empty(self):
        assert TreeDelta().is_empty
        assert not TreeDelta(add=[1]).is_empty
        assert not TreeDelta(masteries={1: 2}).is_empty


@needs_pob
class TestWorkerProtocol:
    @pytest.fixture(scope="class")
    def worker(self):
        w = PoBWorker(worker_id=0)
        assert w.start(), "worker failed to start"
        yield w
        w.stop()

    @pytest.fixture(scope="class")
    def xml(self):
        return FIXTURE.read_text()

    def test_ping(self, worker):
        assert worker.ping()

    def test_full_reload_then_session(self, worker, xml):
        full = worker.evaluate(xml)
        assert full.success, full.error
        assert full.stats["combinedDPS"] > 0

        base = worker.load_session(xml)
        assert base.success, base.error
        assert base.stats["combinedDPS"] == pytest.approx(full.stats["combinedDPS"], rel=1e-6)
        assert base.points_used == 119
        assert base.nodes and len(base.nodes) == 130

    def test_delta_results_are_attributed_to_the_right_request(self, worker, xml):
        """Regression: the old select()+buffered-pipe reader returned results
        shifted by one request. Each removal must give its own DPS."""
        worker.load_session(xml)
        nodes = sorted(get_passive_tree_summary(xml)["allocated_nodes"])
        base = worker.evaluate_delta(TreeDelta())
        assert base.success

        seen = {}
        for node_id in nodes[:6]:
            res = worker.evaluate_delta(TreeDelta(remove=[node_id]))
            assert res.success, res.error
            seen[node_id] = res.stats["combinedDPS"]
            assert res.points_used is not None and res.points_used < base.points_used
            assert node_id not in res.nodes

        # Removing a path node prunes its dependents: at least one removal
        # must differ from the baseline, and results must not all be identical.
        assert any(v != base.stats["combinedDPS"] for v in seen.values())
        assert len(set(seen.values())) > 1

    def test_delta_does_not_change_base(self, worker, xml):
        worker.load_session(xml)
        base = worker.evaluate_delta(TreeDelta())
        nodes = sorted(get_passive_tree_summary(xml)["allocated_nodes"])
        worker.evaluate_delta(TreeDelta(remove=[nodes[0]]))
        again = worker.evaluate_delta(TreeDelta())
        assert again.stats["combinedDPS"] == base.stats["combinedDPS"]
        assert again.stats["life"] == base.stats["life"]

    def test_set_matches_delta(self, worker, xml):
        worker.load_session(xml)
        summary = get_passive_tree_summary(xml)
        nodes = sorted(summary["allocated_nodes"])
        victim = nodes[1]
        delta = worker.evaluate_delta(TreeDelta(remove=[victim]))
        assert delta.success

        committed = worker.set_tree(delta.nodes, summary["mastery_effects"])
        assert committed.success, committed.error
        assert committed.stats["combinedDPS"] == pytest.approx(delta.stats["combinedDPS"], rel=1e-6)
        assert committed.points_used == delta.points_used

        # restore
        restored = worker.set_tree(nodes, summary["mastery_effects"])
        assert restored.success
        assert restored.points_used == 119

    def test_remove_start_node_is_rejected(self, worker, xml):
        worker.load_session(xml)
        # Class start nodes are 6 small ids; find one PoB reports as ClassStart by
        # asking for an obviously-invalid removal instead.
        res = worker.evaluate_delta(TreeDelta(remove=[-1]))
        assert not res.success


@needs_pob
class TestWorkerPool:
    def test_parallel_deltas_keep_order(self):
        xml = FIXTURE.read_text()
        nodes = sorted(get_passive_tree_summary(xml)["allocated_nodes"])
        with PoBWorkerPool(num_workers=3) as pool:
            base = pool.load_session(xml)
            assert base.success, base.error

            deltas = [TreeDelta(remove=[n]) for n in nodes[:9]]
            results = pool.evaluate_deltas(deltas)
            assert len(results) == 9
            assert all(r.success for r in results), [r.error for r in results]
            # Order preserved: each result's node list must exclude its own node
            for d, r in zip(deltas, results):
                assert d.remove[0] not in r.nodes

            # Sequential reference on a single worker must agree with pooled results
            ref = pool.workers[0].evaluate_delta(deltas[0])
            assert ref.stats["combinedDPS"] == results[0].stats["combinedDPS"]

    def test_evaluate_batch_full_reload(self):
        xml = FIXTURE.read_text()
        with PoBWorkerPool(num_workers=2) as pool:
            results = pool.evaluate_batch([xml, xml])
            assert all(r.success for r in results)
            assert results[0].stats["combinedDPS"] == results[1].stats["combinedDPS"]
            assert pool.get_stats()["alive_workers"] == 2

    def test_dead_worker_is_revived_with_session(self):
        xml = FIXTURE.read_text()
        with PoBWorkerPool(num_workers=1) as pool:
            pool.load_session(xml)
            worker = pool.workers[0]
            worker.process.kill()
            worker.process.wait(timeout=5)
            res = pool.evaluate_delta(TreeDelta())
            assert res.success, res.error
            assert res.points_used == 119


@needs_pob
class TestLatestTreeVersion:
    """The fixture converted to the newest tree must load and evaluate."""

    def test_fixture_on_latest_tree(self):
        from src.pob.tree_version import get_latest_tree_version, get_tree_version_from_xml

        xml = (FIXTURE.parent / "cyclone_slayer_3_29.xml").read_text()
        assert get_tree_version_from_xml(xml) == "3_29"
        # If PoB ships a newer tree, convert a copy of the fixture and update this test
        assert get_latest_tree_version() >= "3_29"

        worker = PoBWorker(worker_id=0)
        assert worker.start()
        try:
            base = worker.load_session(xml)
            assert base.success, base.error
            assert base.points_used == 119
            assert base.stats["combinedDPS"] > 1_000_000
            nodes = sorted(get_passive_tree_summary(xml)["allocated_nodes"])
            res = worker.evaluate_delta(TreeDelta(remove=[nodes[1]]))
            assert res.success and res.points_used < 119
            committed = worker.set_tree(res.nodes, get_passive_tree_summary(xml)["mastery_effects"])
            assert committed.success, committed.error
        finally:
            worker.stop()


@needs_pob
class TestPoBImport:
    def test_import_minimal_character_through_pob(self):
        """IMPORT: PoB's own ImportTab builds the XML (tree, jewels, cluster nodes)."""
        from src.pob.tree_parser import load_jewel_slots, load_passive_tree
        from src.web.tree_data import get_tree_data
        graph = load_passive_tree("3_29")
        # a short Duelist path: the class start's first two neighbours
        start = get_tree_data("3_29").class_starts["Duelist"]
        first = [n for n in graph.get_neighbors(start) if graph.get_node(n) and not graph.get_node(n).is_ascendancy][:2]
        char = {
            "name": "Fixture", "class": "Slayer", "league": "Standard", "level": 60,
            "equipment": [{"id": "w", "name": "", "typeLine": "Rusted Sword", "frameType": 0, "ilvl": 1, "identified": True, "inventoryId": "Weapon", "x": 0, "y": 0, "w": 1, "h": 3,
                           "sockets": [{"group": 0, "attr": "S", "sColour": "R"}],
                           "socketedItems": [{"id": "g", "typeLine": "Cyclone", "frameType": 4, "socket": 0,
                                              "properties": [{"name": "Level", "values": [["20", 0]]}, {"name": "Quality", "values": [["+20%", 1]]}]}]}],
            "jewels": [{"id": "j", "name": "", "typeLine": "Crimson Jewel", "frameType": 0, "ilvl": 1, "identified": True, "inventoryId": "PassiveJewels", "x": 0, "y": 0, "w": 1, "h": 1,
                        "explicitMods": ["+7% to maximum Life"]}],
            "passives": {"hashes": first, "hashes_ex": [], "mastery_effects": {}, "jewel_data": {}, "skill_overrides": {}, "alternate_ascendancy": 0},
        }
        w = PoBWorker(worker_id=0)
        assert w.start()
        try:
            res = w.import_character(char)
        finally:
            w.stop()
        assert res.success, res.error
        assert res.xml and "<PathOfBuilding>" in res.xml
        assert res.points_used == len(first)
        assert 'className="Duelist"' in res.xml and 'ascendClassName="Slayer"' in res.xml
        assert "Crimson Jewel" in res.xml and f'nodeId="{load_jewel_slots("3_29")[0]}"' in res.xml
        assert "Cyclone" in res.xml

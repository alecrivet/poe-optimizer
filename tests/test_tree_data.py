"""
Tests for src/web/tree_data.py: the browser-facing passive tree export.

These read PoB's tree.lua from the submodule on disk (no network) and are
skipped when the 3_29 tree data is missing.
"""

import json
import math
import time
from pathlib import Path

import pytest

from src.web import tree_data as td_mod
from src.web.tree_data import (
    CLUSTER_ID_THRESHOLD,
    NODE_TYPES,
    TreeData,
    TreeNodeData,
    get_tree_data,
    tree_data_to_dict,
)

VERSION = "3_29"
TREE_FILE = Path("./PathOfBuilding/src/TreeData") / VERSION / "tree.lua"

pytestmark = pytest.mark.skipif(
    not TREE_FILE.exists(), reason=f"PoB tree data for {VERSION} not present"
)


@pytest.fixture(scope="module")
def first_call():
    """Cold build of the 3_29 export with its wall-clock time."""
    td_mod.clear_cache()
    start = time.perf_counter()
    data = get_tree_data(VERSION)
    return data, time.perf_counter() - start


@pytest.fixture(scope="module")
def tree(first_call) -> TreeData:
    return first_call[0]


def test_first_call_is_fast(first_call):
    _, elapsed = first_call
    assert elapsed < 15.0, f"first get_tree_data took {elapsed:.1f}s"


def test_node_count_and_version(tree):
    assert tree.version == VERSION
    # 3_29 has ~3,400 node definitions but only ~3,000 are placed on the tree;
    # the rest are cluster/timeless-jewel-only passives without coordinates.
    assert len(tree.nodes) > 2900


def test_every_node_has_finite_position(tree):
    for node in tree.nodes:
        assert isinstance(node, TreeNodeData)
        assert math.isfinite(node.x), node
        assert math.isfinite(node.y), node


def test_no_cluster_ids_and_ids_unique(tree):
    ids = [n.id for n in tree.nodes]
    assert len(ids) == len(set(ids))
    assert all(i < CLUSTER_ID_THRESHOLD for i in ids)


def test_edges_reference_exported_nodes_once(tree):
    ids = {n.id for n in tree.nodes}
    assert len(tree.edges) > 1000
    seen = set()
    for edge in tree.edges:
        assert len(edge) == 2
        a, b = edge
        assert a < b, edge
        assert a in ids and b in ids, edge
        assert (a, b) not in seen, f"duplicate edge {edge}"
        seen.add((a, b))


def test_every_node_type_present(tree):
    types = {n.type for n in tree.nodes}
    assert types == set(NODE_TYPES)


def test_ascendancy_nodes_are_tagged(tree):
    asc = [n for n in tree.nodes if n.ascendancy]
    assert len(asc) > 100
    assert "Slayer" in {n.ascendancy for n in asc}
    non_asc = [n for n in tree.nodes if n.ascendancy is None]
    assert len(non_asc) > len(asc)


def test_class_starts(tree):
    assert len(tree.class_starts) == 7
    assert set(tree.class_starts) == {
        "Scion", "Marauder", "Ranger", "Witch", "Duelist", "Templar", "Shadow",
    }
    ids = {n.id: n for n in tree.nodes}
    for name, node_id in tree.class_starts.items():
        assert node_id in ids, name
        assert ids[node_id].type == "class_start"


def test_bounds_cover_all_nodes(tree):
    b = tree.bounds
    assert set(b) == {"min_x", "min_y", "max_x", "max_y"}
    assert b["min_x"] < b["max_x"]
    assert b["min_y"] < b["max_y"]
    for n in tree.nodes:
        assert b["min_x"] <= n.x <= b["max_x"]
        assert b["min_y"] <= n.y <= b["max_y"]


def test_to_dict_round_trips_through_json(tree):
    d = tree_data_to_dict(tree)
    text = json.dumps(d, separators=(",", ":"))
    assert len(text.encode("utf-8")) < 1_500_000

    back = json.loads(text)
    assert back["version"] == VERSION
    assert len(back["nodes"]) == len(tree.nodes)
    assert len(back["edges"]) == len(tree.edges)
    assert back["class_starts"] == tree.class_starts
    assert set(back["bounds"]) == {"min_x", "min_y", "max_x", "max_y"}

    first = back["nodes"][0]
    assert set(first) == {"i", "x", "y", "n", "t", "a"}
    by_id = {n["i"]: n for n in back["nodes"]}
    for n in tree.nodes:
        j = by_id[n.id]
        assert abs(j["x"] - n.x) < 0.1
        assert abs(j["y"] - n.y) < 0.1
        assert j["n"] == n.name
        assert j["t"] == n.type
        assert j["a"] == n.ascendancy


def test_get_tree_data_is_cached(tree):
    assert get_tree_data(VERSION) is tree
    assert get_tree_data(VERSION) is get_tree_data(VERSION)


def test_default_version_is_latest():
    latest = get_tree_data(None)
    assert latest.version
    assert len(latest.nodes) > 2900
    assert get_tree_data(None) is latest


def test_unknown_version_raises():
    with pytest.raises(FileNotFoundError):
        get_tree_data("0_00")

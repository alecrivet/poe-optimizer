"""
Passive tree export for the browser.

Builds a compact, JSON-serialisable snapshot of a passive tree version
(node positions, names, types, edges) for the front end to draw as SVG.
Results are cached per tree version; the first build for a version costs
about 0.1 s (two regex passes over PoB's ``tree.lua``), later calls are free.

Sources:
- ``src.pob.tree_parser.load_passive_tree``: node ids, names, types,
  ascendancy membership, connections.
- ``src.pob.tree_positions.TreePositionLoader``: x/y computed from PoB's
  group/orbit layout.

Only drawable nodes are exported: those with a position and a non-cluster id
(< 65536). PoB's ``tree.lua`` also lists ~400 passives that exist only inside
cluster or timeless jewels; they have no group, no coordinates and no edges,
so they are skipped here.
"""

from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.pob.tree_parser import load_passive_tree
from src.pob.tree_positions import TreePositionLoader
from src.pob.tree_version import get_latest_tree_version_or_raise

logger = logging.getLogger(__name__)

# Ids at or above this are cluster jewel proxy nodes, never drawn on the base tree.
CLUSTER_ID_THRESHOLD = 65536

# Every value ``TreeNodeData.type`` can take (mirrors PassiveNode.node_type).
NODE_TYPES = (
    "normal",
    "notable",
    "keystone",
    "jewel",
    "mastery",
    "class_start",
    "ascendancy_start",
)

# PoB's tree.lua names the class start nodes with placeholder strings
# ("Seven" for Scion, "SIX" for Shadow, "TEMPLAR" for Templar, ...).
# Map them to the class names players know.
_CLASS_START_NAMES = {
    "SEVEN": "Scion",
    "SIX": "Shadow",
    "MARAUDER": "Marauder",
    "RANGER": "Ranger",
    "WITCH": "Witch",
    "DUELIST": "Duelist",
    "TEMPLAR": "Templar",
    "SCION": "Scion",
    "SHADOW": "Shadow",
}


@dataclass
class TreeNodeData:
    """One drawable passive node."""

    id: int
    x: float
    y: float
    name: str
    type: str  # one of NODE_TYPES
    ascendancy: Optional[str]  # ascendancy name for ascendancy nodes, else None


@dataclass
class TreeData:
    """A drawable snapshot of one passive tree version."""

    version: str
    nodes: List[TreeNodeData]  # every node with a position and id < CLUSTER_ID_THRESHOLD
    edges: List[List[int]]  # [a, b] with a < b, each undirected edge once, both ids exported
    bounds: Dict[str, float]  # {"min_x", "min_y", "max_x", "max_y"} over exported nodes
    class_starts: Dict[str, int]  # class name (e.g. "Marauder") -> start node id


_cache: Dict[str, TreeData] = {}
_cache_lock = threading.Lock()


def _canonical_class_name(raw_name: str) -> str:
    """Translate PoB's class-start node name into a player-facing class name."""
    return _CLASS_START_NAMES.get(raw_name.strip().upper(), raw_name.strip().title())


def build_tree_data(version: str, pob_path: str = "./PathOfBuilding") -> TreeData:
    """
    Build a TreeData for ``version`` from the PoB submodule, bypassing the cache.

    Raises FileNotFoundError if the tree version has no data on disk.
    """
    graph = load_passive_tree(version)
    positions = TreePositionLoader(version, pob_path=pob_path).load_positions()

    if not graph.nodes or not positions:
        raise FileNotFoundError(
            f"No passive tree data for version {version!r} under {pob_path}/src/TreeData/"
        )

    nodes: List[TreeNodeData] = []
    exported_ids = set()
    for node_id in sorted(graph.nodes):
        if node_id >= CLUSTER_ID_THRESHOLD:
            continue
        pos = positions.get(node_id)
        if pos is None:
            continue
        if not (math.isfinite(pos.x) and math.isfinite(pos.y)):
            logger.debug("Skipping node %d with non-finite position", node_id)
            continue
        node = graph.nodes[node_id]
        nodes.append(
            TreeNodeData(
                id=node_id,
                x=float(pos.x),
                y=float(pos.y),
                name=node.name,
                type=node.node_type if node.node_type in NODE_TYPES else "normal",
                ascendancy=node.ascendancy_name if node.is_ascendancy else None,
            )
        )
        exported_ids.add(node_id)

    edge_set = set()
    for node_id in exported_ids:
        for other in graph.nodes[node_id].connections:
            if other == node_id or other not in exported_ids:
                continue
            edge_set.add((node_id, other) if node_id < other else (other, node_id))
    edges = [[a, b] for a, b in sorted(edge_set)]

    if nodes:
        bounds = {
            "min_x": min(n.x for n in nodes),
            "min_y": min(n.y for n in nodes),
            "max_x": max(n.x for n in nodes),
            "max_y": max(n.y for n in nodes),
        }
    else:
        bounds = {"min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0}

    class_starts = {
        _canonical_class_name(name): node_id
        for name, node_id in graph.class_start_nodes.items()
        if node_id in exported_ids
    }

    logger.info(
        "Built tree data for %s: %d nodes, %d edges, %d class starts",
        version, len(nodes), len(edges), len(class_starts),
    )
    return TreeData(
        version=version,
        nodes=nodes,
        edges=edges,
        bounds=bounds,
        class_starts=class_starts,
    )


def get_tree_data(version: Optional[str] = None) -> TreeData:
    """
    Return the drawable tree for ``version`` (None = latest standard tree).

    Cached per version for the life of the process; the same TreeData object
    is returned on repeated calls, so callers must not mutate it.
    """
    if version is None:
        version = get_latest_tree_version_or_raise()

    cached = _cache.get(version)
    if cached is not None:
        return cached

    with _cache_lock:
        cached = _cache.get(version)
        if cached is None:
            cached = build_tree_data(version)
            _cache[version] = cached
        return cached


def clear_cache() -> None:
    """Drop all cached tree data (tests)."""
    with _cache_lock:
        _cache.clear()


def tree_data_to_dict(td: TreeData) -> dict:
    """
    Convert TreeData to a plain JSON-able dict with compact keys.

    Layout::

        {
          "version": "3_29",
          "nodes": [
            {"i": id, "x": x, "y": y, "n": name, "t": type, "a": ascendancy_or_null},
            ...
          ],
          "edges": [[a, b], ...],           # a < b, node ids, each undirected edge once
          "bounds": {"min_x", "min_y", "max_x", "max_y"},
          "class_starts": {"Marauder": id, ...}
        }

    Node keys: ``i`` id, ``x``/``y`` position rounded to one decimal, ``n``
    name, ``t`` type (one of NODE_TYPES), ``a`` ascendancy name or null.
    """
    return {
        "version": td.version,
        "nodes": [
            {
                "i": n.id,
                "x": round(n.x, 1),
                "y": round(n.y, 1),
                "n": n.name,
                "t": n.type,
                "a": n.ascendancy,
            }
            for n in td.nodes
        ],
        "edges": [list(e) for e in td.edges],
        "bounds": {k: round(v, 1) for k, v in td.bounds.items()},
        "class_starts": dict(td.class_starts),
    }

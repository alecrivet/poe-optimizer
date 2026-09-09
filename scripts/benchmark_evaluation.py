#!/usr/bin/env python3
"""
Benchmark the evaluation paths on the fixture build.

Prints the numbers quoted in docs/PERFORMANCE.md so they can be reproduced:

  - luajit worker start-up
  - full reload evaluation (legacy path)
  - LOAD / SET / DELTA (session protocol)
  - pool throughput for a batch of deltas across N workers

Usage:
    venv/bin/python3 scripts/benchmark_evaluation.py [--workers N] [--build path.xml]
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pob.modifier import get_passive_tree_summary  # noqa: E402
from src.pob.worker_pool import PoBWorker, PoBWorkerPool, TreeDelta  # noqa: E402


def timed(label, fn):
    t = time.perf_counter()
    result = fn()
    dt = time.perf_counter() - t
    print(f"{label:<44} {dt*1000:8.0f} ms")
    return result, dt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--build", type=Path,
                        default=Path(__file__).parent.parent / "tests/fixtures/builds/cyclone_slayer.xml")
    parser.add_argument("--deltas", type=int, default=40)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    xml = args.build.read_text()
    summary = get_passive_tree_summary(xml)
    nodes = sorted(summary["allocated_nodes"])
    masteries = summary["mastery_effects"]

    print(f"Build: {args.build.name} ({len(nodes)} nodes listed, {len(masteries)} masteries)\n")

    print("-- single worker --")
    worker = PoBWorker(worker_id=0)
    timed("worker start (PoB init)", worker.start)
    for i in range(2):
        r, _ = timed(f"full reload evaluate #{i+1}", lambda: worker.evaluate(xml))
        assert r.success, r.error
    r, _ = timed("LOAD (session base)", lambda: worker.load_session(xml))
    assert r.success, r.error
    print(f"{'':<44} points used: {r.points_used}, DPS {r.stats['combinedDPS']:,.0f}")
    for i in range(3):
        r, _ = timed(f"DELTA remove node {nodes[i+1]}", lambda: worker.evaluate_delta(TreeDelta(remove=[nodes[i+1]])))
        assert r.success, r.error
    r, _ = timed("DELTA mastery change", lambda: worker.evaluate_delta(
        TreeDelta(masteries={next(iter(masteries)): 2498})))
    r, _ = timed("SET (commit tree without one node)", lambda: worker.set_tree(nodes[:1] + nodes[2:], masteries))
    assert r.success, r.error
    worker.stop()

    print(f"\n-- pool of {args.workers} workers --")
    pool = PoBWorkerPool(num_workers=args.workers)
    _, start_dt = timed("pool start", pool.start)
    r, _ = timed("load_session (broadcast)", lambda: pool.load_session(xml))
    assert r.success, r.error
    deltas = [TreeDelta(remove=[n]) for n in nodes[1:1 + args.deltas]]
    results, dt = timed(f"evaluate_deltas x{len(deltas)}", lambda: pool.evaluate_deltas(deltas))
    ok = sum(1 for x in results if x.success)
    print(f"{'':<44} {ok}/{len(deltas)} ok, {dt/len(deltas)*1000:.0f} ms per candidate effective")
    results, dt = timed(f"evaluate_batch (full reload) x{args.workers}", lambda: pool.evaluate_batch([xml] * args.workers))
    print(f"{'':<44} {dt/args.workers*1000:.0f} ms per build effective")
    pool.shutdown()


if __name__ == "__main__":
    main()

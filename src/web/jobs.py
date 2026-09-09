"""
Job runner for the local web UI.

Runs one optimisation at a time on a background thread, records every
iteration event so late subscribers can replay them, and exposes a
generator for Server-Sent Events.

The optimizer itself is untouched: this module only adapts
``GreedyTreeOptimizer.optimize(..., on_iteration=..., should_cancel=...)``
(contract in docs/plans/2026-09-frontend.md) to a job model.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

OBJECTIVES = ("dps", "life", "ehp", "balanced")


@dataclass
class JobOptions:
    objective: str = "dps"
    allow_point_change: bool = False
    max_point_change: int = 5
    iterations: int = 15
    workers: Optional[int] = None
    min_improvement: float = 0.1

    def validate(self) -> None:
        if self.objective not in OBJECTIVES:
            raise ValueError(f"objective must be one of {OBJECTIVES}")
        if not 1 <= self.iterations <= 100:
            raise ValueError("iterations must be between 1 and 100")
        if not 0 <= self.max_point_change <= 20:
            raise ValueError("max_point_change must be between 0 and 20")


@dataclass
class JobResult:
    before: Dict[str, float]
    after: Dict[str, float]
    change_pct: Dict[str, float]
    changes: List[Dict[str, Any]]
    original_nodes: List[int]
    final_nodes: List[int]
    original_masteries: Dict[int, int]
    final_masteries: Dict[int, int]
    points_before: int
    points_after: int
    tree_version: Optional[str]
    pob_code: str
    xml: str
    cancelled: bool
    elapsed_s: float
    iterations: int
    constraint_violations: List[str]


@dataclass
class Job:
    id: str
    build_xml: str
    options: JobOptions
    status: str = "queued"          # queued | running | done | error | cancelled
    error: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[JobResult] = None
    created: float = field(default_factory=time.time)
    started: Optional[float] = None
    finished: Optional[float] = None
    cancel_requested: bool = False
    cond: threading.Condition = field(default_factory=threading.Condition)

    def push(self, event: Dict[str, Any]) -> None:
        with self.cond:
            self.events.append(event)
            self.cond.notify_all()

    def finish(self, status: str, error: Optional[str] = None) -> None:
        with self.cond:
            self.status = status
            self.error = error
            self.finished = time.time()
            self.cond.notify_all()


class JobRunner:
    """
    Sequential job queue with a single background worker thread.

    Local use only: one optimisation at a time is the right default because
    each run pins most of the machine's cores.
    """

    def __init__(self, workers: Optional[int] = None, max_history: int = 20):
        self.workers = workers
        self.max_history = max_history
        self._jobs: Dict[str, Job] = {}
        self._queue: List[str] = []
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="poe-optimizer-jobs", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop = True
        self._wake.set()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def submit(self, build_xml: str, options: JobOptions) -> str:
        options.validate()
        self.start()
        job = Job(id=uuid.uuid4().hex[:12], build_xml=build_xml, options=options)
        with self._lock:
            self._jobs[job.id] = job
            self._queue.append(job.id)
            self._trim_history()
        job.push({"type": "queued", "position": self._position(job.id)})
        self._wake.set()
        return job.id

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def result(self, job_id: str) -> Optional[JobResult]:
        job = self._jobs.get(job_id)
        return job.result if job else None

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None:
            return False
        with self._lock:
            if job.id in self._queue:
                self._queue.remove(job.id)
                job.finish("cancelled")
                job.push({"type": "cancelled"})
                return True
        job.cancel_requested = True
        return True

    def events(self, job_id: str, timeout: float = 15.0) -> Iterator[Dict[str, Any]]:
        """
        Yield every event for a job, replaying history first, then blocking
        for new ones until the job reaches a terminal state.

        A ``{"type": "ping"}`` is yielded every ``timeout`` seconds while
        waiting so the HTTP connection stays alive.
        """
        job = self._jobs.get(job_id)
        if job is None:
            yield {"type": "error", "message": "Unknown job"}
            return
        idx = 0
        while True:
            with job.cond:
                while idx >= len(job.events) and job.status in ("queued", "running"):
                    if not job.cond.wait(timeout):
                        break
                batch = job.events[idx:]
                idx = len(job.events)
                terminal = job.status not in ("queued", "running")
            if batch:
                for ev in batch:
                    yield ev
            else:
                yield {"type": "ping"}
            if terminal and idx >= len(job.events):
                return

    def snapshot(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return {
            "id": job.id,
            "status": job.status,
            "error": job.error,
            "options": asdict(job.options),
            "created": job.created,
            "started": job.started,
            "finished": job.finished,
            "events": job.events,
            "result": asdict(job.result) if job.result else None,
        }

    # ------------------------------------------------------------------ #
    # Worker loop
    # ------------------------------------------------------------------ #

    def _position(self, job_id: str) -> int:
        with self._lock:
            return self._queue.index(job_id) if job_id in self._queue else 0

    def _trim_history(self) -> None:
        finished = [j for j in self._jobs.values() if j.status not in ("queued", "running")]
        finished.sort(key=lambda j: j.finished or 0)
        while len(finished) > self.max_history:
            old = finished.pop(0)
            self._jobs.pop(old.id, None)

    def _loop(self) -> None:
        while not self._stop:
            self._wake.wait(timeout=1.0)
            self._wake.clear()
            while not self._stop:
                with self._lock:
                    if not self._queue:
                        break
                    job_id = self._queue.pop(0)
                job = self._jobs.get(job_id)
                if job is None:
                    continue
                self._run(job)

    def _run(self, job: Job) -> None:
        from src.optimizer.tree_optimizer import GreedyTreeOptimizer
        from src.pob.codec import encode_pob_code
        from src.pob.modifier import get_passive_tree_summary

        job.status = "running"
        job.started = time.time()
        job.push({"type": "started"})
        optimizer = None
        try:
            opts = job.options
            optimizer = GreedyTreeOptimizer(
                max_iterations=opts.iterations,
                min_improvement=opts.min_improvement,
                max_points_change=opts.max_point_change,
                max_workers=self.workers,
                show_progress=False,
            )

            def on_iteration(ev) -> None:
                job.push({"type": "iteration", **_event_to_dict(ev)})

            result = optimizer.optimize(
                job.build_xml,
                objective=opts.objective,
                allow_point_increase=opts.allow_point_change,
                on_iteration=on_iteration,
                should_cancel=lambda: job.cancel_requested,
            )

            original = get_passive_tree_summary(job.build_xml)
            final = get_passive_tree_summary(result.optimized_xml)
            before = _stats(result.optimized_stats, "baseline")
            after = _stats(result.optimized_stats, "estimated")
            job.result = JobResult(
                before=before,
                after=after,
                change_pct={
                    "dps": result.optimized_stats.dps_change_percent,
                    "life": result.optimized_stats.life_change_percent,
                    "ehp": result.optimized_stats.ehp_change_percent,
                },
                changes=list(result.modifications_applied),
                original_nodes=sorted(original["allocated_nodes"]),
                final_nodes=sorted(getattr(result, "final_nodes", None) or final["allocated_nodes"]),
                original_masteries=dict(original["mastery_effects"]),
                final_masteries=dict(getattr(result, "final_masteries", None) or final["mastery_effects"]),
                points_before=_points(job.build_xml),
                points_after=_points(result.optimized_xml),
                tree_version=final.get("tree_version"),
                pob_code=encode_pob_code(result.optimized_xml),
                xml=result.optimized_xml,
                cancelled=bool(getattr(result, "cancelled", False)),
                elapsed_s=time.time() - job.started,
                iterations=result.iterations,
                constraint_violations=list(getattr(result, "constraint_violations", []) or []),
            )
            job.finish("cancelled" if job.result.cancelled else "done")
            job.push({"type": "done", "cancelled": job.result.cancelled,
                      "change_pct": job.result.change_pct, "elapsed_s": job.result.elapsed_s})
        except Exception as e:  # surface to the browser; the server keeps running
            logger.exception("Job %s failed", job.id)
            job.finish("error", str(e))
            job.push({"type": "error", "message": str(e)})
        finally:
            if optimizer is not None:
                try:
                    optimizer.shutdown()
                except Exception:
                    logger.debug("optimizer shutdown failed", exc_info=True)


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #

def _event_to_dict(ev) -> Dict[str, Any]:
    """Serialise an IterationEvent (or any object with those attributes)."""
    if hasattr(ev, "__dataclass_fields__"):
        d = asdict(ev)
    else:
        d = dict(ev) if isinstance(ev, dict) else vars(ev)
    d["removed"] = [list(x) for x in d.get("removed", [])]
    d["added"] = [list(x) for x in d.get("added", [])]
    d["masteries"] = {str(k): v for k, v in (d.get("masteries") or {}).items()}
    return d


def _stats(ev, prefix: str) -> Dict[str, float]:
    return {
        "dps": getattr(ev, f"{prefix}_dps"),
        "life": getattr(ev, f"{prefix}_life"),
        "ehp": getattr(ev, f"{prefix}_ehp"),
    }


def _points(xml: str) -> int:
    from src.optimizer.constraints import count_passive_points_in_xml
    try:
        return count_passive_points_in_xml(xml)
    except Exception:
        return 0

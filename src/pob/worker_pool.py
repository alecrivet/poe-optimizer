"""
PoB Worker Pool - Persistent subprocess pool for fast build evaluation.

This module provides a pool of long-running PoB worker processes that can
evaluate builds without the overhead of subprocess initialization each time.

Each worker runs ``evaluator_batch.lua`` which:

1. Initialises PoB once (~2 s).
2. Serves requests over stdin/stdout for the life of the process.

Two evaluation modes are supported:

* **Full reload** (``evaluate``): send a whole build XML, PoB reparses
  everything (items, gems, tree) and recalculates. ~3-5 s per build.
* **Session** (``load_session`` / ``set_tree`` / ``evaluate_delta``): load a
  build once, then evaluate passive-tree changes incrementally using PoB's own
  node-hover calculator. ~0.2 s per candidate, ~0.5 s to commit a new base
  tree. Items, gems and config are fixed for the session.

Implementation notes
--------------------
* The worker's stdout is read as a raw, unbuffered byte stream with our own
  line splitting. Mixing ``select()`` with a buffered text pipe (the previous
  design) silently loses lines: the buffer slurps several lines, ``select``
  then reports "nothing to read" and the caller times out while the response
  sits in the buffer.
* Workers are handed out through an idle queue so N workers give N-way
  parallelism. There is no pool-wide lock around evaluation.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import select
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from typing import Callable, Dict, Iterable, List, Optional, Sequence, TypeVar

from .modifier import ensure_config_element

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class EvaluationResult:
    """Result from a worker evaluation."""
    success: bool
    stats: Optional[Dict] = None
    error: Optional[str] = None
    points_used: Optional[int] = None
    nodes: Optional[List[int]] = None  # resulting allocated node ids (session replies)


@dataclass
class TreeDelta:
    """A passive-tree modification relative to the session base tree."""
    add: Sequence[int] = field(default_factory=tuple)
    remove: Sequence[int] = field(default_factory=tuple)
    masteries: Optional[Dict[int, int]] = None

    def to_request(self) -> Dict:
        req: Dict = {}
        if self.add:
            req["add"] = [int(n) for n in self.add]
        if self.remove:
            req["remove"] = [int(n) for n in self.remove]
        if self.masteries:
            req["masteries"] = {str(int(k)): int(v) for k, v in self.masteries.items()}
        return req

    @property
    def is_empty(self) -> bool:
        return not self.add and not self.remove and not self.masteries


class WorkerProtocolError(RuntimeError):
    """Raised when a worker misbehaves (dies, times out, garbles output)."""


class PoBWorker:
    """
    A single persistent PoB worker subprocess.

    Not thread-safe by itself: the pool guarantees a worker is only used by
    one thread at a time by handing it out through an idle queue.
    """

    def __init__(
        self,
        worker_id: int,
        pob_path: Optional[Path] = None,
        lua_command: str = "luajit",
        startup_timeout: float = 60.0,
    ):
        self.worker_id = worker_id
        self.lua_command = lua_command
        self.startup_timeout = startup_timeout

        if pob_path is None:
            project_root = Path(__file__).parent.parent.parent
            pob_path = project_root / "PathOfBuilding"

        self.pob_path = Path(pob_path).resolve()
        self.pob_src_path = self.pob_path / "src"
        self.evaluator_script = Path(__file__).parent / "evaluator_batch.lua"

        self.process: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()
        self._is_ready = False
        self._is_dead = False
        self._buffer = b""
        self.session_loaded = False

    # ------------------------------------------------------------------ #
    # Process lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> bool:
        """Start the worker subprocess and wait for its ready signal."""
        if self.process is not None:
            logger.warning(f"Worker {self.worker_id} already started")
            return self._is_ready
        return self._spawn()

    def _spawn(self) -> bool:
        try:
            logger.debug(f"Starting worker {self.worker_id}...")
            self._buffer = b""
            self._is_ready = False
            self._is_dead = False
            self.session_loaded = False

            self.process = subprocess.Popen(
                [self.lua_command, str(self.evaluator_script)],
                cwd=str(self.pob_src_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,  # unbuffered: we do our own line splitting
            )

            start_time = time.time()
            data = self._read_json(self.startup_timeout)
            if data.get("ready"):
                self._is_ready = True
                logger.info(
                    f"Worker {self.worker_id} ready (startup: {time.time() - start_time:.2f}s)"
                )
                return True
            logger.error(f"Worker {self.worker_id} sent unexpected startup message: {data}")
            self._kill()
            return False
        except Exception as e:
            logger.error(f"Failed to start worker {self.worker_id}: {e}")
            self._kill()
            return False

    def restart(self) -> bool:
        """Kill (if needed) and restart the worker. Session state is lost."""
        with self.lock:
            logger.warning(f"Restarting worker {self.worker_id}...")
            self._kill()
            self.process = None
            ok = self._spawn()
            if ok:
                logger.warning(f"Worker {self.worker_id} restarted successfully")
            return ok

    def stop(self):
        """Stop the worker subprocess."""
        if self.process is None:
            return
        try:
            with self.lock:
                if self.process.poll() is None:
                    try:
                        self.process.stdin.write(b"EXIT\n")
                        self.process.stdin.flush()
                        self.process.wait(timeout=2.0)
                    except Exception:
                        pass
                self._kill()
            logger.debug(f"Worker {self.worker_id} stopped")
        except Exception as e:
            logger.warning(f"Error stopping worker {self.worker_id}: {e}")
        finally:
            self.process = None
            self._is_ready = False
            self._is_dead = True
            self.session_loaded = False

    def _kill(self):
        proc = self.process
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=2.0)
        except Exception:
            pass
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream:
                    stream.close()
            except Exception:
                pass
        self._is_ready = False
        self._is_dead = True
        self.session_loaded = False

    @property
    def is_alive(self) -> bool:
        return (
            self.process is not None
            and self.process.poll() is None
            and self._is_ready
            and not self._is_dead
        )

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Low-level protocol
    # ------------------------------------------------------------------ #

    def _read_line(self, timeout: float) -> bytes:
        """Read one line from the worker's stdout with a timeout."""
        deadline = time.time() + timeout
        while True:
            nl = self._buffer.find(b"\n")
            if nl >= 0:
                line = self._buffer[:nl]
                self._buffer = self._buffer[nl + 1:]
                return line

            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError("Evaluation timeout")
            if self.process is None or self.process.poll() is not None:
                raise WorkerProtocolError("Worker died")

            ready, _, _ = select.select([self.process.stdout], [], [], min(remaining, 1.0))
            if not ready:
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise WorkerProtocolError("Worker closed stdout")
            self._buffer += chunk

    def _read_json(self, timeout: float) -> Dict:
        """Read lines until one parses as a JSON object."""
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError("Evaluation timeout")
            raw = self._read_line(remaining).strip()
            if not raw.startswith(b"{"):
                # Tolerate stray non-protocol output
                continue
            try:
                return json.loads(raw.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                logger.debug(f"Worker {self.worker_id}: ignoring unparsable line {raw[:120]!r}")
                continue

    def _request(self, line: str, timeout: float) -> Dict:
        """
        Send one request line and return the JSON reply.

        On timeout or protocol error the worker is marked dead: a late reply
        would otherwise be mis-attributed to the next request.
        """
        if not self._is_ready or self._is_dead:
            raise WorkerProtocolError("Worker not ready")
        with self.lock:
            try:
                self.process.stdin.write(line.encode("utf-8") + b"\n")
                self.process.stdin.flush()
                return self._read_json(timeout)
            except (TimeoutError, WorkerProtocolError, OSError, ValueError) as e:
                logger.error(f"Worker {self.worker_id} request failed: {e}")
                self._kill()
                raise WorkerProtocolError(str(e)) from e

    @staticmethod
    def _to_result(data: Dict) -> EvaluationResult:
        if data.get("success"):
            nodes = data.get("nodes")
            return EvaluationResult(
                success=True,
                stats=data.get("stats", {}),
                points_used=data.get("pointsUsed"),
                nodes=[int(n) for n in nodes] if isinstance(nodes, list) else None,
            )
        return EvaluationResult(success=False, error=data.get("error", "Unknown error"))

    # ------------------------------------------------------------------ #
    # Public evaluation API
    # ------------------------------------------------------------------ #

    def evaluate(self, build_xml: str, timeout: float = 60.0) -> EvaluationResult:
        """Full-reload evaluation of a build XML (~3-5 s)."""
        try:
            encoded = base64.b64encode(ensure_config_element(build_xml).encode("utf-8")).decode("ascii")
            result = self._to_result(self._request(encoded, timeout))
            # A legacy full reload replaces any session build on the Lua side
            self.session_loaded = False
            return result
        except WorkerProtocolError as e:
            return EvaluationResult(success=False, error=str(e))

    def load_session(self, build_xml: str, timeout: float = 120.0) -> EvaluationResult:
        """Load a build as the session base and return its baseline stats."""
        try:
            encoded = base64.b64encode(ensure_config_element(build_xml).encode("utf-8")).decode("ascii")
            result = self._to_result(self._request("LOAD " + encoded, timeout))
            self.session_loaded = result.success
            return result
        except WorkerProtocolError as e:
            self.session_loaded = False
            return EvaluationResult(success=False, error=str(e))

    def set_tree(
        self,
        nodes: Iterable[int],
        masteries: Optional[Dict[int, int]] = None,
        timeout: float = 60.0,
    ) -> EvaluationResult:
        """Replace the session tree in place (~0.5 s) and return its stats."""
        req: Dict = {"nodes": [int(n) for n in nodes]}
        if masteries is not None:
            req["masteries"] = {str(int(k)): int(v) for k, v in masteries.items()}
        try:
            return self._to_result(self._request("SET " + json.dumps(req), timeout))
        except WorkerProtocolError as e:
            return EvaluationResult(success=False, error=str(e))

    def evaluate_delta(self, delta: TreeDelta, timeout: float = 60.0) -> EvaluationResult:
        """Evaluate a modification of the session tree without changing it (~0.2 s)."""
        try:
            return self._to_result(
                self._request("DELTA " + json.dumps(delta.to_request()), timeout)
            )
        except WorkerProtocolError as e:
            return EvaluationResult(success=False, error=str(e))

    def ping(self, timeout: float = 5.0) -> bool:
        """Check that the worker is alive and responsive."""
        if not self._is_ready or self._is_dead:
            return False
        acquired = self.lock.acquire(blocking=False)
        if not acquired:
            # Busy evaluating: alive.
            return True
        self.lock.release()
        try:
            return bool(self._request("PING", timeout).get("pong"))
        except WorkerProtocolError:
            return False


class PoBWorkerPool:
    """
    Pool of persistent PoB worker processes.

    Workers are distributed via an idle queue, so up to ``num_workers``
    evaluations run truly in parallel.

    Example:
        >>> pool = PoBWorkerPool(num_workers=4)
        >>> pool.start()
        >>> result = pool.evaluate(build_xml)
        >>> pool.shutdown()

    Session mode:
        >>> pool.load_session(build_xml)              # once, all workers
        >>> results = pool.evaluate_deltas([TreeDelta(remove=[123]), ...])
        >>> pool.set_tree(new_nodes, new_masteries)   # commit a new base
    """

    def __init__(
        self,
        num_workers: Optional[int] = None,
        pob_path: Optional[Path] = None,
        lua_command: str = "luajit",
    ):
        if num_workers is None:
            num_workers = os.cpu_count() or 4

        self.num_workers = max(1, num_workers)
        self.pob_path = pob_path
        self.lua_command = lua_command

        self.workers: List[PoBWorker] = []
        self._idle: Queue = Queue()
        self._started = False
        self._shutdown = False
        self._lock = threading.Lock()

        # Session state mirrored on every worker
        self._session_xml: Optional[str] = None
        self._session_nodes: Optional[List[int]] = None
        self._session_masteries: Optional[Dict[int, int]] = None

        logger.info(f"Initialized PoBWorkerPool with {self.num_workers} workers")

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> int:
        """Start all workers (in parallel). Returns the number that came up."""
        if self._started:
            return len([w for w in self.workers if w.is_alive])

        self._started = True
        results: List[Optional[PoBWorker]] = [None] * self.num_workers

        def start_worker(idx):
            worker = PoBWorker(
                worker_id=idx,
                pob_path=self.pob_path,
                lua_command=self.lua_command,
            )
            if worker.start():
                results[idx] = worker

        threads = [threading.Thread(target=start_worker, args=(i,)) for i in range(self.num_workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.workers = [w for w in results if w is not None]
        for w in self.workers:
            self._idle.put(w)

        if not self.workers:
            raise RuntimeError("Failed to start any PoB workers")

        logger.info(f"Started {len(self.workers)}/{self.num_workers} workers")
        return len(self.workers)

    def shutdown(self):
        """Shutdown all workers and clean up."""
        if self._shutdown:
            return
        self._shutdown = True
        logger.info("Shutting down worker pool...")
        for worker in self.workers:
            worker.stop()
        self.workers = []
        self._idle = Queue()
        logger.info("Worker pool shutdown complete")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Worker checkout
    # ------------------------------------------------------------------ #

    def _acquire(self, timeout: float) -> PoBWorker:
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise WorkerProtocolError("No worker available")
            try:
                worker = self._idle.get(timeout=min(remaining, 1.0))
            except Empty:
                if not any(w.is_alive or w._is_dead for w in self.workers):
                    raise WorkerProtocolError("No workers available")
                continue
            if worker.is_alive:
                return worker
            # Dead worker in the queue: try to bring it back
            if self._revive(worker):
                return worker
            # Could not revive; drop it and keep waiting for another one
            logger.warning(f"Dropping worker {worker.worker_id} (failed to restart)")
            with self._lock:
                if worker in self.workers:
                    self.workers.remove(worker)
            if not self.workers:
                raise WorkerProtocolError("All workers failed")

    def _release(self, worker: PoBWorker):
        if worker in self.workers and not self._shutdown:
            self._idle.put(worker)

    def _revive(self, worker: PoBWorker) -> bool:
        """Restart a dead worker and replay session state onto it."""
        try:
            if not worker.restart():
                return False
        except Exception as e:
            logger.error(f"Pool error restarting worker {worker.worker_id}: {e}")
            return False
        if self._session_xml is not None:
            res = worker.load_session(self._session_xml)
            if not res.success:
                logger.error(f"Worker {worker.worker_id}: session reload failed: {res.error}")
                return False
            if self._session_nodes is not None:
                res = worker.set_tree(self._session_nodes, self._session_masteries)
                if not res.success:
                    logger.error(f"Worker {worker.worker_id}: session tree replay failed: {res.error}")
                    return False
        logger.info(f"Pool restarted worker {worker.worker_id}")
        return True

    def _with_worker(self, fn: Callable[[PoBWorker], EvaluationResult], timeout: float) -> EvaluationResult:
        """Run ``fn`` on an idle worker, retrying once on a worker death."""
        if not self._started or self._shutdown:
            return EvaluationResult(success=False, error="Pool not started")
        if not self.workers:
            return EvaluationResult(success=False, error="No workers available")

        last_error = "All workers failed"
        for _ in range(2):
            try:
                worker = self._acquire(timeout)
            except WorkerProtocolError as e:
                return EvaluationResult(success=False, error=str(e))
            try:
                result = fn(worker)
            finally:
                self._release(worker)
            if result.success or worker.is_alive:
                return result
            last_error = result.error or last_error
        return EvaluationResult(success=False, error=last_error)

    def _map(self, items: Sequence[T], fn: Callable[[T], EvaluationResult]) -> List[EvaluationResult]:
        """Apply ``fn`` to every item using at most ``len(workers)`` threads."""
        if not items:
            return []
        width = max(1, min(len(self.workers) or 1, len(items)))
        with ThreadPoolExecutor(max_workers=width) as executor:
            return list(executor.map(fn, items))

    def _broadcast(self, fn: Callable[[PoBWorker], EvaluationResult]) -> List[EvaluationResult]:
        """Run ``fn`` on every worker in parallel (each worker exactly once)."""
        workers: List[PoBWorker] = []
        deadline = time.time() + 30.0
        while len(workers) < len(self.workers) and time.time() < deadline:
            try:
                w = self._idle.get(timeout=1.0)
            except Empty:
                continue
            if not w.is_alive and not w.restart():
                with self._lock:
                    if w in self.workers:
                        self.workers.remove(w)
                continue
            workers.append(w)
        try:
            with ThreadPoolExecutor(max_workers=max(1, len(workers))) as executor:
                return list(executor.map(fn, workers))
        finally:
            for w in workers:
                self._release(w)

    # ------------------------------------------------------------------ #
    # Full-reload API
    # ------------------------------------------------------------------ #

    def evaluate(self, build_xml: str, timeout: float = 60.0) -> EvaluationResult:
        """Evaluate a build XML on any idle worker (full reload)."""
        return self._with_worker(lambda w: w.evaluate(build_xml, timeout), timeout)

    def evaluate_batch(self, builds: List[str], timeout: float = 60.0) -> List[EvaluationResult]:
        """Evaluate many build XMLs in parallel. Results keep input order."""
        if not self._started or self._shutdown:
            return [EvaluationResult(success=False, error="Pool not started")] * len(builds)
        return self._map(builds, lambda xml: self.evaluate(xml, timeout))

    # ------------------------------------------------------------------ #
    # Session API
    # ------------------------------------------------------------------ #

    def load_session(self, build_xml: str, timeout: float = 120.0) -> EvaluationResult:
        """
        Load ``build_xml`` as the session base on every worker.

        Returns the baseline evaluation (from the first successful worker).
        """
        if not self._started:
            self.start()
        self._session_xml = build_xml
        self._session_nodes = None
        self._session_masteries = None
        results = self._broadcast(lambda w: w.load_session(build_xml, timeout))
        good = [r for r in results if r.success]
        if not good:
            err = results[0].error if results else "No workers"
            return EvaluationResult(success=False, error=f"Session load failed: {err}")
        if len(good) < len(results):
            logger.warning(f"Session loaded on {len(good)}/{len(results)} workers")
        return good[0]

    def set_tree(
        self,
        nodes: Iterable[int],
        masteries: Optional[Dict[int, int]] = None,
        timeout: float = 60.0,
    ) -> EvaluationResult:
        """Commit a new base tree on every worker. Returns its evaluation."""
        node_list = [int(n) for n in nodes]
        mastery_map = {int(k): int(v) for k, v in masteries.items()} if masteries else {}
        self._session_nodes = node_list
        self._session_masteries = mastery_map
        results = self._broadcast(lambda w: w.set_tree(node_list, mastery_map, timeout))
        good = [r for r in results if r.success]
        if not good:
            err = results[0].error if results else "No workers"
            return EvaluationResult(success=False, error=f"Set tree failed: {err}")
        return good[0]

    def evaluate_delta(self, delta: TreeDelta, timeout: float = 60.0) -> EvaluationResult:
        """Evaluate one delta against the session tree on any idle worker."""
        return self._with_worker(lambda w: w.evaluate_delta(delta, timeout), timeout)

    def evaluate_deltas(self, deltas: Sequence[TreeDelta], timeout: float = 60.0) -> List[EvaluationResult]:
        """Evaluate many deltas in parallel. Results keep input order."""
        if not self._started or self._shutdown:
            return [EvaluationResult(success=False, error="Pool not started")] * len(deltas)
        return self._map(deltas, lambda d: self.evaluate_delta(d, timeout))

    def evaluate_trees(
        self,
        trees: Sequence[Sequence[int]],
        masteries: Optional[Sequence[Optional[Dict[int, int]]]] = None,
        timeout: float = 60.0,
    ) -> List[EvaluationResult]:
        """
        Evaluate many complete trees (node lists) against the session build.

        Uses SET on whichever worker picks up each tree, so after this call
        the workers' base trees differ; call ``set_tree`` before using
        ``evaluate_delta`` again.
        """
        if not self._started or self._shutdown:
            return [EvaluationResult(success=False, error="Pool not started")] * len(trees)
        if masteries is None:
            masteries = [None] * len(trees)
        items = list(zip(trees, masteries))

        def run(item):
            nodes, mast = item
            return self._with_worker(lambda w: w.set_tree(nodes, mast, timeout), timeout)

        results = self._map(items, run)
        # Workers now hold arbitrary trees; forget the committed base.
        self._session_nodes = None
        self._session_masteries = None
        return results

    @property
    def session_loaded(self) -> bool:
        return self._session_xml is not None

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def get_stats(self) -> Dict:
        alive = sum(1 for w in self.workers if w.is_alive)
        return {
            "total_workers": len(self.workers),
            "alive_workers": alive,
            "dead_workers": len(self.workers) - alive,
        }

    def health_check(self) -> Dict:
        """Ping every worker and restart any that are dead."""
        if not self._started or self._shutdown:
            return {"error": "Pool not started or shutting down"}

        alive_count = dead_count = restarted_count = restart_failed_count = 0
        for worker in list(self.workers):
            if worker.is_alive and worker.ping():
                alive_count += 1
                continue
            dead_count += 1
            if self._revive(worker):
                restarted_count += 1
                alive_count += 1
                dead_count -= 1
            else:
                restart_failed_count += 1

        stats = {
            "total_workers": len(self.workers),
            "alive_workers": alive_count,
            "dead_workers": dead_count,
            "restarted_workers": restarted_count,
            "restart_failures": restart_failed_count,
        }
        if restarted_count:
            logger.info(f"Health check: restarted {restarted_count} workers")
        if restart_failed_count:
            logger.warning(f"Health check: {restart_failed_count} workers failed to restart")
        return stats

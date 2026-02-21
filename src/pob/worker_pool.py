"""
PoB Worker Pool - Persistent subprocess pool for fast build evaluation.

This module provides a pool of long-running PoB worker processes that can
evaluate builds without the overhead of subprocess initialization each time.

The workers use evaluator_batch.lua which:
1. Initializes PoB once (expensive)
2. Loops on stdin waiting for base64-encoded build XMLs
3. Outputs JSON stats for each build

This reduces per-evaluation overhead from ~600ms to ~100ms.
"""

import base64
import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result from a batch evaluation."""
    success: bool
    stats: Optional[Dict] = None
    error: Optional[str] = None


class PoBWorker:
    """
    A single persistent PoB worker subprocess.

    The worker starts a luajit process running evaluator_batch.lua,
    which initializes PoB once and then processes builds via stdin/stdout.
    """

    def __init__(
        self,
        worker_id: int,
        pob_path: Optional[Path] = None,
        lua_command: str = "luajit",
        startup_timeout: float = 30.0,
    ):
        """
        Initialize a PoB worker.

        Args:
            worker_id: Unique identifier for this worker
            pob_path: Path to PathOfBuilding directory
            lua_command: Lua command to use (luajit recommended)
            startup_timeout: Max time to wait for worker initialization
        """
        self.worker_id = worker_id
        self.lua_command = lua_command
        self.startup_timeout = startup_timeout

        # Set paths
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

    def start(self) -> bool:
        """
        Start the worker subprocess.

        Returns:
            True if worker started and is ready, False otherwise
        """
        if self.process is not None:
            logger.warning(f"Worker {self.worker_id} already started")
            return self._is_ready

        try:
            logger.debug(f"Starting worker {self.worker_id}...")

            self.process = subprocess.Popen(
                [self.lua_command, str(self.evaluator_script)],
                cwd=str(self.pob_src_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Wait for ready signal
            start_time = time.time()
            while time.time() - start_time < self.startup_timeout:
                if self.process.poll() is not None:
                    # Process died during startup
                    stderr = self.process.stderr.read() if self.process.stderr else ""
                    logger.error(f"Worker {self.worker_id} died during startup: {stderr[:500]}")
                    self._is_dead = True
                    return False

                # Try to read ready signal
                line = self.process.stdout.readline()
                if not line:
                    continue

                line = line.strip()
                if not line or not line.startswith('{'):
                    # Skip non-JSON debug output from PoB
                    continue

                try:
                    data = json.loads(line)
                    if data.get("ready"):
                        self._is_ready = True
                        logger.info(f"Worker {self.worker_id} ready (startup: {time.time() - start_time:.2f}s)")
                        return True
                except json.JSONDecodeError:
                    continue

            logger.error(f"Worker {self.worker_id} startup timeout")
            self.stop()
            return False

        except Exception as e:
            logger.error(f"Failed to start worker {self.worker_id}: {e}")
            self._is_dead = True
            return False

    def evaluate(self, build_xml: str, timeout: float = 30.0) -> EvaluationResult:
        """
        Evaluate a build using this worker.

        Args:
            build_xml: The build XML to evaluate
            timeout: Max time to wait for evaluation

        Returns:
            EvaluationResult with stats or error
        """
        if not self._is_ready or self._is_dead:
            return EvaluationResult(success=False, error="Worker not ready")

        with self.lock:
            try:
                # Encode XML as base64 to avoid newline issues
                encoded = base64.b64encode(build_xml.encode('utf-8')).decode('ascii')

                # Send to worker
                self.process.stdin.write(encoded + '\n')
                self.process.stdin.flush()

                # Read response (with timeout via select would be better)
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.process.poll() is not None:
                        self._is_dead = True
                        return EvaluationResult(success=False, error="Worker died")

                    line = self.process.stdout.readline()
                    if not line:
                        continue

                    line = line.strip()
                    if not line or not line.startswith('{'):
                        # Skip non-JSON debug output from PoB
                        continue

                    try:
                        data = json.loads(line)
                        if data.get("success"):
                            return EvaluationResult(
                                success=True,
                                stats=data.get("stats", {})
                            )
                        elif "success" in data:
                            return EvaluationResult(
                                success=False,
                                error=data.get("error", "Unknown error")
                            )
                        # Skip other JSON (like pong, exit, etc)
                    except json.JSONDecodeError:
                        continue

                return EvaluationResult(success=False, error="Evaluation timeout")

            except Exception as e:
                logger.error(f"Worker {self.worker_id} evaluation error: {e}")
                self._is_dead = True
                return EvaluationResult(success=False, error=str(e))

    def ping(self, timeout: float = 5.0) -> bool:
        """
        Check if worker is alive and responsive.

        Uses non-blocking lock acquisition to avoid contention with
        long-running evaluations. If the lock is held, the worker is
        busy evaluating (i.e., alive), so we return True immediately.
        """
        if not self._is_ready or self._is_dead:
            return False

        # Non-blocking try-lock: if the worker is busy evaluating,
        # the lock will be held and we know it's alive.
        acquired = self.lock.acquire(blocking=False)
        if not acquired:
            # Worker is busy with an evaluation - it's alive
            return True

        try:
            self.process.stdin.write("PING\n")
            self.process.stdin.flush()

            start_time = time.time()
            while time.time() - start_time < timeout:
                line = self.process.stdout.readline()
                if line:
                    data = json.loads(line.strip())
                    return data.get("pong", False)
            return False
        except Exception:
            self._is_dead = True
            return False
        finally:
            self.lock.release()

    def stop(self):
        """Stop the worker subprocess."""
        if self.process is None:
            return

        try:
            with self.lock:
                if self.process.poll() is None:
                    # Try graceful exit
                    try:
                        self.process.stdin.write("EXIT\n")
                        self.process.stdin.flush()
                        self.process.wait(timeout=2.0)
                    except Exception:
                        pass

                    # Force kill if still running
                    if self.process.poll() is None:
                        self.process.kill()
                        self.process.wait(timeout=1.0)

            logger.debug(f"Worker {self.worker_id} stopped")
        except Exception as e:
            logger.warning(f"Error stopping worker {self.worker_id}: {e}")
        finally:
            self.process = None
            self._is_ready = False
            self._is_dead = True


    def restart(self) -> bool:
        """
        Restart a dead worker by killing the old process and creating a new one.

        Returns:
            True if worker restarted successfully, False otherwise
        """
        with self.lock:
            logger.warning(f"Restarting worker {self.worker_id}...")

            # Kill old process if still running
            if self.process is not None:
                try:
                    if self.process.poll() is None:
                        self.process.kill()
                        self.process.wait(timeout=5.0)
                except Exception as e:
                    logger.warning(f"Error killing old process for worker {self.worker_id}: {e}")
                self.process = None

            # Reset state
            self._is_dead = False
            self._is_ready = False

            # Start a new subprocess with the same command/args
            try:
                self.process = subprocess.Popen(
                    [self.lua_command, str(self.evaluator_script)],
                    cwd=str(self.pob_src_path),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                )

                # Wait for ready signal (same as in start())
                start_time = time.time()
                while time.time() - start_time < self.startup_timeout:
                    if self.process.poll() is not None:
                        stderr = self.process.stderr.read() if self.process.stderr else ""
                        logger.error(f"Worker {self.worker_id} died during restart: {stderr[:500]}")
                        self._is_dead = True
                        return False

                    line = self.process.stdout.readline()
                    if not line:
                        continue

                    line = line.strip()
                    if not line or not line.startswith('{'):
                        continue

                    try:
                        data = json.loads(line)
                        if data.get("ready"):
                            self._is_ready = True
                            logger.warning(
                                f"Worker {self.worker_id} restarted successfully "
                                f"(startup: {time.time() - start_time:.2f}s)"
                            )
                            return True
                    except json.JSONDecodeError:
                        continue

                logger.error(f"Worker {self.worker_id} restart timed out")
                self._is_dead = True
                if self.process and self.process.poll() is None:
                    self.process.kill()
                    self.process.wait(timeout=2.0)
                self.process = None
                return False

            except Exception as e:
                logger.error(f"Failed to restart worker {self.worker_id}: {e}")
                self._is_dead = True
                self.process = None
                return False

    @property
    def is_alive(self) -> bool:
        """Check if worker process is running."""
        return (
            self.process is not None
            and self.process.poll() is None
            and self._is_ready
            and not self._is_dead
        )

    def __del__(self):
        self.stop()


class PoBWorkerPool:
    """
    Pool of persistent PoB worker processes.

    Manages multiple workers and distributes evaluation jobs across them.
    Workers are started lazily and restarted if they die.

    Example:
        >>> pool = PoBWorkerPool(num_workers=4)
        >>> pool.start()
        >>> result = pool.evaluate(build_xml)
        >>> pool.shutdown()
    """

    def __init__(
        self,
        num_workers: Optional[int] = None,
        pob_path: Optional[Path] = None,
        lua_command: str = "luajit",
    ):
        """
        Initialize the worker pool.

        Args:
            num_workers: Number of workers (defaults to CPU count)
            pob_path: Path to PathOfBuilding directory
            lua_command: Lua command to use
        """
        if num_workers is None:
            num_workers = os.cpu_count() or 4

        self.num_workers = num_workers
        self.pob_path = pob_path
        self.lua_command = lua_command

        self.workers: List[PoBWorker] = []
        self.job_queue: Queue = Queue()
        self._started = False
        self._shutdown = False
        self._worker_index = 0
        self._lock = threading.Lock()

        logger.info(f"Initialized PoBWorkerPool with {num_workers} workers")

    def start(self) -> int:
        """
        Start all workers in the pool.

        Returns:
            Number of workers successfully started
        """
        if self._started:
            return len([w for w in self.workers if w.is_alive])

        self._started = True
        successful = 0

        # Start workers in parallel for faster initialization
        threads = []
        results = [None] * self.num_workers

        def start_worker(idx):
            worker = PoBWorker(
                worker_id=idx,
                pob_path=self.pob_path,
                lua_command=self.lua_command,
            )
            if worker.start():
                results[idx] = worker

        for i in range(self.num_workers):
            t = threading.Thread(target=start_worker, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.workers = [w for w in results if w is not None]
        successful = len(self.workers)

        if successful == 0:
            raise RuntimeError("Failed to start any PoB workers")

        logger.info(f"Started {successful}/{self.num_workers} workers")
        return successful

    def evaluate(self, build_xml: str, timeout: float = 30.0) -> EvaluationResult:
        """
        Evaluate a build using an available worker.

        Uses round-robin scheduling to distribute work.

        Args:
            build_xml: The build XML to evaluate
            timeout: Max time to wait for evaluation

        Returns:
            EvaluationResult with stats or error
        """
        if not self._started or self._shutdown:
            return EvaluationResult(success=False, error="Pool not started")

        if not self.workers:
            return EvaluationResult(success=False, error="No workers available")

        # Round-robin worker selection with auto-restart of dead workers
        with self._lock:
            for _ in range(len(self.workers)):
                worker = self.workers[self._worker_index % len(self.workers)]
                self._worker_index += 1

                if not worker.is_alive and worker._is_dead:
                    # Try to restart the dead worker before skipping it
                    try:
                        if worker.restart():
                            logger.info(f"Pool restarted dead worker {worker.worker_id} on demand")
                        else:
                            logger.warning(f"Pool failed to restart worker {worker.worker_id}, skipping")
                            continue
                    except Exception as e:
                        logger.error(f"Pool error restarting worker {worker.worker_id}: {e}")
                        worker._is_dead = True
                        continue

                if worker.is_alive:
                    result = worker.evaluate(build_xml, timeout)
                    if result.success or not worker._is_dead:
                        return result
                    # Worker died during evaluation, try next one

        return EvaluationResult(success=False, error="All workers failed")

    def evaluate_batch(
        self,
        builds: List[str],
        timeout: float = 30.0,
    ) -> List[EvaluationResult]:
        """
        Evaluate multiple builds in parallel across workers.

        Args:
            builds: List of build XMLs to evaluate
            timeout: Max time per evaluation

        Returns:
            List of EvaluationResults in same order as input
        """
        if not self._started or self._shutdown:
            return [EvaluationResult(success=False, error="Pool not started")] * len(builds)

        results = [None] * len(builds)
        threads = []

        def eval_build(idx, xml):
            results[idx] = self.evaluate(xml, timeout)

        for i, xml in enumerate(builds):
            t = threading.Thread(target=eval_build, args=(i, xml))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        return results

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        alive = sum(1 for w in self.workers if w.is_alive)
        return {
            "total_workers": len(self.workers),
            "alive_workers": alive,
            "dead_workers": len(self.workers) - alive,
        }

    def health_check(self) -> Dict:
        """
        Check health of all workers and restart any dead ones.

        Returns:
            Dict with health check results including restart counts
        """
        if not self._started or self._shutdown:
            return {"error": "Pool not started or shutting down"}

        alive_count = 0
        dead_count = 0
        restarted_count = 0
        restart_failed_count = 0

        for worker in self.workers:
            if worker.is_alive:
                # Ping to verify the worker is truly responsive
                if worker.ping():
                    alive_count += 1
                else:
                    # Worker failed ping, it may have just died
                    dead_count += 1
                    try:
                        if worker.restart():
                            restarted_count += 1
                            alive_count += 1
                            dead_count -= 1
                        else:
                            restart_failed_count += 1
                    except Exception as e:
                        logger.error(f"Health check failed to restart worker {worker.worker_id}: {e}")
                        worker._is_dead = True
                        restart_failed_count += 1
            elif worker._is_dead:
                dead_count += 1
                # Try to restart dead workers
                try:
                    if worker.restart():
                        restarted_count += 1
                        alive_count += 1
                        dead_count -= 1
                    else:
                        restart_failed_count += 1
                except Exception as e:
                    logger.error(f"Health check failed to restart worker {worker.worker_id}: {e}")
                    worker._is_dead = True
                    restart_failed_count += 1

        stats = {
            "total_workers": len(self.workers),
            "alive_workers": alive_count,
            "dead_workers": dead_count,
            "restarted_workers": restarted_count,
            "restart_failures": restart_failed_count,
        }

        if restarted_count > 0:
            logger.info(f"Health check: restarted {restarted_count} workers")
        if restart_failed_count > 0:
            logger.warning(f"Health check: {restart_failed_count} workers failed to restart")

        return stats

    def shutdown(self):
        """Shutdown all workers and clean up."""
        if self._shutdown:
            return

        self._shutdown = True
        logger.info("Shutting down worker pool...")

        for worker in self.workers:
            worker.stop()

        self.workers = []
        logger.info("Worker pool shutdown complete")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False

    def __del__(self):
        self.shutdown()

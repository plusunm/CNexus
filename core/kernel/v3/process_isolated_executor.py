"""Process-isolated executor — picklable named tasks only (no runtime closures)."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.kernel.v3.warmup_task_registry import run_process_safe_task


@dataclass(frozen=True)
class ProcessRunResult:
    ok: bool
    value: Any = None
    status: str = "ok"
    error: Optional[str] = None
    layer: str = "process_isolated"


def _pool_worker_count() -> int:
    return max(1, min(4, int(os.environ.get("CNEXUS_V3_PROCESS_WORKERS", "2"))))


class ProcessIsolatedExecutor:
    def __init__(self, processes: Optional[int] = None) -> None:
        self._processes = processes or _pool_worker_count()
        self._pool: Optional[ProcessPoolExecutor] = None
        self._lock = threading.Lock()
        self._inflight = 0

    def _ensure_pool(self) -> ProcessPoolExecutor:
        with self._lock:
            if self._pool is None:
                self._pool = ProcessPoolExecutor(
                    max_workers=self._processes,
                    mp_context=None,
                )
            return self._pool

    def run_named(
        self,
        handler: str,
        *,
        timeout_s: float = 3.0,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ProcessRunResult:
        if timeout_s <= 0:
            return ProcessRunResult(ok=False, status="killed_timeout", layer="process_isolated")
        with self._lock:
            self._inflight += 1
        try:
            pool = self._ensure_pool()
            future = pool.submit(run_process_safe_task, handler, payload or {})
            value = future.result(timeout=timeout_s)
            return ProcessRunResult(ok=True, value=value, layer="process_isolated")
        except FuturesTimeoutError:
            return ProcessRunResult(ok=False, status="killed_timeout", layer="process_isolated")
        except Exception as exc:
            return ProcessRunResult(
                ok=False,
                status="failed",
                error=f"{exc.__class__.__name__}: {exc}",
                layer="process_isolated",
            )
        finally:
            with self._lock:
                self._inflight = max(0, self._inflight - 1)

    def is_idle(self) -> bool:
        with self._lock:
            return self._inflight == 0

    def shutdown(self) -> None:
        with self._lock:
            if self._pool is not None:
                self._pool.shutdown(wait=False, cancel_futures=True)
                self._pool = None


_executor: Optional[ProcessIsolatedExecutor] = None
_executor_lock = threading.Lock()


def get_process_executor() -> ProcessIsolatedExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ProcessIsolatedExecutor()
        return _executor

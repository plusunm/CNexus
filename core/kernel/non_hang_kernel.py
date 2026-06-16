"""Non-Hang Kernel v1 — bounded worker execution with wall-clock timeouts.

Python cannot forcibly kill threads; on timeout the caller stops waiting and the
orphan work may continue in the pool. Callers must treat timeout as skip/requeue.
"""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any, Callable, Optional

_DEFAULT_WORKERS = max(2, min(8, int(os.environ.get("CNEXUS_NON_HANG_WORKERS", "4"))))


@dataclass(frozen=True)
class NonHangResult:
    ok: bool
    value: Any = None
    status: str = "ok"
    error: Optional[str] = None


class NonHangKernel:
    def __init__(self, max_workers: int = _DEFAULT_WORKERS) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="cnexus-nonhang",
        )
        self._lock = threading.Lock()

    def run_bounded(
        self,
        fn: Callable[[], Any],
        *,
        timeout_s: float,
    ) -> NonHangResult:
        if timeout_s <= 0:
            return NonHangResult(ok=False, status="killed_timeout")
        future = self._executor.submit(fn)
        try:
            return NonHangResult(ok=True, value=future.result(timeout=timeout_s))
        except FuturesTimeoutError:
            return NonHangResult(ok=False, status="killed_timeout")
        except Exception as exc:
            return NonHangResult(ok=False, status="failed", error=f"{exc.__class__.__name__}: {exc}")

    def shutdown(self, *, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=not wait)


_shared: Optional[NonHangKernel] = None
_shared_lock = threading.Lock()


def get_non_hang_kernel() -> NonHangKernel:
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = NonHangKernel()
        return _shared

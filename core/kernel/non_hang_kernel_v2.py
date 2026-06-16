"""Non-Hang Kernel v2 — asyncio-safe bounded offload from the API event loop."""

from __future__ import annotations

import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Optional

_DEFAULT_WORKERS = max(2, min(16, int(os.environ.get("CNEXUS_NON_HANG_V2_WORKERS", "8"))))


@dataclass(frozen=True)
class NonHangAsyncResult:
    ok: bool
    value: Any = None
    status: str = "ok"
    error: Optional[str] = None


class NonHangKernelV2:
    def __init__(self, max_workers: int = _DEFAULT_WORKERS) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="cnexus-nh2")
        self._lock = threading.Lock()

    async def run_bounded_async(
        self,
        fn: Callable[[], Any],
        *,
        timeout_s: float = 3.0,
    ) -> NonHangAsyncResult:
        if timeout_s <= 0:
            return NonHangAsyncResult(ok=False, status="killed_timeout")
        loop = asyncio.get_running_loop()
        try:
            value = await asyncio.wait_for(
                loop.run_in_executor(self._pool, fn),
                timeout=timeout_s,
            )
            return NonHangAsyncResult(ok=True, value=value)
        except asyncio.TimeoutError:
            return NonHangAsyncResult(ok=False, status="killed_timeout")
        except Exception as exc:
            return NonHangAsyncResult(ok=False, status="failed", error=f"{exc.__class__.__name__}: {exc}")

    def shutdown(self, *, wait: bool = False) -> None:
        self._pool.shutdown(wait=wait, cancel_futures=not wait)


_shared_v2: Optional[NonHangKernelV2] = None
_shared_v2_lock = threading.Lock()


def get_non_hang_kernel_v2() -> NonHangKernelV2:
    global _shared_v2
    with _shared_v2_lock:
        if _shared_v2 is None:
            _shared_v2 = NonHangKernelV2()
        return _shared_v2

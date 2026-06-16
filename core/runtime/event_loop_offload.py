"""Event-loop offload helpers — Non-Hang Kernel v2."""

from __future__ import annotations

import os
from typing import Any, Callable, TypeVar

from core.kernel.non_hang_kernel_v2 import get_non_hang_kernel_v2

T = TypeVar("T")


class EventLoopOffloadTimeout(RuntimeError):
    """Sync cognitive work exceeded bounded executor timeout on API thread."""


class EventLoopOffloadFailed(RuntimeError):
    """Sync cognitive work failed inside executor."""


def non_hang_v2_enabled() -> bool:
    flag = os.environ.get("CNEXUS_NON_HANG_V2", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def default_offload_timeout_s() -> float:
    raw = os.environ.get("CNEXUS_OFFLOAD_TIMEOUT_SEC", "120").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 120.0


async def offload_sync(
    fn: Callable[[], T],
    *,
    timeout_s: float | None = None,
) -> T:
    """Run sync runtime/cognitive callable off the event loop with bounded wait."""
    if not non_hang_v2_enabled():
        return fn()

    effective = default_offload_timeout_s() if timeout_s is None else timeout_s
    result = await get_non_hang_kernel_v2().run_bounded_async(fn, timeout_s=effective)
    if result.ok:
        return result.value
    if result.status == "killed_timeout":
        raise EventLoopOffloadTimeout(f"offload exceeded {effective}s")
    raise EventLoopOffloadFailed(result.error or "offload failed")

"""Non-Hang system guard — policy hooks for control/cognitive boundary."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.runtime.l3_scheduler import L3GovernanceScheduler

logger = logging.getLogger(__name__)

L3_QUEUE_MAX = max(64, int(os.environ.get("CNEXUS_L3_QUEUE_MAX", "1024")))


def non_hang_kernel_enabled() -> bool:
    flag = os.environ.get("CNEXUS_NON_HANG_KERNEL", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def governance_inline_on_l3_allowed() -> bool:
    """Boot L3 must not run full governance cycles when non-hang is on."""
    if not non_hang_kernel_enabled():
        return os.environ.get("CNEXUS_BOOT_FULL_GOVERNANCE", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    return False


def l3_queue_within_limit(scheduler: "L3GovernanceScheduler") -> bool:
    return scheduler.queue_length() <= L3_QUEUE_MAX


def non_hang_v2_enabled() -> bool:
    flag = os.environ.get("CNEXUS_NON_HANG_V2", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def enforce_non_hang_policies(runtime: Optional[Any] = None) -> dict[str, Any]:
    """Startup policy snapshot — no blocking work."""
    report = {
        "non_hang_kernel": non_hang_kernel_enabled(),
        "non_hang_v2": non_hang_v2_enabled(),
        "non_hang_v3": non_hang_v3_enabled(),
        "non_hang_v4": non_hang_v4_enabled(),
        "non_hang_v5": non_hang_v5_enabled(),
        "l3_queue_max": L3_QUEUE_MAX,
        "governance_inline_on_l3": governance_inline_on_l3_allowed(),
        "runtime_pointer": runtime is not None,
        "event_loop_offload": non_hang_v2_enabled(),
        "force_executor_boundary": non_hang_v2_enabled(),
    }
    logger.info("Non-Hang Kernel policies active", extra=report)
    return report


def non_hang_v3_enabled() -> bool:
    from core.kernel.v3.system_guard_v3 import non_hang_v3_enabled as _v3

    return _v3()


def non_hang_v4_enabled() -> bool:
    from core.kernel.v4.system_guard_v4 import non_hang_v4_enabled as _v4

    return _v4()


def non_hang_v5_enabled() -> bool:
    from core.kernel.v5.system_guard_v5 import non_hang_v5_enabled as _v5

    return _v5()


def effective_non_hang_tier() -> str:
    """Highest active non-hang tier — only one worker stack may run."""
    if non_hang_v5_enabled():
        return "v5"
    if non_hang_v4_enabled():
        return "v4"
    if non_hang_v3_enabled():
        return "v3"
    if non_hang_v2_enabled():
        return "v2"
    return "v1"


def enforce_non_hang_event_loop(runtime: Optional[Any] = None) -> dict[str, Any]:
    """v2/v3/v4 event-loop protection contract — no cluster spin-up on startup."""
    tier = effective_non_hang_tier()
    report = enforce_non_hang_policies(runtime)
    report["effective_tier"] = tier
    report.update(
        {
            "block_sync_on_loop": non_hang_v2_enabled(),
            "watchdog_enabled": tier != "v1",
            "isolation": (
                "cross_machine_cluster_v5"
                if tier == "v5"
                else (
                    "deterministic_cluster_v4"
                    if tier == "v4"
                    else (
                        "process_event_bus_v3"
                        if tier == "v3"
                        else ("non_hang_v2" if tier == "v2" else "non_hang_v1")
                    )
                )
            ),
            "cluster_enforce_deferred": tier in ("v4", "v5"),
        }
    )
    if tier in ("v3", "v4", "v5"):
        from core.kernel.v3.system_guard_v3 import enforce_v3_guards

        report.update(enforce_v3_guards(runtime))
    return report

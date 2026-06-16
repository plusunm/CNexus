"""Non-Hang Kernel v3 guards — process + event-bus isolation flags."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def non_hang_v3_enabled() -> bool:
    flag = os.environ.get("CNEXUS_NON_HANG_V3", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def enforce_v3_guards(runtime: Optional[Any] = None) -> Dict[str, Any]:
    from core.kernel.v3.event_bus import get_event_bus
    from core.kernel.v3.governance_worker_v3 import get_governance_worker_v3
    from core.kernel.v3.process_isolated_executor import get_process_executor

    bus = get_event_bus()
    worker = get_governance_worker_v3()
    executor = get_process_executor()

    return {
        "non_hang_v3": non_hang_v3_enabled(),
        "sync_execution_forbidden": non_hang_v3_enabled(),
        "require_event_bus_for_all_l3": non_hang_v3_enabled(),
        "forbid_inline_governance": non_hang_v3_enabled(),
        "require_process_executor": non_hang_v3_enabled(),
        "runtime_pointer": runtime is not None,
        "bus_idle": bus.is_idle(),
        "worker_idle": worker.is_idle(),
        "process_executor_idle": executor.is_idle(),
        "isolation": "process_event_bus_v3",
    }

"""Non-Hang Kernel v4 guards — deterministic log + cluster constraints."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def non_hang_v4_enabled() -> bool:
    flag = os.environ.get("CNEXUS_NON_HANG_V4", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def enforce_v4(runtime: Optional[Any] = None) -> Dict[str, Any]:
    from core.kernel.v3.event_bus import get_event_bus
    from core.kernel.v4.cluster_runtime import get_cluster_runtime
    from core.kernel.v4.deterministic_log import get_deterministic_log
    from core.kernel.v4.replay_engine import get_replay_engine

    cluster = get_cluster_runtime()
    bus = get_event_bus()
    replay = get_replay_engine()

    return {
        "non_hang_v4": non_hang_v4_enabled(),
        "forbid_shared_state": non_hang_v4_enabled(),
        "require_append_only_log": non_hang_v4_enabled(),
        "force_replay_source_of_truth": non_hang_v4_enabled(),
        "disable_inline_governance": non_hang_v4_enabled(),
        "runtime_pointer": runtime is not None,
        "cluster_ok": cluster.cluster_healthy(),
        "bus_ok": bus.is_idle(),
        "replay_ok": replay.replay_consistent(),
        "log_seq": get_deterministic_log().last_seq(),
        "isolation": "deterministic_cluster_v4",
    }

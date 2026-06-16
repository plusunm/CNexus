"""Non-Hang Kernel v5 guards — CRDT + consensus + self-healing constraints."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def non_hang_v5_enabled() -> bool:
    flag = os.environ.get("CNEXUS_NON_HANG_V5", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def enforce_v5(runtime: Optional[Any] = None) -> Dict[str, Any]:
    from core.kernel.v5.crdt_memory import get_crdt_memory
    from core.kernel.v5.global_cluster_runtime import get_global_cluster_runtime

    cluster = get_global_cluster_runtime()
    crdt = get_crdt_memory()

    return {
        "non_hang_v5": non_hang_v5_enabled(),
        "forbid_single_node_truth": non_hang_v5_enabled(),
        "force_crdt_memory": non_hang_v5_enabled(),
        "enable_self_healing_cluster": non_hang_v5_enabled(),
        "require_consensus_before_write": non_hang_v5_enabled(),
        "runtime_pointer": runtime is not None,
        "cluster_ok": cluster.cluster_health(),
        "consensus_ok": cluster.consensus_stable(),
        "crdt_ok": cluster.crdt_consistent(),
        "crdt_clock": crdt.stats().get("clock"),
        "isolation": "cross_machine_cluster_v5",
    }

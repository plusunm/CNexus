"""Boot Protocol v5 — cross-machine cluster ready gate."""

from __future__ import annotations

from typing import Any, Dict, Optional


def system_ready(runtime: Optional[Any] = None) -> Dict[str, Any]:
    from core.kernel.v5.global_cluster_runtime import get_global_cluster_runtime

    cluster = get_global_cluster_runtime()
    cluster_ok = cluster.cluster_health()
    consensus_ok = cluster.consensus_stable()
    crdt_ok = cluster.crdt_consistent()

    if not (cluster_ok and consensus_ok and crdt_ok):
        return {
            "status": "warming",
            "layer": "v5",
            "cluster": cluster_ok,
            "consensus": consensus_ok,
            "crdt": crdt_ok,
            "runtime_pointer": runtime is not None,
        }

    return {
        "status": "ready",
        "layer": "v5",
        "isolation": "cross_machine_cluster_v5",
        "cluster": cluster_ok,
        "consensus": consensus_ok,
        "crdt": crdt_ok,
        "runtime_pointer": runtime is not None,
    }

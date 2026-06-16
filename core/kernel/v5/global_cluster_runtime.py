"""Global cluster runtime — CRDT + consensus front, v4 execution backend."""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from core.kernel.v5.cluster_consensus import ClusterConsensus
from core.kernel.v5.crdt_memory import CRDTMemory, get_crdt_memory

logger = logging.getLogger(__name__)


class GlobalClusterNode:
    """Logical cluster node — delegates execution to the v4 local cluster."""

    def __init__(self, node_id: int, backend: Any) -> None:
        self.node_id = node_id
        self._backend = backend
        self._healthy = True
        self._last_heartbeat_mono = time.monotonic()

    def enqueue(self, event: Dict[str, Any]) -> None:
        self._backend.submit(event)
        self._last_heartbeat_mono = time.monotonic()

    def heartbeat_ok(self) -> bool:
        if not self._healthy:
            return False
        return self._backend.cluster_healthy()

    def reset(self) -> None:
        self._healthy = True
        self._last_heartbeat_mono = time.monotonic()
        logger.info("GlobalClusterNode %s reset", self.node_id)

    def touch_heartbeat(self) -> None:
        self._last_heartbeat_mono = time.monotonic()


class GlobalClusterRuntime:
    def __init__(
        self,
        nodes: List[GlobalClusterNode],
        crdt: CRDTMemory,
        consensus: ClusterConsensus,
        *,
        backend: Any,
    ) -> None:
        self.nodes = nodes
        self.crdt = crdt
        self.consensus = consensus
        self._backend = backend
        self._lock = threading.Lock()

    def submit(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = str(event.get("id") or uuid.uuid4().hex)
        payload = {**event, "id": event_id}

        leader = self.consensus.leader
        if leader is None:
            leader = self.consensus.elect_leader()
        leader_id = getattr(leader, "node_id", leader)

        target_node = self._route(payload)
        target_node.enqueue(payload)

        self.crdt.merge(key=event_id, value=payload, node_id=leader_id)
        self.consensus.heartbeat(leader_id)
        return payload

    def _route(self, event: Dict[str, Any]) -> GlobalClusterNode:
        key = str(event.get("id") or "")
        digest = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
        return self.nodes[digest % len(self.nodes)]

    def cluster_health(self) -> bool:
        backend_ok = self._backend.cluster_healthy() and self._backend.queue_length() == 0
        nodes_ok = all(node.heartbeat_ok() for node in self.nodes)
        return backend_ok and nodes_ok

    def consensus_stable(self) -> bool:
        return self.consensus.is_stable()

    def crdt_consistent(self) -> bool:
        return self.crdt.is_consistent()

    def cluster_healthy(self) -> bool:
        return self.cluster_health()

    def queue_length(self) -> int:
        return self._backend.queue_length()

    def stats(self) -> Dict[str, Any]:
        return {
            "nodes": len(self.nodes),
            "backend": self._backend.stats(),
            "crdt": self.crdt.stats(),
            "consensus": self.consensus.stats(),
            "healthy": self.cluster_health(),
            "consensus_ok": self.consensus_stable(),
            "crdt_ok": self.crdt_consistent(),
        }


_global: Optional[GlobalClusterRuntime] = None
_global_lock = threading.Lock()


def get_global_cluster_runtime() -> GlobalClusterRuntime:
    global _global
    with _global_lock:
        if _global is None:
            from core.kernel.v4.cluster_runtime import get_cluster_runtime

            backend = get_cluster_runtime()
            node_count = max(1, min(8, int(os.environ.get("CNEXUS_V5_CLUSTER_NODES", "2"))))
            nodes = [GlobalClusterNode(i, backend) for i in range(node_count)]
            crdt = get_crdt_memory()
            consensus = ClusterConsensus(nodes)
            consensus.elect_leader()
            _global = GlobalClusterRuntime(nodes, crdt, consensus, backend=backend)
        return _global

"""Local cluster runtime — hash-routed nodes with deterministic log front."""

from __future__ import annotations

import hashlib
import logging
import queue
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from core.kernel.v4.deterministic_log import get_deterministic_log

logger = logging.getLogger(__name__)


class ClusterNode:
    def __init__(self, node_id: int, executor: "ClusterRuntime") -> None:
        self.node_id = node_id
        self._executor = executor
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
        self._active = 0
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name=f"cnexus-cluster-node-{node_id}",
            daemon=True,
        )
        self._thread.start()

    def enqueue(self, event: Dict[str, Any]) -> None:
        self._queue.put(event)

    def is_idle(self) -> bool:
        with self._lock:
            busy = self._active > 0
        return not busy and self._queue.empty()

    def _loop(self) -> None:
        while self._running:
            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            with self._lock:
                self._active += 1
            try:
                self._executor.dispatch_on_node(self.node_id, event)
            except Exception as exc:
                logger.warning("ClusterNode %s failed: %s", self.node_id, exc)
            finally:
                with self._lock:
                    self._active = max(0, self._active - 1)

    def stop(self) -> None:
        self._running = False


class ClusterRuntime:
    def __init__(self, node_count: int = 2) -> None:
        self.log = get_deterministic_log()
        self._node_count = max(1, node_count)
        self._nodes: List[ClusterNode] = [
            ClusterNode(i, self) for i in range(self._node_count)
        ]
        self._pending_labels: Dict[str, str] = {}
        self._completed: Dict[str, str] = {}
        self._lock = threading.Lock()

    def submit(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = str(event.get("id") or uuid.uuid4().hex)
        payload = {**event, "id": event_id}
        entry = self.log.append(payload)
        label = str(payload.get("label") or payload.get("handler") or event_id)
        with self._lock:
            self._pending_labels[event_id] = label
        node = self._route(payload)
        node.enqueue(payload)
        return entry

    def _route(self, event: Dict[str, Any]) -> ClusterNode:
        key = str(event.get("id") or "")
        digest = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
        idx = digest % len(self._nodes)
        return self._nodes[idx]

    def dispatch_on_node(self, node_id: int, event: Dict[str, Any]) -> Dict[str, Any]:
        from core.kernel.v3.governance_worker_v3 import get_governance_worker_v3

        worker = get_governance_worker_v3()
        worker._execute(event)
        event_id = str(event.get("id") or "")
        label = str(event.get("label") or event.get("handler") or event_id)
        with self._lock:
            self._completed[event_id] = label
            self._pending_labels.pop(event_id, None)
        return {"node_id": node_id, "event_id": event_id, "status": "ok"}

    def cluster_healthy(self) -> bool:
        return all(node.is_idle() for node in self._nodes)

    def queue_length(self) -> int:
        with self._lock:
            return len(self._pending_labels)

    def mark_completed(self, label: str) -> None:
        with self._lock:
            for event_id, pending_label in list(self._pending_labels.items()):
                if pending_label == label:
                    self._completed[event_id] = label
                    del self._pending_labels[event_id]
                    break

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            pending = len(self._pending_labels)
            completed = len(self._completed)
        return {
            "nodes": self._node_count,
            "pending": pending,
            "completed": completed,
            "log_seq": self.log.last_seq(),
            "healthy": self.cluster_healthy(),
        }


_cluster: Optional[ClusterRuntime] = None
_cluster_lock = threading.Lock()


def get_cluster_runtime() -> ClusterRuntime:
    global _cluster
    with _cluster_lock:
        if _cluster is None:
            import os

            nodes = max(1, min(4, int(os.environ.get("CNEXUS_V4_CLUSTER_NODES", "2"))))
            _cluster = ClusterRuntime(node_count=nodes)
        return _cluster

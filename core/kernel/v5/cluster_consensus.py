"""Cluster consensus — leader election and heartbeat for multi-node writes."""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any, List, Optional


class ClusterConsensus:
    def __init__(self, nodes: List[Any]) -> None:
        self.nodes = nodes
        self.leader: Optional[Any] = None
        self._lock = threading.Lock()
        self._last_election_mono = time.monotonic()

    def elect_leader(self) -> Any:
        with self._lock:
            if not self.nodes:
                return None
            digest = hashlib.sha256(repr([getattr(n, "node_id", i) for i, n in enumerate(self.nodes)]).encode()).hexdigest()
            idx = int(digest, 16) % len(self.nodes)
            self.leader = self.nodes[idx]
            self._last_election_mono = time.monotonic()
            return self.leader

    def heartbeat(self, node_id: Any) -> Optional[Any]:
        with self._lock:
            if self.leader is None:
                return self.elect_leader()
            leader_id = getattr(self.leader, "node_id", self.leader)
            if leader_id == node_id:
                self._last_election_mono = time.monotonic()
            return self.leader

    def is_stable(self) -> bool:
        with self._lock:
            return self.leader is not None

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            leader_id = None
            if self.leader is not None:
                leader_id = getattr(self.leader, "node_id", self.leader)
            return {
                "leader_id": leader_id,
                "node_count": len(self.nodes),
                "stable": self.is_stable(),
                "last_election_mono": self._last_election_mono,
            }

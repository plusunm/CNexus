"""Self-healing cluster — heartbeat recovery and leader re-election."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class SelfHealingCluster:
    def __init__(self, consensus: Any, nodes: List[Any]) -> None:
        self.consensus = consensus
        self.nodes = nodes
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="cnexus-self-healing-v5",
            daemon=True,
        )
        self._thread.start()
        logger.info("SelfHealingCluster v5 started")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            time.sleep(1.0)
            for node in self.nodes:
                if not node.heartbeat_ok():
                    self._recover(node)

    def _recover(self, node: Any) -> None:
        node.reset()
        self.consensus.elect_leader()
        logger.warning("SelfHealingCluster recovered node %s", getattr(node, "node_id", node))


_healing: Optional[SelfHealingCluster] = None
_healing_lock = threading.Lock()


def get_self_healing_cluster() -> SelfHealingCluster:
    global _healing
    with _healing_lock:
        if _healing is None:
            from core.kernel.v5.global_cluster_runtime import get_global_cluster_runtime

            runtime = get_global_cluster_runtime()
            _healing = SelfHealingCluster(runtime.consensus, runtime.nodes)
        return _healing


def start_self_healing_cluster() -> SelfHealingCluster:
    healing = get_self_healing_cluster()
    healing.start()
    return healing

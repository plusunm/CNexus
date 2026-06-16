"""Governance sidecar v4 — replay verification loop off control plane."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

from core.kernel.v4.replay_engine import get_replay_engine

logger = logging.getLogger(__name__)


def _replay_handler_l3_task(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "l3.task",
        "id": event.get("id"),
        "handler": event.get("handler"),
        "status": "replay_ok",
    }


class GovernanceSidecar:
    def __init__(self) -> None:
        self._replay = get_replay_engine()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="cnexus-governance-sidecar-v4", daemon=True)
        self._thread.start()
        logger.info("GovernanceSidecar v4 started")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        handler_map = {"l3.task": _replay_handler_l3_task}
        while self._running:
            self._replay.verify_consistent(handler_map)
            time.sleep(1.0)

    def handle_task(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return _replay_handler_l3_task(event)


_sidecar: Optional[GovernanceSidecar] = None
_sidecar_lock = threading.Lock()


def get_governance_sidecar() -> GovernanceSidecar:
    global _sidecar
    with _sidecar_lock:
        if _sidecar is None:
            _sidecar = GovernanceSidecar()
        return _sidecar


def start_governance_sidecar() -> GovernanceSidecar:
    sidecar = get_governance_sidecar()
    sidecar.start()
    return sidecar

"""Governance signal plane — enqueue only, execute in background worker."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List

_lock = threading.Lock()
_signals: Deque[Dict[str, Any]] = deque(maxlen=256)


def enqueue_governance_signal(signal: Dict[str, Any]) -> None:
    with _lock:
        _signals.append({**signal, "enqueued_at": time.time()})


def drain_governance_signals(*, limit: int = 32) -> List[Dict[str, Any]]:
    drained: List[Dict[str, Any]] = []
    with _lock:
        while _signals and len(drained) < limit:
            drained.append(_signals.popleft())
    return drained


def pending_governance_signal_count() -> int:
    with _lock:
        return len(_signals)

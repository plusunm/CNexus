"""Deterministic replay engine — verify log against handler map."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from core.kernel.v4.deterministic_log import DeterministicLog, get_deterministic_log

HandlerFn = Callable[[Dict[str, Any]], Any]


class ReplayEngine:
    def __init__(self, log: Optional[DeterministicLog] = None) -> None:
        self.log = log or get_deterministic_log()
        self._last_consistent = True
        self._last_results: List[Any] = []
        self._lock = threading.Lock()

    def replay(self, handler_map: Dict[str, HandlerFn]) -> List[Any]:
        results = self.log.replay(handler_map)
        with self._lock:
            self._last_results = results
        return results

    def verify_consistent(self, handler_map: Dict[str, HandlerFn]) -> bool:
        """Replay-only verification — handlers must be pure readers."""
        try:
            results = self.replay(handler_map)
            ok = all(r is not None for r in results) if results else True
            with self._lock:
                self._last_consistent = ok
            return ok
        except Exception:
            with self._lock:
                self._last_consistent = False
            return False

    def replay_consistent(self) -> bool:
        with self._lock:
            return self._last_consistent

    def last_results(self) -> List[Any]:
        with self._lock:
            return list(self._last_results)


_engine: Optional[ReplayEngine] = None
_engine_lock = threading.Lock()


def get_replay_engine() -> ReplayEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = ReplayEngine()
        return _engine

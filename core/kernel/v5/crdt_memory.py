"""CRDT memory — last-write-wins convergent state for cluster events."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional


class CRDTMemory:
    def __init__(self) -> None:
        self.state: Dict[str, Dict[str, Any]] = {}
        self.clock = 0
        self._lock = threading.Lock()
        self._last_merge_mono = time.monotonic()

    def merge(self, key: str, value: Any, node_id: Any) -> None:
        with self._lock:
            self.clock += 1
            self._last_merge_mono = time.monotonic()

            if key not in self.state:
                self.state[key] = {
                    "value": value,
                    "ts": self.clock,
                    "node": node_id,
                }
                return

            current = self.state[key]
            if self.clock >= current["ts"]:
                self.state[key] = {
                    "value": value,
                    "ts": self.clock,
                    "node": node_id,
                }

    def read(self, key: str) -> Any:
        with self._lock:
            return self.state.get(key, {}).get("value")

    def is_consistent(self) -> bool:
        """LWW CRDT has converged when every entry has monotonic logical clock."""
        with self._lock:
            if not self.state:
                return True
            return all(int(entry.get("ts") or 0) <= self.clock for entry in self.state.values())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            consistent = (
                all(int(entry.get("ts") or 0) <= self.clock for entry in self.state.values())
                if self.state
                else True
            )
            return {
                "clock": self.clock,
                "keys": len(self.state),
                "last_merge_mono": self._last_merge_mono,
                "consistent": consistent,
            }


_crdt: Optional[CRDTMemory] = None
_crdt_lock = threading.Lock()


def get_crdt_memory() -> CRDTMemory:
    global _crdt
    with _crdt_lock:
        if _crdt is None:
            _crdt = CRDTMemory()
        return _crdt

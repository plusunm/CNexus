"""Append-only deterministic event log — replay source of truth."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

HandlerFn = Callable[[Dict[str, Any]], Any]


class DeterministicLog:
    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._seq = 0
        self._persist_path: Optional[Path] = None

    def configure_persistence(self, base_dir: Optional[str]) -> None:
        if not base_dir:
            self._persist_path = None
            return
        path = Path(str(base_dir)) / "observability" / "deterministic_log.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path = path

    def append(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._seq += 1
            entry = {
                "seq": self._seq,
                "ts": time.time(),
                "event": dict(event),
            }
            self._entries.append(entry)
            if self._persist_path is not None:
                with self._persist_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return entry

    def entries(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._entries)

    def pending_after(self, seq: int) -> int:
        with self._lock:
            return max(0, self._seq - seq)

    def last_seq(self) -> int:
        with self._lock:
            return self._seq

    def dump(self) -> str:
        return json.dumps(self.entries(), ensure_ascii=False)

    def replay(self, handler_map: Dict[str, HandlerFn]) -> List[Any]:
        results: List[Any] = []
        for entry in self.entries():
            event = entry.get("event") or {}
            handler = handler_map.get(str(event.get("type") or ""))
            if handler is not None:
                results.append(handler(event))
        return results


_log: Optional[DeterministicLog] = None
_log_lock = threading.Lock()


def get_deterministic_log() -> DeterministicLog:
    global _log
    with _log_lock:
        if _log is None:
            _log = DeterministicLog()
        return _log

"""Execution Identity Store — identity → trace index with disk persistence."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Optional


class ExecutionIdentityStore:
    def __init__(self) -> None:
        self._index: dict[str, list[str]] = {}
        self._trace_to_identity: dict[str, str] = {}
        self._lock = threading.Lock()
        self._persist_path: Optional[Path] = None

    def set_persist_base(self, base_dir: str | Path) -> None:
        root = Path(base_dir) / "observability"
        root.mkdir(parents=True, exist_ok=True)
        self._persist_path = root / "execution_identity.jsonl"

    def register(self, identity: str, trace_id: str) -> None:
        with self._lock:
            traces = self._index.setdefault(identity, [])
            if trace_id not in traces:
                traces.append(trace_id)
            self._trace_to_identity[trace_id] = identity
        self._append_row({"identity": identity, "trace_id": trace_id, "ts": time.time()})

    def lookup(self, identity: str) -> list[str]:
        with self._lock:
            return list(self._index.get(identity, []))

    def identity_for_trace(self, trace_id: str) -> Optional[str]:
        with self._lock:
            return self._trace_to_identity.get(trace_id)

    def all_identities(self) -> dict[str, list[str]]:
        with self._lock:
            return {k: list(v) for k, v in self._index.items()}

    def hydrate_from_disk(self) -> int:
        if not self._persist_path or not self._persist_path.exists():
            return 0
        loaded = 0
        with self._lock:
            with open(self._persist_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    identity = str(row.get("identity") or "")
                    trace_id = str(row.get("trace_id") or "")
                    if not identity or not trace_id:
                        continue
                    traces = self._index.setdefault(identity, [])
                    if trace_id not in traces:
                        traces.append(trace_id)
                    self._trace_to_identity[trace_id] = identity
                    loaded += 1
        return loaded

    def _append_row(self, row: dict[str, Any]) -> None:
        if not self._persist_path:
            return
        with open(self._persist_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


_store: Optional[ExecutionIdentityStore] = None
_store_lock = threading.Lock()


def get_identity_store() -> ExecutionIdentityStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = ExecutionIdentityStore()
        return _store


def configure_identity_store(base_dir: str) -> None:
    store = get_identity_store()
    store.set_persist_base(base_dir)
    store.hydrate_from_disk()


def reset_identity_store() -> None:
    global _store
    with _store_lock:
        _store = ExecutionIdentityStore()

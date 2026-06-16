"""In-memory execution tap — runtime truth buffer for drift detection (read-only export)."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Optional

from core.runtime.tap_storage import ExecutionTapLog

_DEFAULT_MAX = 500


@dataclass
class TapEvent:
    ts: float
    type: str
    trace_id: Optional[str]
    event_id: Optional[str]
    summary: str
    impact: str = "unknown"
    payload: dict[str, Any] = field(default_factory=dict)
    spine_written: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "type": self.type,
            "trace_id": self.trace_id,
            "event_id": self.event_id,
            "summary": self.summary,
            "impact": self.impact,
            "payload": self.payload,
            "spine_written": self.spine_written,
        }


class ExecutionTap:
    """Ring buffer of runtime-side execution events (independent of spine write success)."""

    def __init__(self, max_size: int = _DEFAULT_MAX) -> None:
        self._max = max(1, max_size)
        self._buffer: Deque[TapEvent] = deque(maxlen=self._max)
        self._lock = threading.Lock()
        self._persist_base: Optional[str] = None
        self._hydrated = False

    def set_persist_base(self, base_dir: str | Path) -> None:
        self._persist_base = str(base_dir)

    def ingest_row(self, row: dict[str, Any]) -> None:
        """Load persisted row without re-writing disk."""
        event_id = row.get("event_id")
        event_type = str(row.get("type") or "unknown")
        if event_id:
            with self._lock:
                for existing in self._buffer:
                    if existing.event_id == event_id and existing.type == event_type:
                        return
        ev = TapEvent(
            ts=float(row.get("ts") or time.time()),
            type=event_type,
            trace_id=row.get("trace_id"),
            event_id=event_id,
            summary=str(row.get("summary") or ""),
            impact=str(row.get("impact") or "unknown"),
            payload=dict(row.get("payload") or {}),
            spine_written=bool(row.get("spine_written")),
        )
        with self._lock:
            self._buffer.append(ev)

    def hydrate_from_disk(self) -> int:
        """Load tap rows from execution_tap.jsonl into memory buffer."""
        if not self._persist_base or self._hydrated:
            return 0
        log = ExecutionTapLog(self._persist_base)
        rows = log.read_all()
        loaded = 0
        for row in rows[-self._max :]:
            self.ingest_row(row)
            loaded += 1
        self._hydrated = True
        return loaded

    def events_for_trace_merged(self, trace_id: str) -> list[dict[str, Any]]:
        """In-memory tap + on-disk rows for trace (cross-process replay)."""
        mem = self.events_for_trace(trace_id)
        if not self._persist_base:
            return mem
        disk = ExecutionTapLog(self._persist_base).events_for_trace(trace_id)
        if not mem:
            return disk
        if not disk:
            return mem
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for row in mem + disk:
            eid = row.get("event_id")
            key = str(eid) if eid else f"{row.get('type')}:{row.get('ts')}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
        return merged

    def record(
        self,
        *,
        event_type: str,
        summary: str,
        trace_id: Optional[str] = None,
        event_id: Optional[str] = None,
        impact: str = "unknown",
        payload: Optional[dict[str, Any]] = None,
        spine_written: bool = False,
        persist: bool = True,
    ) -> TapEvent:
        if event_id:
            with self._lock:
                for existing in self._buffer:
                    if existing.event_id == event_id and existing.type == event_type:
                        return existing

        ev = TapEvent(
            ts=time.time(),
            type=event_type,
            trace_id=trace_id,
            event_id=event_id,
            summary=summary,
            impact=impact,
            payload=dict(payload or {}),
            spine_written=spine_written,
        )
        with self._lock:
            self._buffer.append(ev)
        if persist and self._persist_base:
            ExecutionTapLog(self._persist_base).append(ev.to_dict())
        return ev

    def tail(self, n: int = 20, *, trace_id: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._buffer)
        if trace_id:
            items = [e for e in items if e.trace_id == trace_id]
        return [e.to_dict() for e in items[-n:]]

    def events_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            items = [e for e in self._buffer if e.trace_id == trace_id]
        return [e.to_dict() for e in items]

    def flush(self, *, trace_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Return matching events without clearing (snapshot, not destructive flush)."""
        if trace_id:
            return self.events_for_trace(trace_id)
        with self._lock:
            return [e.to_dict() for e in self._buffer]

    def last_event(self, trace_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        items = self.tail(1, trace_id=trace_id)
        return items[-1] if items else None


_tap: Optional[ExecutionTap] = None
_tap_lock = threading.Lock()


def get_execution_tap() -> ExecutionTap:
    global _tap
    with _tap_lock:
        if _tap is None:
            _tap = ExecutionTap()
        return _tap


def reset_execution_tap() -> None:
    global _tap
    with _tap_lock:
        _tap = ExecutionTap()

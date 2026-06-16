"""In-memory trace index over spine event rows (v1 — rebuilt per query)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class TraceIndex:
    """Group spine rows by trace_id for O(1) lookup after one scan."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._by_trace: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            tid = str(row.get("trace_id") or "")
            if tid:
                self._by_trace[tid].append(row)

    def events_for(self, trace_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        items = list(self._by_trace.get(trace_id, []))
        items.sort(key=lambda r: str(r.get("timestamp") or ""))
        if limit and len(items) > limit:
            return items[-limit:]
        return items

    def trace_ids(self) -> list[str]:
        return sorted(self._by_trace.keys())

"""Trace completeness helper — debug / explain support."""

from __future__ import annotations

from typing import Any


def validate_trace(trace_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Report which event types are present for a trace (observability only)."""
    present = {str(e.get("event_type") or "") for e in events}
    hints = ("recall", "capture", "control", "chat")
    missing = [name for name in hints if name not in present]
    return {
        "trace_id": trace_id,
        "complete": len(missing) == 0,
        "present": sorted(p for p in present if p),
        "missing": missing,
        "event_count": len(events),
    }

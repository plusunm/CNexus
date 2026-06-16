"""Unified ExecutionTap recording — single import for all runtime entry points."""

from __future__ import annotations

from typing import Any, Optional

from core.runtime.execution_tap import get_execution_tap
from core.runtime.trace_context import resolve_trace_id


def record_execution(
    *,
    event_type: str,
    summary: str,
    trace_id: Optional[str] = None,
    event_id: Optional[str] = None,
    impact: str = "read",
    payload: Optional[dict[str, Any]] = None,
    spine_written: bool = False,
) -> dict[str, Any]:
    """Record runtime-side execution (tap-only or mirrored from spine)."""
    effective = resolve_trace_id(trace_id)
    ev = get_execution_tap().record(
        event_type=event_type,
        summary=summary,
        trace_id=effective,
        event_id=event_id,
        impact=impact,
        payload=payload,
        spine_written=spine_written,
    )
    return ev.to_dict()


def record_direct_access(operation: str, *, trace_id: Optional[str] = None) -> dict[str, Any]:
    return record_execution(
        event_type=f"direct_{operation}",
        summary=f"direct runtime.{operation}",
        trace_id=trace_id,
        impact="read",
        payload={"operation": operation, "source": "direct_access"},
        spine_written=False,
    )

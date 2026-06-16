"""Runtime hooks — register global SpineWriter for control-plane projection."""

from __future__ import annotations

from typing import Optional

from core.control_plane.decision_engine import Decision
from core.runtime.trace_context import resolve_trace_id
from core.spine.writer import SpineWriter

_spine_writer: Optional[SpineWriter] = None


def register_spine_writer(writer: Optional[SpineWriter]) -> None:
    global _spine_writer
    _spine_writer = writer


def get_spine_writer() -> Optional[SpineWriter]:
    return _spine_writer


def maybe_project_control_decision(
    decision: Decision,
    *,
    trace_id: Optional[str] = None,
) -> None:
    effective = resolve_trace_id(trace_id)
    if not effective or _spine_writer is None:
        return
    _spine_writer.project_control(
        trace_id=effective,
        decision=decision.type.value,
        reason=decision.reason,
        caller=decision.caller,
        entry=decision.registry_entry,
        route_kind=decision.route_kind,
    )

"""CP-2.5 Execution Spine Hook — unified runtime event emission."""

from __future__ import annotations

from typing import Any, Optional

from core.runtime.execution_tap import get_execution_tap
from core.runtime.trace_context import resolve_trace_id
from core.spine.execution_context import note_execution_event
from core.spine.integration import get_spine_writer
from core.spine.types import SpineEvent, SpineEventType


def emit_spine_event(
    *,
    event_type: str,
    summary: str,
    subsystem: str = "runtime",
    action: str = "read",
    trace_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    triggered_by: Optional[str] = None,
    control_of: Optional[str] = None,
    **fields: Any,
) -> Optional[SpineEvent]:
    """
    Emit a runtime execution event into spine_events.jsonl.
    No-ops when spine writer is unregistered or trace_id is missing.
    """
    from core.kernel.enforce.context import is_kernel_context
    from core.kernel.enforce.mode import enforce_mode

    if enforce_mode() and action == "mutate" and not is_kernel_context():
        return None

    writer = get_spine_writer()
    effective = resolve_trace_id(trace_id)
    impact = "state_update" if action == "mutate" else "read"
    tap = get_execution_tap()

    if writer is None or not effective:
        tap.record(
            event_type=event_type,
            summary=summary,
            trace_id=effective,
            impact=impact,
            payload=payload,
            spine_written=False,
        )
        return None

    event = writer.emit(
        trace_id=effective,
        event_type=event_type,
        summary=summary,
        subsystem=subsystem,
        action=action,
        payload=payload,
        triggered_by=triggered_by,
        control_of=control_of,
        **fields,
    )
    # Tap mirrored in SpineWriter._link_and_append — avoid duplicate record.
    if event:
        note_execution_event(event_type, event.event_id)
        try:
            from core.spine.token.hooks import maybe_emit_for_event_type

            maybe_emit_for_event_type(event, extra=fields)
        except Exception:
            pass
    return event


def emit_execution_recall(
    *,
    query: str,
    top_k: int,
    mutate_state: bool,
    result_count: int,
    trace_id: Optional[str] = None,
) -> Optional[SpineEvent]:
    return emit_spine_event(
        event_type=SpineEventType.RECALL.value,
        summary=f"recall · {query[:80]}",
        action="read" if not mutate_state else "mutate",
        trace_id=trace_id,
        payload={
            "query": query,
            "top_k": top_k,
            "mutate_state": mutate_state,
            "result_count": result_count,
            "source": "execution_spine",
        },
    )


def emit_execution_llm_call(
    *,
    caller: str,
    model_hint: str = "",
    input_chars: int = 0,
    trace_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> Optional[SpineEvent]:
    return emit_spine_event(
        event_type=SpineEventType.LLM_CALL.value,
        summary=f"llm_call · {caller}",
        action="read",
        trace_id=trace_id,
        triggered_by=triggered_by,
        payload={
            "caller": caller,
            "model_hint": model_hint,
            "input_chars": input_chars,
            "source": "execution_spine",
        },
    )


def emit_execution_chat(
    *,
    user_preview: str,
    mode: str = "chat",
    trace_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> Optional[SpineEvent]:
    return emit_spine_event(
        event_type=SpineEventType.CHAT.value,
        summary=f"chat · {user_preview[:60]}",
        action="mutate",
        trace_id=trace_id,
        triggered_by=triggered_by,
        payload={"mode": mode, "source": "execution_spine"},
    )


def emit_memory_mutation(
    *,
    kind: str,
    summary: str,
    trace_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> Optional[SpineEvent]:
    body = {"kind": kind, "source": "execution_spine", **(payload or {})}
    return emit_spine_event(
        event_type=SpineEventType.MEMORY_MUTATION.value,
        summary=summary,
        action="mutate",
        trace_id=trace_id,
        triggered_by=triggered_by,
        payload=body,
    )


def emit_dispatch(
    *,
    kind: str,
    entry: str,
    trace_id: Optional[str] = None,
) -> Optional[SpineEvent]:
    return emit_spine_event(
        event_type=SpineEventType.DISPATCH.value,
        summary=f"dispatch · {kind}",
        subsystem="control_plane",
        action="read",
        trace_id=trace_id,
        payload={"kind": kind, "entry": entry, "source": "execution_spine"},
    )

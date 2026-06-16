"""Runtime Introspection Port — read-only execution observation boundary."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from core.governance.gtbs.state_snapshot import snapshot_tier_a
from core.runtime.execution_tap import get_execution_tap
from core.runtime.trace_context import get_trace_id
from core.spine.execution_context import resolve_llm_trigger, resolve_recall_trigger
from core.spine.execution.semantics import classify_event_phase
from core.spine.integration import get_spine_writer
from core.spine.storage import SpineEventLog
from core.spine.token.service import build_token_observatory

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def _memory_pressure(runtime: "BrainMemoryRuntime") -> float:
    try:
        stats = runtime.memory_manager.block_stats()
        total = float(stats.get("total_active") or 0)
        return min(1.0, total / 200.0) if total else 0.0
    except Exception:
        return 0.0


def _spine_sync_status(
    base_dir: str,
    trace_id: Optional[str],
    tap_events: list[dict[str, Any]],
) -> dict[str, Any]:
    log = SpineEventLog(base_dir)
    try:
        rows = log.read_all()
    except Exception:
        rows = []

    if trace_id:
        spine_rows = [r for r in rows if str(r.get("trace_id") or "") == trace_id]
    else:
        spine_rows = rows[-20:]

    last_id = None
    if spine_rows:
        last_id = str(spine_rows[-1].get("event_id") or "") or None

    unwritten = sum(1 for e in tap_events if not e.get("spine_written"))
    if not tap_events and not spine_rows:
        status = "synced"
    elif unwritten == 0 and tap_events:
        status = "synced"
    elif unwritten > 0:
        status = "drifted" if unwritten >= max(1, len(tap_events) // 2) else "partial"
    else:
        status = "partial"

    return {
        "spine_sync_status": status,
        "last_spine_event_id": last_id,
        "spine_event_count": len(spine_rows),
        "tap_unwritten_count": unwritten,
    }


def build_runtime_introspection(runtime: "BrainMemoryRuntime") -> dict[str, Any]:
    """Assemble read-only snapshot: live runtime state + trace context + tap buffer."""
    trace_id = get_trace_id()
    tap = get_execution_tap()
    tap_events = tap.events_for_trace_merged(trace_id) if trace_id else tap.tail(20)

    tier_a = snapshot_tier_a(runtime)
    attention = {}
    try:
        attention = runtime.memory_manager.get_attention_snapshot()
    except Exception:
        pass

    last = tap.last_event(trace_id) if trace_id else tap.last_event()
    execution_phase = None
    if last:
        execution_phase = classify_event_phase(
            {
                "event_type": last.get("type"),
                "event_id": last.get("event_id"),
                "summary": last.get("summary"),
            }
        )

    sync = _spine_sync_status(str(runtime.base_dir), trace_id, tap_events)
    writer = get_spine_writer()

    token_traces: list[dict[str, Any]] = []
    try:
        token_traces = build_token_observatory(str(runtime.base_dir), limit=50)
    except Exception:
        pass

    return {
        "schema_version": "runtime-introspect-1",
        "working_self": tier_a.working_self,
        "attention": attention,
        "memory_state": runtime.memory_manager.block_stats(),
        "memory_pressure": _memory_pressure(runtime),
        "trace": {
            "active_trace_id": trace_id,
            "last_event": last.get("type") if last else None,
            "last_event_id": last.get("event_id") if last else None,
            "execution_phase": execution_phase,
            "recall_anchor": resolve_recall_trigger(),
            "llm_anchor": resolve_llm_trigger(),
        },
        "recent_events": tap.tail(20, trace_id=trace_id) if trace_id else tap.tail(20),
        "spine_sync": sync,
        "spine_writer_registered": writer is not None,
        "token_traces": token_traces,
    }

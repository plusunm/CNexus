"""Kernel pre/post hooks — tap, spine, identity (async observability queue)."""

from __future__ import annotations

import os
import threading
from queue import SimpleQueue
from typing import Any, Optional

from core.kernel.context import ExecutionContext
from core.kernel.intent import ExecutionIntent
from core.runtime.execution_tap import get_execution_tap
from core.spine.emit import emit_spine_event
from core.spine.identity.service import get_identity_service
from core.spine.identity.store import get_identity_store

_TAP_QUEUE: SimpleQueue = SimpleQueue()
_SPINE_QUEUE: SimpleQueue = SimpleQueue()
_WORKERS_STARTED = False
_WORKER_LOCK = threading.Lock()

_LIGHT_TIERS = frozenset({"T0", "T1"})


def _tap_sync_mode() -> bool:
    flag = os.environ.get("KERNEL_TAP_SYNC", "").strip().lower()
    return flag in ("1", "true", "yes", "on")


def _record_execution_tap_sync(event: dict[str, Any]) -> None:
    from core.kernel.enforce.context import is_kernel_context
    from core.kernel.enforce.mode import enforce_mode

    if enforce_mode() and not is_kernel_context():
        return
    trace_id = event.get("trace_id")
    phase = str(event.get("phase") or event.get("intent") or "kernel")
    get_execution_tap().record(
        event_type="kernel",
        summary=phase,
        trace_id=trace_id if isinstance(trace_id, str) else None,
        impact="state_update",
        payload=event,
    )


def _emit_spine_event_sync(**kwargs: Any) -> None:
    emit_spine_event(**kwargs)


def _ensure_workers() -> None:
    global _WORKERS_STARTED
    with _WORKER_LOCK:
        if _WORKERS_STARTED:
            return
        threading.Thread(target=_tap_worker, name="kernel-tap-worker", daemon=True).start()
        threading.Thread(target=_spine_worker, name="kernel-spine-worker", daemon=True).start()
        _WORKERS_STARTED = True


def _tap_worker() -> None:
    while True:
        event = _TAP_QUEUE.get()
        try:
            _record_execution_tap_sync(event)
        except Exception:
            pass


def _spine_worker() -> None:
    while True:
        kwargs = _SPINE_QUEUE.get()
        try:
            _emit_spine_event_sync(**kwargs)
        except Exception:
            pass


def record_execution_tap(event: dict[str, Any]) -> None:
    """Enqueue tap write (sync when KERNEL_TAP_SYNC=1)."""
    if _tap_sync_mode():
        _record_execution_tap_sync(event)
        return
    _ensure_workers()
    _TAP_QUEUE.put_nowait(event)


def enqueue_spine_event(**kwargs: Any) -> None:
    if _tap_sync_mode():
        _emit_spine_event_sync(**kwargs)
        return
    _ensure_workers()
    _SPINE_QUEUE.put_nowait(kwargs)


def flush_observability_queues(timeout: float = 2.0) -> None:
    """Drain async observability queues (tests / shutdown)."""
    if _tap_sync_mode():
        return
    deadline = threading.Event()
    import time

    end = time.time() + timeout
    while time.time() < end:
        if _TAP_QUEUE.empty() and _SPINE_QUEUE.empty():
            break
        time.sleep(0.01)


def reset_observability_workers() -> None:
    global _WORKERS_STARTED
    with _WORKER_LOCK:
        _WORKERS_STARTED = False
    while not _TAP_QUEUE.empty():
        try:
            _TAP_QUEUE.get_nowait()
        except Exception:
            break
    while not _SPINE_QUEUE.empty():
        try:
            _SPINE_QUEUE.get_nowait()
        except Exception:
            break


def resolve_identity(trace_id: str) -> str | None:
    return get_identity_store().identity_for_trace(trace_id)


def before_execute(intent: ExecutionIntent, ctx: ExecutionContext, tier: str = "T3") -> None:
    record_execution_tap(
        {
            "trace_id": ctx.trace_id,
            "phase": "before_execute",
            "intent": intent.type,
            "source": intent.source,
            "execution_tier": tier,
            "payload_keys": sorted(intent.payload.keys()),
        }
    )
    if tier in _LIGHT_TIERS:
        return
    enqueue_spine_event(
        event_type="kernel_enter",
        summary=f"kernel:{intent.type}",
        subsystem="kernel",
        action="mutate",
        trace_id=ctx.trace_id,
        payload={"intent": intent.type, "source": intent.source, "execution_tier": tier},
        triggered_by=intent.source,
    )


def after_execute(intent: ExecutionIntent, ctx: ExecutionContext, result: Any, tier: str = "T3") -> None:
    record_execution_tap(
        {
            "trace_id": ctx.trace_id,
            "phase": "after_execute",
            "intent": intent.type,
            "execution_tier": tier,
            "result_type": type(result).__name__,
            "elapsed_ms": ctx.elapsed_ms(),
        }
    )
    if tier not in _LIGHT_TIERS:
        enqueue_spine_event(
            event_type="kernel_exit",
            summary=f"kernel:{intent.type}:done",
            subsystem="kernel",
            action="read",
            trace_id=ctx.trace_id,
            payload={
                "intent": intent.type,
                "result_type": type(result).__name__,
                "elapsed_ms": ctx.elapsed_ms(),
                "execution_tier": tier,
            },
            triggered_by=intent.source,
        )
    _maybe_register_identity(intent, ctx, result)


def _maybe_register_identity(intent: ExecutionIntent, ctx: ExecutionContext, result: Any) -> None:
    """Lightweight identity bind when enough observability exists."""
    if not isinstance(result, dict):
        return
    events = result.get("spine_events") or result.get("events")
    if not isinstance(events, list) or not events:
        return
    try:
        svc = get_identity_service()
        resolved = svc.resolve_for_response(
            ctx.trace_id,
            events,
            control=[],
            state={},
            execution={"intent": intent.type},
            register=True,
        )
        ctx.identity_id = resolved.get("identity")
    except Exception:
        return


def before_graph(graph: Any, ctx: ExecutionContext, tier: str = "T3") -> None:
    record_execution_tap(
        {
            "trace_id": ctx.trace_id,
            "phase": "graph_planned",
            "execution_tier": tier,
            "graph_invariant": graph.invariant_hash(),
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        }
    )
    enqueue_spine_event(
        event_type="kernel_graph_enter",
        summary=f"graph:{len(graph.nodes)}nodes",
        subsystem="kernel",
        action="mutate",
        trace_id=ctx.trace_id,
        payload={
            "graph_invariant": graph.invariant_hash(),
            "nodes": [n.label for n in graph.nodes],
            "execution_tier": tier,
        },
        triggered_by=str(ctx.tags.get("source", "kernel")),
    )


def after_graph(graph: Any, ctx: ExecutionContext, result: Any, tier: str = "T3") -> None:
    invariant = graph.invariant_hash()
    record_execution_tap(
        {
            "trace_id": ctx.trace_id,
            "phase": "graph_complete",
            "execution_tier": tier,
            "graph_invariant": invariant,
            "result_type": type(result).__name__,
            "elapsed_ms": ctx.elapsed_ms(),
        }
    )
    record_execution_tap(
        {
            "trace_id": ctx.trace_id,
            "phase": "exit_kernel",
            "execution_tier": tier,
            "graph_invariant": invariant,
            "result_type": type(result).__name__,
            "elapsed_ms": ctx.elapsed_ms(),
        }
    )
    spine_payload: dict[str, Any] = {
        "graph_invariant": invariant,
        "result_type": type(result).__name__,
        "execution_tier": tier,
    }
    if tier == "T3":
        spine_payload["execution_graph"] = graph.to_dict()
    enqueue_spine_event(
        event_type="kernel_graph_exit",
        summary=f"graph:done:{invariant[:8]}",
        subsystem="kernel",
        action="read",
        trace_id=ctx.trace_id,
        payload=spine_payload,
        triggered_by=str(ctx.tags.get("source", "kernel")),
    )
    ctx.identity_id = ctx.identity_id or invariant
    if isinstance(result, dict):
        result.setdefault("identity", ctx.identity_id)
        result.setdefault("graph_invariant", invariant)
        if tier == "T3":
            result.setdefault("execution_graph", graph.to_dict())

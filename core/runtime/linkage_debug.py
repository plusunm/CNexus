"""CNEXUS Runtime Linkage Debug Protocol v1 — provable runtime graph snapshots."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from core.runtime.boot_protocol import (
    BootPhase,
    boot_status,
    cognitive_disabled,
    evaluate_system_ready,
    fast_health_payload,
    get_boot_phase,
    get_l3_scheduler_status,
    is_runtime_warming,
)
from core.runtime.control_plane_kernel import build_ready_snapshot, peek_runtime_pointer
from core.runtime.execution_trace import trace_stats
from core.runtime.thread_registry import COGNITIVE_WARM_ROLE, RUNTIME_WARM_ROLE, all_thread_snapshots

try:
    from core.runtime.control_plane_isolation import isolation_enabled
except ImportError:
    def isolation_enabled() -> bool:
        return True

RUNTIME_STALE_MS = 300_000
L3_TICK_STALE_MS = 30_000
L3_OVERLOAD_MS = 50

_PeekRuntime = Callable[[], Any]


def _default_peek() -> Any:
    return peek_runtime_pointer()


def collect_control_section(*, app_started: bool = True) -> Dict[str, Any]:
    boot = boot_status()
    runtime = _default_peek()
    health = fast_health_payload(runtime)
    ready_status = evaluate_system_ready(
        app_started=app_started,
        runtime_present=runtime is not None,
        runtime_warming=is_runtime_warming(),
        memory_ok=health.get("status") in ("ready", "degraded", "initializing"),
    )
    ok = app_started and boot.get("control_plane_alive", True)
    return {
        "ok": ok,
        "ready": ready_status,
        "boot_phase": boot.get("boot_phase"),
        "health": health.get("status"),
        "app_started": app_started,
        "control_plane_alive": boot.get("control_plane_alive", True),
        "minimal_boot": boot.get("minimal_boot"),
        "cognitive_disabled": boot.get("cognitive_disabled"),
    }


def collect_runtime_section(
    *,
    peek_runtime: Optional[_PeekRuntime] = None,
    thread_snapshots: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    peek = peek_runtime or _default_peek
    runtime = peek()
    threads = thread_snapshots or all_thread_snapshots()
    warm = threads.get(RUNTIME_WARM_ROLE, {})
    pointer = runtime is not None
    thread_alive = bool(warm.get("thread_alive"))
    age_ms = warm.get("age_ms")
    stale = (
        pointer
        and thread_alive
        and age_ms is not None
        and age_ms > RUNTIME_STALE_MS
        and get_boot_phase() != BootPhase.BOOT_4_READY
    )
    init_error = None
    warm_cooldown = False
    try:
        from api.runtime_warm_status import runtime_warm_meta

        warm_meta = runtime_warm_meta()
        init_error = warm_meta.get("init_error")
        warm_cooldown = bool(warm_meta.get("in_cooldown"))
    except ImportError:
        pass
    return {
        "pointer": pointer,
        "thread_alive": thread_alive,
        "thread_registered": warm.get("registered", False),
        "thread_name": warm.get("name"),
        "last_spawn_ts": warm.get("last_spawn_ts"),
        "thread_age_ms": age_ms,
        "runtime_warming": is_runtime_warming(),
        "stale": stale,
        "init_error": init_error,
        "warm_cooldown": warm_cooldown,
        "base_dir": str(getattr(runtime, "base_dir", "") or "") or None,
    }


def collect_l3_section(*, boot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    boot = boot or boot_status()
    l3 = get_l3_scheduler_status() or boot.get("l3") or {}
    phase = get_boot_phase()
    required = (
        not cognitive_disabled()
        and phase == BootPhase.BOOT_3_COGNITIVE_WARMING
        and not boot.get("cognitive_warmup_done")
    )
    ticks = int(l3.get("ticks") or 0)
    queue_length = int(l3.get("queue_length") or 0)
    last_tick = l3.get("last_tick") or {}
    tick_latency = int(last_tick.get("tick_cost_ms") or 0)
    last_tick_mono = last_tick.get("mono_ms")
    if last_tick_mono is None and ticks > 0:
        last_tick_mono = int(time.monotonic() * 1000)

    now_mono = int(time.monotonic() * 1000)
    tick_stale = (
        ticks > 0
        and queue_length > 0
        and last_tick_mono is not None
        and (now_mono - int(last_tick_mono)) > L3_TICK_STALE_MS
    )
    queue_stuck = queue_length > 0 and (ticks == 0 or tick_stale)
    cognitive_thread = all_thread_snapshots().get(COGNITIVE_WARM_ROLE, {})

    return {
        "required": required,
        "ticks": ticks,
        "queue_length": queue_length,
        "tick_latency": tick_latency,
        "last_tick_ms": last_tick_mono,
        "queue_stuck": queue_stuck,
        "tick_latency_overload": tick_latency > L3_OVERLOAD_MS,
        "scheduler": l3.get("scheduler"),
        "slice_ms": l3.get("slice_ms"),
        "last_tick": last_tick,
        "cognitive_thread_alive": cognitive_thread.get("thread_alive", False),
    }


def collect_cognition_section(*, boot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    boot = boot or boot_status()
    return {
        "cognitive_warming": boot.get("cognitive_warming"),
        "cognitive_warmup_done": boot.get("cognitive_warmup_done"),
        "cognitive_elapsed_ms": boot.get("cognitive_elapsed_ms"),
        "cognitive_timeout_sec": boot.get("cognitive_timeout_sec"),
        "hydrate_complete": boot.get("hydrate_complete"),
    }


def collect_event_section(*, base_dir: Optional[str] = None, include_trace: bool = False) -> Dict[str, Any]:
    if not include_trace or isolation_enabled():
        return {
            "path": None,
            "skipped": True,
            "reason": "control_plane_isolation",
            "flow_active": None,
            "no_flow": False,
            "l3_tick_count": None,
        }
    stats = trace_stats(base_dir)
    no_flow = bool(stats.get("no_flow")) and stats.get("exists")
    partial_flow = int(stats.get("l3_tick_count") or 0) > 0 and not stats.get("flow_active")
    return {
        **stats,
        "no_flow": no_flow,
        "partial_flow": partial_flow,
        "backlog_hint": int(stats.get("l3_tick_count") or 0),
    }


def collect_linkage_snapshot(
    *,
    app_started: bool = True,
    peek_runtime: Optional[_PeekRuntime] = None,
) -> Dict[str, Any]:
    peek = peek_runtime or _default_peek
    runtime = peek()
    boot = boot_status()
    base_dir = str(getattr(runtime, "base_dir", "") or "") or None
    return {
        "control": collect_control_section(app_started=app_started),
        "runtime": collect_runtime_section(peek_runtime=peek),
        "l3": collect_l3_section(boot=boot),
        "cognition": collect_cognition_section(boot=boot),
        "event": collect_event_section(base_dir=base_dir),
        "linkage": build_ready_snapshot(app_started=app_started),
    }


def resolve_root_cause(snapshot: Dict[str, Any]) -> str:
    control = snapshot.get("control") or {}
    runtime = snapshot.get("runtime") or {}
    l3 = snapshot.get("l3") or {}
    event = snapshot.get("event") or {}

    if not control.get("ok"):
        return "CONTROL_PLANE_FAILURE"

    if not runtime.get("pointer"):
        if runtime.get("runtime_warming") or runtime.get("thread_alive"):
            return "BOOT_IN_PROGRESS"
        if runtime.get("init_error") and runtime.get("warm_cooldown"):
            return "RUNTIME_INIT_FAILED"
        if runtime.get("warm_cooldown"):
            return "BOOT_IN_PROGRESS"
        return "BOOT_INJECTION_FAILURE"

    if runtime.get("runtime_warming"):
        return "BOOT_IN_PROGRESS"

    if runtime.get("stale"):
        return "RUNTIME_DEAD_AFTER_SPAWN"

    if l3.get("required") and l3.get("ticks", 0) == 0 and not cognitive_disabled():
        if not l3.get("cognitive_thread_alive"):
            return "L3_HEARTBEAT_NOT_STARTED"

    if l3.get("queue_stuck"):
        return "L3_DEADLOCK"

    if l3.get("tick_latency_overload"):
        return "L3_SCHEDULER_OVERLOAD"

    if event.get("no_flow") and l3.get("ticks", 0) > 0:
        return "EVENT_FABRIC_BROKEN"

    if control.get("ready") == "ready":
        return "SYSTEM_HEALTHY"

    if control.get("ready") == "warming":
        return "BOOT_IN_PROGRESS"

    return "RUNTIME_NOT_READY"


_FAULT_LAYER = {
    "CONTROL_PLANE_FAILURE": "CONTROL",
    "BOOT_INJECTION_FAILURE": "BOOT",
    "RUNTIME_THREAD_NOT_RUNNING": "RUNTIME",
    "RUNTIME_DEAD_AFTER_SPAWN": "RUNTIME",
    "L3_HEARTBEAT_NOT_STARTED": "L3",
    "L3_DEADLOCK": "L3",
    "L3_SCHEDULER_OVERLOAD": "L3",
    "EVENT_FABRIC_BROKEN": "EVENT",
    "SYSTEM_HEALTHY": "NONE",
    "BOOT_IN_PROGRESS": "BOOT",
    "RUNTIME_INIT_FAILED": "RUNTIME",
    "RUNTIME_NOT_READY": "RUNTIME",
}

_RECOMMENDED_ACTIONS = {
    "CONTROL_PLANE_FAILURE": "restart_control_plane",
    "BOOT_INJECTION_FAILURE": "start_runtime_warm_thread",
    "RUNTIME_THREAD_NOT_RUNNING": "restart_runtime_thread",
    "RUNTIME_DEAD_AFTER_SPAWN": "restart_runtime_thread",
    "L3_HEARTBEAT_NOT_STARTED": "start_cognitive_warmup_thread",
    "L3_DEADLOCK": "flush_queue_and_restart_scheduler",
    "L3_SCHEDULER_OVERLOAD": "reduce_cognitive_load",
    "EVENT_FABRIC_BROKEN": "rebind_event_bus",
    "SYSTEM_HEALTHY": "none",
    "BOOT_IN_PROGRESS": "wait_for_boot",
    "RUNTIME_INIT_FAILED": "inspect_runtime_init_logs",
    "RUNTIME_NOT_READY": "wait_for_boot",
}


def _build_evidence(snapshot: Dict[str, Any], root_cause: str) -> List[str]:
    control = snapshot.get("control") or {}
    runtime = snapshot.get("runtime") or {}
    l3 = snapshot.get("l3") or {}
    event = snapshot.get("event") or {}
    evidence = [
        f"control.ok={control.get('ok')}",
        f"boot_phase={control.get('boot_phase')}",
        f"runtime.pointer={runtime.get('pointer')}",
        f"runtime.thread_alive={runtime.get('thread_alive')}",
        f"l3.ticks={l3.get('ticks')}",
        f"l3.queue_length={l3.get('queue_length')}",
        f"event.l3_tick_count={event.get('l3_tick_count')}",
    ]
    if root_cause == "L3_DEADLOCK":
        evidence.append(f"l3.queue_stuck={l3.get('queue_stuck')}")
    if root_cause == "EVENT_FABRIC_BROKEN":
        evidence.append(f"event.flow_active={event.get('flow_active')}")
    return evidence


def resolve_diagnosis(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    root_cause = resolve_root_cause(snapshot)
    if root_cause == "SYSTEM_HEALTHY":
        status = "READY"
    elif root_cause in ("BOOT_IN_PROGRESS", "L3_SCHEDULER_OVERLOAD"):
        status = "DEGRADED"
    elif root_cause in ("RUNTIME_NOT_READY", "RUNTIME_INIT_FAILED"):
        status = "DEGRADED" if root_cause == "RUNTIME_NOT_READY" else "BROKEN"
    else:
        status = "BROKEN" if root_cause.endswith("FAILURE") or "NOT_RUNNING" in root_cause else "DEGRADED"

    return {
        "status": status,
        "root_cause": root_cause,
        "layer": _FAULT_LAYER.get(root_cause, "UNKNOWN"),
        "evidence": _build_evidence(snapshot, root_cause),
        "recommended_action": _RECOMMENDED_ACTIONS.get(root_cause, "inspect_logs"),
    }


def build_linkage_debug_payload(
    *,
    app_started: bool = True,
    peek_runtime: Optional[_PeekRuntime] = None,
) -> Dict[str, Any]:
    snapshot = collect_linkage_snapshot(app_started=app_started, peek_runtime=peek_runtime)
    diagnosis = resolve_diagnosis(snapshot)
    return {
        "schema_version": "linkage-debug-v1",
        **snapshot,
        "diagnosis": diagnosis,
        "status": diagnosis["status"],
        "root_cause": diagnosis["root_cause"],
        "layer": diagnosis["layer"],
        "evidence": diagnosis["evidence"],
        "recommended_action": diagnosis["recommended_action"],
    }

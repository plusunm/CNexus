"""CNexus Boot Protocol v3 — unified scheduler semantics for boot phases."""

from __future__ import annotations

import os
import threading
import time
from enum import Enum
from typing import Any, Dict, Optional

BOOT_VERSION = "boot-protocol-v3"

# Cognitive warmup may be declared complete after this many seconds (scheduler fallback).
_COGNITIVE_TIMEOUT_SEC = float(os.environ.get("CNEXUS_BOOT_COGNITIVE_TIMEOUT_SEC", "120"))


class BootPhase(str, Enum):
    """Linear boot phases — Control → Runtime → Storage → Cognitive → Ready."""

    BOOT_0_API = "boot_0_api"
    BOOT_1_RUNTIME_SPAWNED = "boot_1_runtime_spawned"
    BOOT_2_HYDRATING = "boot_2_hydrating"
    BOOT_3_COGNITIVE_WARMING = "boot_3_cognitive_warming"
    BOOT_4_READY = "boot_4_ready"


# v2 string aliases for read-side compatibility
LEGACY_PHASE_VALUES: Dict[str, BootPhase] = {
    "boot_1_state": BootPhase.BOOT_1_RUNTIME_SPAWNED,
    "boot_2_hydrate": BootPhase.BOOT_2_HYDRATING,
    "boot_2_cognitive": BootPhase.BOOT_3_COGNITIVE_WARMING,
    "boot_3_optimized": BootPhase.BOOT_4_READY,
}

_lock = threading.RLock()
_phase = BootPhase.BOOT_0_API
_runtime_warming = False
_cognitive_warming = False
_cognitive_warmup_done = False
_hydrate_complete = False
_warmup_started_at: Optional[float] = None
_cognitive_started_at: Optional[float] = None
_l3_scheduler_status: Optional[Dict[str, Any]] = None


def minimal_boot() -> bool:
    flag = os.environ.get("CNEXUS_MINIMAL_BOOT", "0").strip().lower()
    return flag in ("1", "true", "yes", "on")


def cognitive_disabled() -> bool:
    if minimal_boot():
        return True
    for key in (
        "CNEXUS_BOOT_SKIP_COGNITIVE",
        "CNEXUS_DISABLE_CDG",
        "CNEXUS_DISABLE_REFLECTION",
        "CNEXUS_DISABLE_COGNITIVE_WARMUP",
    ):
        if os.environ.get(key, "0").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def normalize_boot_phase(value: str) -> BootPhase:
    """Map API / legacy strings to v3 BootPhase."""
    try:
        return BootPhase(value)
    except ValueError:
        mapped = LEGACY_PHASE_VALUES.get(value)
        if mapped is not None:
            return mapped
        raise


def get_boot_phase() -> BootPhase:
    with _lock:
        return _phase


def set_boot_phase(phase: BootPhase) -> None:
    global _phase
    with _lock:
        old = _phase
        if old == phase:
            return
        _phase = phase
    try:
        from core.runtime.conflict_monitor import log_boot_transition

        log_boot_transition(old.value, phase.value)
    except Exception:
        pass


def mark_runtime_warming(started: bool = True) -> None:
    global _runtime_warming, _warmup_started_at
    with _lock:
        _runtime_warming = started
        if started and _warmup_started_at is None:
            _warmup_started_at = time.monotonic()


def is_runtime_warming() -> bool:
    with _lock:
        return _runtime_warming


def mark_runtime_spawned() -> None:
    """BOOT_0 → BOOT_1: runtime pointer exists, no event-loop construction."""
    mark_runtime_warming(False)
    if cognitive_disabled():
        # Minimal boot may complete hydrate before deferred runtime warm — stay at BOOT_4.
        with _lock:
            global _hydrate_complete
            _hydrate_complete = True
        mark_cognitive_warmup_done(bypass_causal=True)
        return
    set_boot_phase(BootPhase.BOOT_1_RUNTIME_SPAWNED)


def mark_hydrate_started() -> None:
    """BOOT_1 → BOOT_2: storage domain hydrate begins (off event loop)."""
    set_boot_phase(BootPhase.BOOT_2_HYDRATING)


def mark_hydrate_complete() -> None:
    """BOOT_2 → BOOT_3 or BOOT_4 depending on cognitive policy."""
    global _hydrate_complete
    with _lock:
        _hydrate_complete = True
    if cognitive_disabled():
        mark_cognitive_warmup_done(bypass_causal=True)
    else:
        set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)


def is_hydrate_complete() -> bool:
    with _lock:
        return _hydrate_complete


def mark_cognitive_warming(started: bool = True) -> None:
    global _cognitive_warming, _cognitive_started_at
    with _lock:
        _cognitive_warming = started
        if started:
            if _cognitive_started_at is None:
                _cognitive_started_at = time.monotonic()
            set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)


def mark_cognitive_warmup_done(*, bypass_causal: bool = False) -> bool:
    """
    Commit BOOT_4_READY only when causal convergence holds (or cognitive is disabled).
    Returns True when phase advanced, False when rejected (optimistic commit blocked).
    """
    import logging

    if not bypass_causal and not cognitive_disabled() and not cognitive_causally_complete():
        logging.getLogger(__name__).warning(
            "BOOT_4 commit rejected: L3 queue or adapter not causally complete"
        )
        return False
    global _cognitive_warmup_done, _cognitive_warming
    with _lock:
        _cognitive_warmup_done = True
        _cognitive_warming = False
        set_boot_phase(BootPhase.BOOT_4_READY)
    try:
        from core.runtime.cognitive_warmup_adapter import reset_warmup_adapter

        reset_warmup_adapter()
    except Exception:
        pass
    return True


def is_cognitive_warmup_done() -> bool:
    with _lock:
        return _cognitive_warmup_done


def cognitive_warmup_timed_out() -> bool:
    with _lock:
        if _cognitive_warmup_done or _cognitive_started_at is None:
            return False
        return (time.monotonic() - _cognitive_started_at) >= _COGNITIVE_TIMEOUT_SEC


def cognitive_causally_complete() -> bool:
    """BOOT_4 may commit only when L3 queue is drained and adapter (if any) is done."""
    l3 = get_l3_scheduler_status() or {}
    if int(l3.get("queue_length") or 0) > 0:
        return False
    try:
        from core.runtime.cognitive_warmup_adapter import get_active_warmup_adapter

        adapter = get_active_warmup_adapter()
        if adapter is not None:
            return bool(adapter.done)
    except Exception:
        pass
    return True


def maybe_advance_cognitive_timeout() -> bool:
    """Cognitive time budget exceeded — progressive ready on personal/desktop editions."""
    if not cognitive_warmup_timed_out():
        return False
    import logging

    logger = logging.getLogger(__name__)
    deploy = os.environ.get("CNEXUS_DEPLOY_LEVEL", "dev").strip().lower()
    edition = os.environ.get("CNEXUS_EDITION", "personal").strip().lower()
    bundled_desktop = os.environ.get("CNEXUS_AUTO_RUNTIME_WARM", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    relaxed = (
        deploy in ("dev", "internal", "personal")
        or edition == "personal"
        or bundled_desktop
    )
    if relaxed:
        logger.warning(
            "Cognitive warmup exceeded timeout — progressive ready (BOOT_4) for %s/%s edition",
            deploy,
            edition,
        )
        return mark_cognitive_warmup_done(bypass_causal=True)
    logger.warning(
        "Cognitive warmup exceeded timeout — holding BOOT_3 until L3 drains (no optimistic BOOT_4)"
    )
    return False


def set_l3_scheduler_status(payload: Dict[str, Any]) -> None:
    global _l3_scheduler_status
    with _lock:
        _l3_scheduler_status = dict(payload)


def get_l3_scheduler_status() -> Optional[Dict[str, Any]]:
    with _lock:
        return dict(_l3_scheduler_status) if _l3_scheduler_status else None


def advance_boot_cognitive_tick(adapter: Any) -> BootPhase:
    """BOOT_3 glue — one L3 tick; advances to BOOT_4 when queue drains."""
    if get_boot_phase() != BootPhase.BOOT_3_COGNITIVE_WARMING:
        return get_boot_phase()
    phase = adapter.tick()
    if hasattr(adapter, "l3_status"):
        set_l3_scheduler_status(adapter.l3_status())
    return phase


def _cognitive_warmup_blocks_ready() -> bool:
    """Anti false-ready: BOOT_4 must not report ready while L3 queue or warmup adapter is active."""
    l3 = get_l3_scheduler_status() or {}
    if int(l3.get("queue_length") or 0) > 0:
        return True
    try:
        from core.runtime.cognitive_warmup_adapter import get_active_warmup_adapter

        adapter = get_active_warmup_adapter()
        if adapter is not None and not adapter.done:
            return True
    except Exception:
        pass
    with _lock:
        if _cognitive_warming and not _cognitive_warmup_done:
            return True
    try:
        from core.runtime.system_guard import effective_non_hang_tier

        tier = effective_non_hang_tier()
        if tier == "v5":
            from core.kernel.v3.event_bus import get_event_bus
            from core.kernel.v5.global_cluster_runtime import get_global_cluster_runtime

            cluster = get_global_cluster_runtime()
            if not cluster.cluster_health():
                return True
            if not get_event_bus().is_idle():
                return True
            if not cluster.consensus_stable():
                return True
            if not cluster.crdt_consistent():
                return True
        elif tier == "v4":
            from core.kernel.v4.cluster_runtime import get_cluster_runtime
            from core.kernel.v4.replay_engine import get_replay_engine
            from core.kernel.v3.event_bus import get_event_bus

            if not get_cluster_runtime().cluster_healthy():
                return True
            if not get_event_bus().is_idle():
                return True
            if not get_replay_engine().replay_consistent():
                return True
        elif tier == "v3":
            from core.kernel.v3.event_bus import get_event_bus

            if not get_event_bus().is_idle():
                return True
            if not cognitive_process_idle():
                return True
    except Exception:
        pass
    return False


def cognitive_warming_active() -> bool:
    return _cognitive_warmup_blocks_ready()


def cognitive_process_idle() -> bool:
    try:
        from core.runtime.system_guard import effective_non_hang_tier

        if effective_non_hang_tier() == "v1":
            return not cognitive_warming_active()
        from core.kernel.v3.governance_worker_v3 import get_governance_worker_v3
        from core.kernel.v3.process_isolated_executor import get_process_executor

        return get_governance_worker_v3().is_idle() and get_process_executor().is_idle()
    except Exception:
        return not cognitive_warming_active()


def ready_gate_snapshot() -> Dict[str, Any]:
    from core.runtime.system_guard import effective_non_hang_tier

    tier = effective_non_hang_tier()
    l3 = get_l3_scheduler_status() or {}
    l3_ok = int(l3.get("queue_length") or 0) == 0
    cognitive_ok = not cognitive_warming_active()
    snap: Dict[str, Any] = {
        "l3_ok": l3_ok,
        "cognitive_ok": cognitive_ok,
        "ready_gate_ok": l3_ok and cognitive_ok,
        "queue_length": int(l3.get("queue_length") or 0),
    }
    if tier == "v5":
        from core.kernel.v3.event_bus import get_event_bus
        from core.kernel.v5.global_cluster_runtime import get_global_cluster_runtime

        bus = get_event_bus()
        cluster = get_global_cluster_runtime()
        bus_idle = bus.is_idle()
        cluster_ok = cluster.cluster_health()
        consensus_ok = cluster.consensus_stable()
        crdt_ok = cluster.crdt_consistent()
        proc_idle = cognitive_process_idle()
        snap.update(
            {
                "bus_idle": bus_idle,
                "bus_ok": bus_idle,
                "cluster_ok": cluster_ok,
                "consensus_ok": consensus_ok,
                "crdt_ok": crdt_ok,
                "cognitive_process_idle": proc_idle,
                "cognitive_ok": cognitive_ok and proc_idle,
                "ready_gate_ok": l3_ok
                and cognitive_ok
                and bus_idle
                and cluster_ok
                and consensus_ok
                and crdt_ok,
                "layer": "v5",
            }
        )
        return snap
    if tier == "v4":
        from core.kernel.v3.event_bus import get_event_bus
        from core.kernel.v4.cluster_runtime import get_cluster_runtime
        from core.kernel.v4.replay_engine import get_replay_engine

        bus = get_event_bus()
        cluster = get_cluster_runtime()
        replay = get_replay_engine()
        bus_idle = bus.is_idle()
        cluster_ok = cluster.cluster_healthy()
        replay_ok = replay.replay_consistent()
        proc_idle = cognitive_process_idle()
        snap.update(
            {
                "bus_idle": bus_idle,
                "bus_ok": bus_idle,
                "cluster_ok": cluster_ok,
                "replay_ok": replay_ok,
                "cognitive_process_idle": proc_idle,
                "cognitive_ok": cognitive_ok and proc_idle,
                "ready_gate_ok": l3_ok and cognitive_ok and bus_idle and cluster_ok and replay_ok,
                "layer": "v4",
            }
        )
        return snap
    if tier == "v3":
        from core.kernel.v3.event_bus import get_event_bus

        bus = get_event_bus()
        bus_idle = bus.is_idle()
        proc_idle = cognitive_process_idle()
        snap.update(
            {
                "bus_idle": bus_idle,
                "bus_ok": bus_idle,
                "cognitive_process_idle": proc_idle,
                "cognitive_ok": cognitive_ok and proc_idle,
                "ready_gate_ok": l3_ok and cognitive_ok and bus_idle and proc_idle,
                "layer": "v3",
            }
        )
    return snap


def boot_ready_details(
    *,
    status: str,
    app_started: bool,
    runtime_present: bool,
    runtime_warming: bool,
    memory_ok: bool,
) -> Dict[str, Any]:
    """Machine-readable blocking reason for /v1/system/ready (UI + consultation)."""
    phase = get_boot_phase()
    boot = boot_status()
    ready = status == "ready"

    if ready:
        return {"ready": True, "reason": None, "progress": 100, "boot_phase": phase.value}

    progress = 5
    reason = "UNKNOWN"

    if not app_started:
        reason = "API_STARTING"
        progress = 10
    elif runtime_warming or not runtime_present:
        reason = "RUNTIME_INIT"
        progress = 25
    elif not memory_ok:
        reason = "STORAGE_INIT"
        progress = 35
    elif phase != BootPhase.BOOT_4_READY:
        if phase == BootPhase.BOOT_3_COGNITIVE_WARMING:
            reason = "COGNITIVE_WARMUP"
            elapsed = boot.get("cognitive_elapsed_ms") or 0
            budget_ms = int(_COGNITIVE_TIMEOUT_SEC * 1000)
            progress = min(90, 40 + int(elapsed * 50 / max(budget_ms, 1)))
        elif phase == BootPhase.BOOT_2_HYDRATING:
            reason = "STORAGE_HYDRATE"
            progress = 30
        else:
            reason = f"BOOT_PHASE_{phase.value.upper()}"
            progress = 20
    elif _cognitive_warmup_blocks_ready():
        l3 = get_l3_scheduler_status() or {}
        if int(l3.get("queue_length") or 0) > 0:
            reason = "L3_QUEUE_DRAIN"
            progress = 85
        else:
            reason = "COGNITIVE_WARMUP"
            progress = 75
    elif cognitive_warmup_timed_out():
        reason = "COGNITIVE_WARMUP_TIMEOUT"
        progress = 92
    else:
        reason = "NOT_READY"
        progress = 15

    return {
        "ready": False,
        "reason": reason,
        "progress": progress,
        "boot_phase": phase.value,
    }


def evaluate_operational_ready(
    *,
    app_started: bool,
    runtime_present: bool,
    runtime_warming: bool,
    memory_ok: bool,
    token_valid: bool = True,
    license_valid: bool = True,
) -> str:
    """
    Layer-1 readiness: API + runtime pointer + memory — no BOOT_4 / cognitive gate.
    Returns: "operational" | "warming" | "not_ready"
    """
    if not app_started:
        return "warming"
    if runtime_warming or not runtime_present:
        return "warming"
    if not memory_ok:
        return "warming"
    if not (token_valid and license_valid):
        return "not_ready"
    return "operational"


def evaluate_system_ready(
    *,
    app_started: bool,
    runtime_present: bool,
    runtime_warming: bool,
    memory_ok: bool,
    token_valid: bool = True,
    license_valid: bool = True,
) -> str:
    """
    Authoritative ready/warming/not_ready — single scheduler interpretation.
    Returns: "ready" | "warming" | "not_ready"
    """
    maybe_advance_cognitive_timeout()
    phase = get_boot_phase()

    if not app_started:
        return "warming"

    if runtime_warming or phase != BootPhase.BOOT_4_READY:
        return "warming"

    if _cognitive_warmup_blocks_ready():
        return "warming"

    if not (
        runtime_present
        and token_valid
        and license_valid
        and memory_ok
    ):
        return "not_ready"

    return "ready"


def boot_status() -> Dict[str, Any]:
    with _lock:
        elapsed_ms = None
        if _warmup_started_at is not None:
            elapsed_ms = int((time.monotonic() - _warmup_started_at) * 1000)
        cognitive_elapsed_ms = None
        if _cognitive_started_at is not None:
            cognitive_elapsed_ms = int((time.monotonic() - _cognitive_started_at) * 1000)
        return {
            "boot_version": BOOT_VERSION,
            "boot_phase": _phase.value,
            "runtime_warming": _runtime_warming,
            "cognitive_warming": _cognitive_warming,
            "cognitive_warmup_done": _cognitive_warmup_done,
            "hydrate_complete": _hydrate_complete,
            "control_plane_alive": True,
            "warmup_elapsed_ms": elapsed_ms,
            "cognitive_elapsed_ms": cognitive_elapsed_ms,
            "cognitive_timeout_sec": _COGNITIVE_TIMEOUT_SEC,
            "minimal_boot": minimal_boot(),
            "cognitive_disabled": cognitive_disabled(),
            "l3": dict(_l3_scheduler_status) if _l3_scheduler_status else None,
        }


def fast_health_payload(runtime: Any = None) -> Dict[str, Any]:
    """Control-plane health — no embedding, no LLM, no table scans."""
    from core.paths import get_project_root, resolve_memory_dir
    from pathlib import Path

    project_root = get_project_root(
        getattr(runtime, "project_root", None) if runtime is not None else None
    )
    memory_dir = Path(
        getattr(runtime, "base_dir", None) or resolve_memory_dir(project_root, "memory")
    )

    blocks_ok = (memory_dir / "blocks" / "index.json").exists() or (memory_dir / "blocks").exists()
    lance_ok = (memory_dir / "lancedb").exists()
    runtime_ok = runtime is not None

    checks = {
        "runtime": {
            "name": "runtime",
            "ok": runtime_ok,
            "detail": "loaded" if runtime_ok else "warming",
        },
        "blocks": {
            "name": "blocks",
            "ok": blocks_ok,
            "path": str(memory_dir / "blocks"),
            "required": True,
            "detail": "exists" if blocks_ok else "missing",
        },
        "lance": {
            "name": "lance",
            "ok": lance_ok,
            "path": str(memory_dir / "lancedb"),
            "required": True,
            "detail": "exists" if lance_ok else "missing",
        },
    }

    deploy = os.environ.get("CNEXUS_DEPLOY_LEVEL", "dev").strip().lower()
    edition = os.environ.get("CNEXUS_EDITION", "personal").strip().lower()
    bundled_desktop = os.environ.get("CNEXUS_AUTO_RUNTIME_WARM", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    relaxed = (
        deploy in ("dev", "internal", "personal")
        or edition == "personal"
        or bundled_desktop
    )

    required_ok = all(item["ok"] for item in checks.values() if item.get("required"))
    if relaxed and runtime_ok:
        required_ok = True
        status = "ready" if blocks_ok or lance_ok else "initializing"
    else:
        status = "ready" if required_ok else "not_ready"

    return {
        "status": status,
        "service": "cnexus",
        "checks": checks,
        "memory_dir": str(memory_dir),
        "mode": "fast",
    }

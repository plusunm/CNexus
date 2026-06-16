"""CNEXUS Control Plane Isolation Kernel v1 — zero-blocking guarantee.

Control plane handlers MUST NOT:
  - run L3 ticks, CDG, or governance
  - perform sync filesystem IO (trace stats, health probes)
  - wait on worker threads or locks held during runtime init

Control plane handlers MAY ONLY:
  - read precomputed atomic flags (boot_protocol)
  - peek runtime pointer (non-blocking global read)
  - return cached snapshots updated by background workers
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional

from core.runtime.boot_protocol import (
    boot_status,
    evaluate_system_ready,
    get_boot_phase,
    is_runtime_warming,
    minimal_boot,
)

# Cached health — refreshed by background worker, never on request path.
_health_lock = threading.Lock()
_cached_memory_ok: bool = True
_cached_memory_status: str = "warming"
_last_health_refresh_mono: Optional[float] = None

RUNTIME_WARM_DELAY_SEC = float(os.environ.get("CNEXUS_RUNTIME_WARM_DELAY_SEC", "1"))


def auto_runtime_warm_enabled() -> bool:
    explicit = os.environ.get("CNEXUS_AUTO_RUNTIME_WARM", "").strip().lower()
    if explicit in ("1", "true", "yes", "on"):
        return True
    if explicit in ("0", "false", "no", "off"):
        return False
    # Isolation default: defer runtime warm — control plane stays responsive.
    return not isolation_enabled()


def isolation_enabled() -> bool:
    flag = os.environ.get("CNEXUS_CONTROL_PLANE_ISOLATION", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def cognitive_workers_enabled() -> bool:
    if minimal_boot():
        return False
    if os.environ.get("CNEXUS_DISABLE_COGNITIVE_WORKERS", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return False
    return True


def self_healing_worker_enabled() -> bool:
    if minimal_boot():
        return False
    flag = os.environ.get("CNEXUS_SELF_HEALING", "0").strip().lower()
    return flag in ("1", "true", "yes", "on")


def probe_event_loop() -> Dict[str, Any]:
    import asyncio

    started = time.monotonic()
    try:
        loop = asyncio.get_event_loop()
        running = loop.is_running()
    except RuntimeError:
        running = False
    elapsed_ms = int((time.monotonic() - started) * 1000)
    return {
        "loop_running": running,
        "loop_time": time.time(),
        "probe_elapsed_ms": elapsed_ms,
        "isolation_enabled": isolation_enabled(),
    }


def update_cached_health(*, memory_ok: bool, memory_status: str) -> None:
    global _cached_memory_ok, _cached_memory_status, _last_health_refresh_mono
    with _health_lock:
        _cached_memory_ok = memory_ok
        _cached_memory_status = memory_status
        _last_health_refresh_mono = time.monotonic()


def get_cached_health() -> Dict[str, Any]:
    with _health_lock:
        return {
            "memory_ok": _cached_memory_ok,
            "memory_status": _cached_memory_status,
            "last_refresh_mono": _last_health_refresh_mono,
        }


def zero_dep_ready_payload(
    *,
    app_started: bool,
    runtime_present: bool,
    token_valid: bool = True,
    license_valid: bool = True,
) -> Dict[str, Any]:
    """IO-free, zero-dependency ready payload — safe under GIL contention."""
    cached = get_cached_health()
    memory_ok = cached["memory_ok"] if runtime_present else True

    status = evaluate_system_ready(
        app_started=app_started,
        runtime_present=runtime_present,
        runtime_warming=is_runtime_warming(),
        memory_ok=memory_ok,
        token_valid=token_valid,
        license_valid=license_valid,
    )

    boot = boot_status()
    return {
        "status": status,
        "boot_phase": get_boot_phase().value,
        "runtime_pointer": runtime_present,
        "control_plane_alive": True,
        "memory": cached["memory_status"] if runtime_present else "warming",
        "isolation": True,
        "boot": boot,
    }

"""Detached daemon workers — never run cognitive/IO on the uvicorn event loop."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Optional

from api.runtime_log import runtime_log


def _sleep(sec: float) -> None:
    time.sleep(sec)


def start_runtime_warm_delayed(
    warm_fn: Callable[[], None],
    *,
    delay_sec: Optional[float] = None,
) -> None:
    """Defer runtime warm so control plane can serve probes first."""
    from core.runtime.control_plane_isolation import RUNTIME_WARM_DELAY_SEC

    delay = RUNTIME_WARM_DELAY_SEC if delay_sec is None else delay_sec

    def _delayed() -> None:
        _sleep(delay)
        warm_fn()

    thread = threading.Thread(target=_delayed, name="cnexus-runtime-warm-delay", daemon=True)
    thread.start()


def start_hydrate_worker(hydrate_fn: Callable[[], None]) -> None:
    thread = threading.Thread(target=hydrate_fn, name="cnexus-hydrate-worker", daemon=True)
    thread.start()


def start_governance_worker(governance_fn: Callable[[], None]) -> None:
    thread = threading.Thread(target=governance_fn, name="cnexus-governance-worker", daemon=True)
    thread.start()


def start_self_healing_worker(healing_fn: Callable[[], None]) -> None:
    thread = threading.Thread(target=healing_fn, name="cnexus-self-healing-worker", daemon=True)
    thread.start()


def _hydrate_loop() -> None:
    from api.deps import RuntimeNotReady, peek_runtime
    from core.runtime.boot_protocol import mark_hydrate_complete, mark_hydrate_started
    from core.runtime.tap_bootstrap import hydrate_execution_stores_sync

    for _ in range(240):
        if peek_runtime() is not None:
            break
        _sleep(0.5)

    try:
        runtime = peek_runtime()
        if runtime is None:
            raise RuntimeNotReady("runtime unavailable for hydrate")
        base = str(runtime.base_dir)
        mark_hydrate_started()
        hydrate_execution_stores_sync(base)
        runtime_log("info", "execution_tap", "Hydrated from disk", base_dir=base)
    except Exception as exc:
        runtime_log("error", "execution_tap", "Hydrate skipped", error=str(exc))
    finally:
        mark_hydrate_complete()


def _governance_loop() -> None:
    import asyncio

    from api.deps import RuntimeNotReady, peek_runtime
    from core.runtime.boot_protocol import cognitive_disabled
    from core.runtime.governance_signal_queue import drain_governance_signals

    for _ in range(240):
        if peek_runtime() is not None:
            break
        _sleep(0.5)

    pending = drain_governance_signals()
    if pending:
        runtime_log("info", "governance", "Drained warmup signals", count=len(pending))

    if cognitive_disabled():
        runtime_log("info", "governance", "Background governance skipped (minimal boot)")
        return

    try:
        runtime = peek_runtime()
        if runtime is None:
            raise RuntimeNotReady("runtime unavailable for background governance")
    except Exception as exc:
        runtime_log("error", "governance", "Background loop skipped", error=str(exc))
        return

    if runtime.config.get("local_stack_bootstrap_models", True):
        bootstrap_flag = os.environ.get("CNEXUS_LOCAL_STACK_BOOTSTRAP_MODELS", "").strip().lower()
        if bootstrap_flag not in ("0", "false", "no", "off"):
            try:
                report = runtime.local_stack.ensure_models()
                runtime_log(
                    "info",
                    "execution",
                    "Local stack bootstrap finished",
                    ok=report.get("ok"),
                    detail=report.get("detail"),
                )
            except Exception as exc:
                runtime_log("error", "execution", "Local stack bootstrap failed", error=str(exc))

    if not runtime.config.get("governance_background_enabled", True):
        runtime_log("info", "governance", "Background governance disabled by config")
        return

    interval = int(runtime.config.get("governance_interval_seconds", 3600))

    async def _run() -> None:
        runtime_log("info", "governance", "Background governance started", interval_seconds=interval)
        await runtime.start_background_governance(interval_seconds=interval)

    try:
        asyncio.run(_run())
    except Exception as exc:
        runtime_log("error", "governance", "Background governance failed", error=str(exc))


def _health_refresh_loop() -> None:
    from api.deps import peek_runtime
    from core.runtime.boot_protocol import fast_health_payload
    from core.runtime.control_plane_isolation import update_cached_health

    while True:
        _sleep(15)
        runtime = peek_runtime()
        if runtime is None:
            update_cached_health(memory_ok=True, memory_status="warming")
            continue
        try:
            deep = fast_health_payload(runtime)
            status = str(deep.get("status", "not_ready"))
            memory_ok = status in ("ready", "degraded", "initializing")
            update_cached_health(memory_ok=memory_ok, memory_status=status)
        except Exception:
            pass


def _self_healing_loop() -> None:
    from core.runtime.self_healing_runtime import run_self_healing_tick, self_healing_enabled

    if not self_healing_enabled():
        return

    runtime_log("info", "self_healing", "Detached self-healing worker started", interval_sec=10)
    while True:
        _sleep(10)
        try:
            result = run_self_healing_tick()
            if result.get("result") not in ("OK", "DISABLED"):
                runtime_log(
                    "info",
                    "self_healing",
                    "Recovery tick",
                    result=result.get("result"),
                    fault=result.get("fault"),
                )
        except Exception as exc:
            runtime_log("warn", "self_healing", "Recovery tick failed", error=str(exc))


def _start_llm_socket_warm() -> None:
    """Pre-warm LLM connection pool (Fast Lane v2) in background."""

    def _run() -> None:
        try:
            from core.runtime.llm_fast_lane_v2 import llm_fast_lane_v2_enabled, warm_llm_socket

            if not llm_fast_lane_v2_enabled():
                return
            import asyncio

            from api.deps import peek_runtime

            asyncio.run(warm_llm_socket(peek_runtime()))
            runtime_log("info", "llm", "LLM socket pool pre-warmed (fast_lane_v2)")
        except Exception as exc:
            runtime_log("debug", "llm", "LLM socket warm skipped", error=str(exc))

    threading.Thread(
        target=_run,
        name="cnexus-llm-socket-warm",
        daemon=True,
    ).start()


def _start_v5_cluster_stack() -> None:
    """Deferred v5 cluster — must not run on uvicorn startup coroutine."""
    _sleep(0.05)
    try:
        from core.kernel.v4.governance_sidecar import start_governance_sidecar
        from core.kernel.v5.global_cluster_runtime import get_global_cluster_runtime
        from core.kernel.v5.self_healing import start_self_healing_cluster

        get_global_cluster_runtime()
        start_governance_sidecar()
        start_self_healing_cluster()
        runtime_log("info", "system", "Non-hang v5 cluster stack started (deferred)")
    except Exception as exc:
        runtime_log("error", "system", "Non-hang v5 cluster stack failed", error=str(exc))


def _start_v4_cluster_stack() -> None:
    _sleep(0.05)
    try:
        from core.kernel.v4.cluster_runtime import get_cluster_runtime
        from core.kernel.v4.governance_sidecar import start_governance_sidecar

        get_cluster_runtime()
        start_governance_sidecar()
        runtime_log("info", "system", "Non-hang v4 cluster stack started (deferred)")
    except Exception as exc:
        runtime_log("error", "system", "Non-hang v4 cluster stack failed", error=str(exc))


def _start_self_healing_if_enabled() -> None:
    from core.runtime.control_plane_isolation import self_healing_worker_enabled

    if not self_healing_worker_enabled():
        return

    from api.deps import peek_runtime
    from api.runtime_healing import execute_recovery_action
    from core.runtime.linkage_debug import collect_linkage_snapshot
    from core.runtime.self_healing_runtime import configure_self_healing

    configure_self_healing(
        recovery_handler=execute_recovery_action,
        snapshot_builder=lambda: collect_linkage_snapshot(
            app_started=True, peek_runtime=peek_runtime
        ),
    )
    start_self_healing_worker(_self_healing_loop)


_post_runtime_workers_started = False
_post_runtime_workers_lock = threading.Lock()


def schedule_post_runtime_workers() -> None:
    """Start cognitive / governance workers only after BrainMemoryRuntime warm succeeds."""
    global _post_runtime_workers_started
    with _post_runtime_workers_lock:
        if _post_runtime_workers_started:
            return
        _post_runtime_workers_started = True

    from api.deps import peek_runtime, start_cognitive_warmup_background
    from core.runtime.control_plane_isolation import cognitive_workers_enabled
    from core.runtime.system_guard import effective_non_hang_tier

    if peek_runtime() is None or not cognitive_workers_enabled():
        return

    runtime_log("info", "system", "Scheduling post-runtime workers (sequential boot)")
    start_cognitive_warmup_background()

    tier = effective_non_hang_tier()
    if tier in ("v1", "v2"):
        start_governance_worker(_deferred_background_governance)
    _start_llm_socket_warm()


def _deferred_background_governance() -> None:
    """Avoid stacking governance asyncio loop on top of runtime warm + L3 ticks."""
    from core.runtime.boot_protocol import cognitive_disabled, is_cognitive_warmup_done

    if cognitive_disabled():
        return
    for _ in range(600):
        if is_cognitive_warmup_done():
            break
        _sleep(0.5)
    _governance_loop()


def start_control_plane_workers(
    *,
    warm_runtime: Callable[[], None],
    start_cognitive_warm: Callable[[], None],
) -> None:
    """Attach runtime pointer hooks only — all heavy work in daemon threads."""
    from core.runtime.control_plane_isolation import (
        auto_runtime_warm_enabled,
        cognitive_workers_enabled,
        self_healing_worker_enabled,
    )
    from core.runtime.system_guard import effective_non_hang_tier

    if auto_runtime_warm_enabled():
        start_runtime_warm_delayed(warm_runtime)
    else:
        runtime_log("info", "system", "Runtime warm deferred (CNEXUS_AUTO_RUNTIME_WARM=0)")
    threading.Thread(
        target=_health_refresh_loop, name="cnexus-health-cache", daemon=True
    ).start()

    if cognitive_workers_enabled():
        tier = effective_non_hang_tier()
        if tier == "v5":
            threading.Thread(
                target=_start_v5_cluster_stack,
                name="cnexus-nonhang-v5-stack",
                daemon=True,
            ).start()
        elif tier == "v4":
            threading.Thread(
                target=_start_v4_cluster_stack,
                name="cnexus-nonhang-v4-stack",
                daemon=True,
            ).start()
        elif tier == "v3":
            from core.kernel.v3.governance_worker_v3 import start_governance_worker_v3

            start_governance_worker_v3()
        start_hydrate_worker(_hydrate_loop)
    else:
        start_hydrate_worker(_minimal_boot_complete)

    _start_self_healing_if_enabled()


def _minimal_boot_complete() -> None:
    from api.deps import peek_runtime
    from core.runtime.boot_protocol import mark_hydrate_complete
    from core.runtime.control_plane_isolation import auto_runtime_warm_enabled

    if not auto_runtime_warm_enabled():
        mark_hydrate_complete()
        runtime_log("info", "system", "Minimal boot — runtime warm deferred")
        return

    for _ in range(240):
        if peek_runtime() is not None:
            break
        _sleep(0.5)
    mark_hydrate_complete()
    runtime_log("info", "system", "Minimal boot — cognitive workers skipped")

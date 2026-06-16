"""Recovery actions for Self-Healing Runtime Layer — wired from API startup."""

from __future__ import annotations

from typing import Any


def execute_recovery_action(action: str) -> bool:
    from api.deps import can_retry_runtime_warm, peek_runtime, warm_runtime_background
    from core.runtime.boot_protocol import BootPhase, cognitive_disabled, get_boot_phase, is_runtime_warming
    from core.runtime.cognitive_warmup_adapter import get_active_warmup_adapter, reset_warmup_adapter
    from core.runtime.execution_trace import configure_execution_trace
    from core.runtime.thread_registry import COGNITIVE_WARM_ROLE, RUNTIME_WARM_ROLE, thread_snapshot
    from api.runtime_warm_status import runtime_warm_meta

    disruptive = {
        "reinject_runtime_pointer",
        "restart_runtime_thread",
        "start_l3_tick_loop",
        "restart_scheduler",
        "flush_queue",
    }
    if action in disruptive:
        warm_meta = runtime_warm_meta()
        if warm_meta.get("warming") or is_runtime_warming():
            return False
        phase = get_boot_phase()
        if phase in (BootPhase.BOOT_2_HYDRATING, BootPhase.BOOT_3_COGNITIVE_WARMING):
            return False
        if warm_meta.get("in_cooldown") and peek_runtime() is None:
            return False

    match action:
        case "reinject_runtime_pointer":
            if peek_runtime() is not None:
                return False
            warm = thread_snapshot(RUNTIME_WARM_ROLE)
            if warm.get("thread_alive"):
                return False
            if not can_retry_runtime_warm():
                return False
            warm_runtime_background()
            return True

        case "restart_runtime_thread":
            if peek_runtime() is not None:
                return False
            warm = thread_snapshot(RUNTIME_WARM_ROLE)
            if warm.get("thread_alive"):
                return False
            if not can_retry_runtime_warm():
                return False
            warm_runtime_background()
            return True

        case "start_l3_tick_loop":
            if cognitive_disabled():
                return False
            if get_boot_phase() == BootPhase.BOOT_4_READY:
                return False
            from api.deps import start_cognitive_warmup_background

            warm = thread_snapshot(COGNITIVE_WARM_ROLE)
            if warm.get("thread_alive"):
                return False
            start_cognitive_warmup_background()
            return True

        case "flush_queue":
            adapter = get_active_warmup_adapter()
            if adapter is None:
                return False
            adapter.scheduler._queue.clear()
            return True

        case "restart_scheduler":
            reset_warmup_adapter()
            warm = thread_snapshot(COGNITIVE_WARM_ROLE)
            if warm.get("thread_alive"):
                return False
            from api.deps import start_cognitive_warmup_background

            start_cognitive_warmup_background()
            return True

        case "rebind_event_bus":
            runtime: Any = peek_runtime()
            if runtime is None:
                return False
            base_dir = str(getattr(runtime, "base_dir", "") or "")
            if not base_dir:
                return False
            configure_execution_trace(base_dir)
            adapter = get_active_warmup_adapter()
            if adapter is not None:
                adapter.scheduler.trace_base_dir = base_dir
            return True

        case _:
            return False

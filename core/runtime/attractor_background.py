"""L3-2 Attractor background scheduling — never block chat fast lane."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from core.governance.cdg.stability_monitor import RecalibrationSignal
from core.runtime.llm_executor_pool import ExecutorPool

logger = logging.getLogger(__name__)

ObserveReadFn = Callable[..., Any]

_fallback_scheduler: Any = None


def resolve_observe_read(runtime: Optional[Any]) -> Optional[ObserveReadFn]:
    """Resolve observe_read via control-plane adapter — no direct SelfModel reads."""
    if runtime is None:
        return None
    try:
        from core.control_plane.legacy_adapter import LegacyDispatchAdapter

        return LegacyDispatchAdapter.from_runtime(runtime).observe_read
    except Exception as exc:
        logger.debug("attractor: observe_read unavailable: %s", exc)
        return None


def resolve_self_model_store(runtime: Optional[Any]) -> Any:
    store = getattr(runtime, "self_model_store", None) if runtime is not None else None
    if store is not None:
        return store
    raise RuntimeError("self_model_store unavailable on runtime")


def get_attractor_scheduler(runtime: Optional[Any], scheduler: Optional[Any] = None) -> Any:
    if scheduler is not None:
        return scheduler
    from core.runtime.cognitive_warmup_adapter import get_active_warmup_adapter

    adapter = get_active_warmup_adapter()
    if adapter is not None:
        return adapter.scheduler
    global _fallback_scheduler
    if _fallback_scheduler is None:
        from core.runtime.l3_scheduler import L3GovernanceScheduler

        _fallback_scheduler = L3GovernanceScheduler()
    if runtime is not None:
        _fallback_scheduler.trace_base_dir = str(getattr(runtime, "base_dir", "") or "")
    return _fallback_scheduler


def enqueue_attractor_recalibration(
    runtime: Any,
    signal: RecalibrationSignal,
    scheduler: Optional[Any] = None,
) -> None:
    """Push recalibration onto L3 queue (cooperative tick drain)."""
    from core.runtime.l3_scheduler import L3Task, L3TaskKind
    from core.personality.attractor.recalibration_loop import run_attractor_recalibration

    sched = get_attractor_scheduler(runtime, scheduler)
    base_dir = str(getattr(runtime, "base_dir", "") or "")

    def _task() -> dict:
        store = resolve_self_model_store(runtime)
        return run_attractor_recalibration(store, signal, base_dir=base_dir)

    sched.enqueue(
        L3Task(
            kind=L3TaskKind.ATTRACTOR_RECALIBRATION,
            fn=_task,
            label="attractor_recalibration",
            estimated_cost_ms=50,
        )
    )
    try:
        sched.run_tick()
    except Exception as exc:
        logger.debug("attractor: tick drain failed: %s", exc)


def schedule_post_interaction_stability_check(
    runtime: Optional[Any],
    scheduler: Optional[Any] = None,
) -> None:
    """Async probe after interaction — enqueues recalibration when governance breaches."""
    ExecutorPool.background_executor().submit(_run_stability_probe, runtime, scheduler)


def _run_stability_probe(runtime: Optional[Any], scheduler: Optional[Any]) -> None:
    try:
        observe_read = resolve_observe_read(runtime)
        if observe_read is None or runtime is None:
            return
        from core.governance.cdg.stability_monitor import get_stability_monitor

        get_stability_monitor().enqueue_recalibration_if_needed(
            observe_read,
            get_attractor_scheduler(runtime, scheduler),
            runtime,
        )
    except Exception as exc:
        logger.debug("attractor stability probe failed: %s", exc)

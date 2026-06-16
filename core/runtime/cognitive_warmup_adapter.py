"""Cognitive warmup adapter — BOOT_3 tick-driven L3 runtime."""

from __future__ import annotations

import os
import logging
import time
from typing import Any, Optional

from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, mark_cognitive_warming, set_l3_scheduler_status
from core.runtime.execution_trace import configure_execution_trace
from core.runtime.l3_scheduler import L3GovernanceScheduler, L3TaskKind
from core.runtime.governance_signal_queue import enqueue_governance_signal
from core.runtime.system_guard import (
    effective_non_hang_tier,
    governance_inline_on_l3_allowed,
)

logger = logging.getLogger(__name__)

_TICK_YIELD_SEC = 0.02
_active_adapter: Optional["CognitiveWarmupAdapter"] = None


def get_active_warmup_adapter() -> Optional["CognitiveWarmupAdapter"]:
    return _active_adapter


def reset_warmup_adapter() -> None:
    global _active_adapter
    _active_adapter = None


class CognitiveWarmupAdapter:
    """Maps blocking warmup into L3-scheduled slices; drives BOOT_3 → BOOT_4."""

    def __init__(self, runtime: Any, scheduler: Optional[Any] = None):
        self.runtime = runtime
        tier = effective_non_hang_tier()
        if tier == "v5":
            from core.kernel.v5.l3_scheduler_v5 import L3SchedulerV5

            self.scheduler = scheduler or L3SchedulerV5()
        elif tier == "v4":
            from core.kernel.v4.l3_scheduler_v4 import L3SchedulerV4

            self.scheduler = scheduler or L3SchedulerV4()
        elif tier == "v3":
            from core.kernel.v3.l3_scheduler_v3 import L3SchedulerV3

            self.scheduler = scheduler or L3SchedulerV3()
        else:
            self.scheduler = scheduler or L3GovernanceScheduler()
        self.scheduler.trace_base_dir = str(getattr(runtime, "base_dir", "") or "")
        configure_execution_trace(self.scheduler.trace_base_dir)
        self.done = False
        self._submitted = False

    def submit(self) -> None:
        if self._submitted:
            return
        self._submitted = True
        mark_cognitive_warming(True)

        specs_v3: list[tuple[str, str, L3TaskKind, int]] = [
            ("cdg_init", "cdg_init", L3TaskKind.CDG_CPU, 8),
            ("memory_warmup", "memory_warmup", L3TaskKind.STORAGE_BATCH, 10),
            ("governance_init", "governance_init", L3TaskKind.CDG_CPU, 25),
            ("reflection_seed", "reflection_seed", L3TaskKind.MEMORY_REFLECT, 5),
        ]

        if effective_non_hang_tier() in ("v3", "v4", "v5"):
            self.scheduler.enqueue_batch(specs_v3)
            return

        rt = self.runtime
        specs_legacy: list[tuple[str, Any, L3TaskKind, int]] = [
            ("cdg_init", lambda: self._task_cdg_init(rt), L3TaskKind.CDG_CPU, 8),
            ("memory_warmup", lambda: self._task_memory_warmup(rt), L3TaskKind.STORAGE_BATCH, 10),
            ("governance_init", lambda: self._task_governance_init(rt), L3TaskKind.CDG_CPU, 25),
            ("reflection_seed", lambda: self._task_reflection_seed(rt), L3TaskKind.MEMORY_REFLECT, 5),
        ]
        self.scheduler.enqueue_batch(specs_legacy)

    @staticmethod
    def _task_cdg_init(runtime: Any) -> None:
        cdg = getattr(runtime, "cdg", None)
        if cdg is None:
            return
        if hasattr(cdg, "trajectory_report"):
            cdg.trajectory_report(last_n=1)

    @staticmethod
    def _task_memory_warmup(runtime: Any) -> None:
        mm = getattr(runtime, "memory_manager", None)
        if mm is not None and hasattr(mm, "block_stats"):
            mm.block_stats()

    @staticmethod
    def _boot_full_governance() -> bool:
        return os.environ.get("CNEXUS_BOOT_FULL_GOVERNANCE", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    @staticmethod
    def _task_governance_init(runtime: Any) -> None:
        """Non-Hang v2: signal-only on L3 — execution owned by cnexus-governance-worker."""
        if not getattr(runtime, "config", {}).get("governance_background_enabled", True):
            return
        if governance_inline_on_l3_allowed():
            if CognitiveWarmupAdapter._boot_full_governance():
                runtime.run_governance_cycle()
                return
            stability = getattr(runtime, "stability", None)
            if stability is not None and hasattr(stability, "run_governance_cycle"):
                stability.run_governance_cycle()
            return
        enqueue_governance_signal({"type": "GOVERNANCE_INIT", "source": "l3_warmup"})
        logger.debug("governance_init: signal enqueued (non-hang kernel v2)")

    @staticmethod
    def _task_reflection_seed(runtime: Any) -> None:
        pipe = getattr(runtime, "reflection_pipeline", None)
        if pipe is not None and hasattr(pipe, "count_due_reviews"):
            pipe.count_due_reviews()

    def tick(self) -> BootPhase:
        """Single L3 heartbeat — non-blocking relative to control plane."""
        if self.done:
            return BootPhase.BOOT_4_READY

        if not self._submitted:
            self.submit()

        result = self.scheduler.run_tick()
        set_l3_scheduler_status(self.l3_status())
        if result.queue_empty:
            self.done = True
            mark_cognitive_warmup_done()
            return BootPhase.BOOT_4_READY

        return BootPhase.BOOT_3_COGNITIVE_WARMING

    def l3_status(self) -> dict:
        return self.scheduler.status_payload()


def run_cognitive_warmup_ticks(
    runtime: Any,
    *,
    max_ticks: Optional[int] = None,
    yield_sec: float = _TICK_YIELD_SEC,
) -> BootPhase:
    """
    Run BOOT_3 cognitive warmup on caller thread (cnexus-cognitive-warm).
    Yields between ticks so GIL returns to the API event loop.
    """
    if max_ticks is None:
        max_ticks = max(200, int(os.environ.get("CNEXUS_COGNITIVE_WARM_MAX_TICKS", "1500")))
    global _active_adapter
    adapter = CognitiveWarmupAdapter(runtime)
    _active_adapter = adapter

    final = BootPhase.BOOT_3_COGNITIVE_WARMING
    for _ in range(max_ticks):
        final = adapter.tick()
        if final == BootPhase.BOOT_4_READY:
            break
        time.sleep(yield_sec)

    if final != BootPhase.BOOT_4_READY:
        logger.warning(
            "Cognitive warmup tick budget exhausted — staying in BOOT_3 until L3 drains "
            "(queue_length=%s, adapter.done=%s)",
            (adapter.l3_status().get("queue_length")),
            adapter.done,
        )

    set_l3_scheduler_status(adapter.l3_status())
    return final

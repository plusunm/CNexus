"""L3 Governance Scheduler — time-sliced cognitive warmup runtime heartbeat."""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, List, Optional

from core.kernel.non_hang_kernel import get_non_hang_kernel
from core.runtime.execution_trace import append_execution_trace
from core.runtime.system_guard import L3_QUEUE_MAX, non_hang_kernel_enabled

logger = logging.getLogger(__name__)


def _slice_ms() -> int:
    return max(10, min(50, int(os.environ.get("CNEXUS_L3_SLICE_MS", "30"))))


def _task_timeout_ms() -> int:
    return max(50, int(os.environ.get("CNEXUS_L3_TASK_TIMEOUT_MS", "3000")))


class L3TaskKind(str, Enum):
    CDG_CPU = "cdg_cpu"
    MEMORY_REFLECT = "memory_reflect"
    LLM_DEFERRED = "llm_deferred"
    STORAGE_BATCH = "storage_batch"
    WARMUP = "warmup"


@dataclass
class L3Task:
    kind: L3TaskKind
    fn: Callable[[], Any]
    label: str = ""
    estimated_cost_ms: int = 5


@dataclass
class TickResult:
    ticks: int
    queue_empty: bool
    remaining: int
    executed: List[str]
    slice_ms: int
    tick_cost_ms: int
    budget_used_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticks": self.ticks,
            "queue_empty": self.queue_empty,
            "remaining": self.remaining,
            "last_executed": self.executed,
            "slice_ms": self.slice_ms,
            "tick_cost_ms": self.tick_cost_ms,
            "budget_used_ms": self.budget_used_ms,
            "mono_ms": int(time.monotonic() * 1000),
        }


@dataclass
class L3GovernanceScheduler:
    """Cooperative scheduler — each tick executes ≤ slice_ms wall time."""

    time_slice_ms: int = field(default_factory=_slice_ms)
    _queue: Deque[L3Task] = field(default_factory=deque)
    _checkpoint: dict[str, Any] = field(default_factory=dict)
    _ticks: int = 0
    _last_tick_result: Optional[TickResult] = None
    trace_base_dir: Optional[str] = None

    def enqueue(self, task: L3Task) -> None:
        if len(self._queue) >= L3_QUEUE_MAX:
            logger.warning("L3 queue full (%s) — dropping task %s", L3_QUEUE_MAX, task.label)
            return
        self._queue.append(task)

    def enqueue_batch(self, specs: List[tuple[str, Callable[[], Any], L3TaskKind, int]]) -> None:
        """Enqueue named warmup tasks: (label, fn, kind, estimated_cost_ms)."""
        for label, fn, kind, cost_ms in specs:
            self.enqueue(
                L3Task(
                    kind=kind,
                    fn=fn,
                    label=label,
                    estimated_cost_ms=max(1, int(cost_ms)),
                )
            )

    def queue_length(self) -> int:
        return len(self._queue)

    def run_tick(self, slice_ms: Optional[int] = None) -> TickResult:
        budget_ms = slice_ms if slice_ms is not None else self.time_slice_ms
        tick_start = time.monotonic()
        executed: List[str] = []
        budget_used_ms = 0

        while self._queue:
            elapsed_ms = int((time.monotonic() - tick_start) * 1000)
            if elapsed_ms >= budget_ms:
                break

            task = self._queue[0]
            if elapsed_ms + task.estimated_cost_ms > budget_ms and executed:
                break

            self._queue.popleft()
            task_start = time.monotonic()
            label = task.label or task.kind.value
            remaining_ms = max(1, budget_ms - int((time.monotonic() - tick_start) * 1000))
            timeout_s = min(remaining_ms, _task_timeout_ms()) / 1000.0

            if non_hang_kernel_enabled():
                result = get_non_hang_kernel().run_bounded(task.fn, timeout_s=timeout_s)
                if result.ok:
                    executed.append(label)
                elif result.status == "killed_timeout":
                    executed.append(f"timeout:{label}")
                else:
                    executed.append(f"err:{label}:{result.error or result.status}")
            else:
                try:
                    task.fn()
                    executed.append(label)
                except Exception as exc:
                    executed.append(f"err:{label}:{exc.__class__.__name__}")

            task_cost = max(1, int((time.monotonic() - task_start) * 1000))
            budget_used_ms += task_cost

        tick_cost_ms = max(0, int((time.monotonic() - tick_start) * 1000))
        self._ticks += 1
        result = TickResult(
            ticks=self._ticks,
            queue_empty=len(self._queue) == 0,
            remaining=len(self._queue),
            executed=executed,
            slice_ms=budget_ms,
            tick_cost_ms=tick_cost_ms,
            budget_used_ms=budget_used_ms,
        )
        self._last_tick_result = result
        self._checkpoint = result.to_dict()
        self._emit_trace(result)
        return result

    def _emit_trace(self, result: TickResult) -> None:
        if not self.trace_base_dir:
            return
        append_execution_trace(
            self.trace_base_dir,
            {
                "type": "l3_tick",
                "ticks": result.ticks,
                "remaining": result.remaining,
                "executed": result.executed,
                "tick_cost_ms": result.tick_cost_ms,
                "queue_empty": result.queue_empty,
            },
        )

    def drained(self) -> bool:
        return len(self._queue) == 0

    def last_tick_result(self) -> Optional[TickResult]:
        return self._last_tick_result

    def status_payload(self) -> dict[str, Any]:
        last = self._last_tick_result
        return {
            "scheduler": "l3-governance",
            "ticks": self._ticks,
            "queue_length": len(self._queue),
            "slice_ms": self.time_slice_ms,
            "last_tick": last.to_dict() if last else None,
        }

    def persist_checkpoint(self) -> dict[str, Any]:
        return dict(self._checkpoint)

    def ready_affecting_ops(self) -> bool:
        """Fast-Path v2 — L3 ticks do not participate in UI ready path."""
        return False

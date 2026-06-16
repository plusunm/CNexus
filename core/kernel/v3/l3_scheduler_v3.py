"""L3 scheduler v3 — signal-only dispatch via event bus (no inline execution)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.kernel.v3.event_bus import TOPIC_L3_DONE, TOPIC_L3_TASK, EventBus, get_event_bus
from core.runtime.l3_scheduler import L3TaskKind, TickResult


@dataclass
class L3SchedulerV3:
    """Publishes warmup work to the bus; execution happens in GovernanceWorkerV3."""

    bus: EventBus = field(default_factory=get_event_bus)
    trace_base_dir: Optional[str] = None
    time_slice_ms: int = 30
    _pending: List[str] = field(default_factory=list)
    _completed: Set[str] = field(default_factory=set)
    _ticks: int = 0
    _last_tick_result: Optional[TickResult] = None

    def enqueue_signal(
        self,
        *,
        label: str,
        handler: str,
        kind: L3TaskKind,
        timeout_s: float = 3.0,
        estimated_cost_ms: int = 5,
    ) -> None:
        self._pending.append(label)
        self.bus.publish(
            TOPIC_L3_TASK,
            {
                "label": label,
                "handler": handler,
                "kind": kind.value,
                "timeout_s": timeout_s,
                "estimated_cost_ms": estimated_cost_ms,
            },
        )

    def enqueue_batch(self, specs: List[tuple[str, str, L3TaskKind, int]]) -> None:
        """(label, handler_name, kind, estimated_cost_ms)."""
        for label, handler, kind, cost_ms in specs:
            self.enqueue_signal(
                label=label,
                handler=handler,
                kind=kind,
                timeout_s=max(1.0, cost_ms / 1000.0),
                estimated_cost_ms=max(1, int(cost_ms)),
            )

    def queue_length(self) -> int:
        self._drain_done_events()
        return max(0, len(self._pending) - len(self._completed))

    def _drain_done_events(self) -> None:
        while True:
            event = self.bus.try_get(TOPIC_L3_DONE)
            if event is None:
                break
            label = str(event.get("label") or "")
            if label:
                self._completed.add(label)

    def run_tick(self, slice_ms: Optional[int] = None) -> TickResult:
        """Signal-only tick — never executes task bodies."""
        tick_start = time.monotonic()
        self._drain_done_events()
        budget_ms = slice_ms if slice_ms is not None else self.time_slice_ms
        remaining = self.queue_length()
        self._ticks += 1
        result = TickResult(
            ticks=self._ticks,
            queue_empty=remaining == 0,
            remaining=remaining,
            executed=["signal_only"],
            slice_ms=budget_ms,
            tick_cost_ms=max(0, int((time.monotonic() - tick_start) * 1000)),
            budget_used_ms=0,
        )
        self._last_tick_result = result
        return result

    def drained(self) -> bool:
        return self.queue_length() == 0

    def last_tick_result(self) -> Optional[TickResult]:
        return self._last_tick_result

    def status_payload(self) -> Dict[str, Any]:
        self._drain_done_events()
        last = self._last_tick_result
        return {
            "scheduler": "l3-signal-v3",
            "ticks": self._ticks,
            "queue_length": self.queue_length(),
            "slice_ms": self.time_slice_ms,
            "pending": list(self._pending),
            "completed": sorted(self._completed),
            "bus": self.bus.stats(),
            "last_tick": last.to_dict() if last else None,
        }

    def persist_checkpoint(self) -> Dict[str, Any]:
        return self.status_payload()

    def is_idle(self) -> bool:
        return self.queue_length() == 0

    def ready_affecting_ops(self) -> bool:
        return False

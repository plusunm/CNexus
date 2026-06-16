"""L3 scheduler v4 — cluster + deterministic log (signal only)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.kernel.v3 import event_bus as _event_bus
from core.kernel.v3.event_bus import TOPIC_L3_DONE
from core.kernel.v4.cluster_runtime import get_cluster_runtime
from core.runtime.l3_scheduler import L3TaskKind, TickResult


@dataclass
class L3SchedulerV4:
    trace_base_dir: Optional[str] = None
    time_slice_ms: int = 30
    _pending: List[str] = field(default_factory=list)
    _completed: Set[str] = field(default_factory=set)
    _ticks: int = 0
    _last_tick_result: Optional[TickResult] = None

    def __post_init__(self) -> None:
        cluster = get_cluster_runtime()
        if self.trace_base_dir:
            cluster.log.configure_persistence(self.trace_base_dir)

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
        get_cluster_runtime().submit(
            {
                "id": uuid.uuid4().hex,
                "type": "l3.task",
                "label": label,
                "handler": handler,
                "kind": kind.value,
                "timeout_s": timeout_s,
                "estimated_cost_ms": estimated_cost_ms,
            }
        )

    def enqueue_batch(self, specs: List[tuple[str, str, L3TaskKind, int]]) -> None:
        for label, handler, kind, cost_ms in specs:
            self.enqueue_signal(
                label=label,
                handler=handler,
                kind=kind,
                timeout_s=max(1.0, cost_ms / 1000.0),
                estimated_cost_ms=max(1, int(cost_ms)),
            )

    def _drain_done_events(self) -> None:
        bus = _event_bus.get_event_bus()
        while True:
            event = bus.try_get(TOPIC_L3_DONE)
            if event is None:
                break
            label = str(event.get("label") or "")
            if label:
                self._completed.add(label)

    def queue_length(self) -> int:
        self._drain_done_events()
        return max(0, len(self._pending) - len(self._completed))

    def run_tick(self, slice_ms: Optional[int] = None) -> TickResult:
        tick_start = time.monotonic()
        self._drain_done_events()
        budget_ms = slice_ms if slice_ms is not None else self.time_slice_ms
        remaining = self.queue_length()
        self._ticks += 1
        result = TickResult(
            ticks=self._ticks,
            queue_empty=remaining == 0,
            remaining=remaining,
            executed=["signal_only_v4"],
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
        cluster = get_cluster_runtime()
        return {
            "scheduler": "l3-cluster-v4",
            "ticks": self._ticks,
            "queue_length": self.queue_length(),
            "slice_ms": self.time_slice_ms,
            "pending": list(self._pending),
            "completed": sorted(self._completed),
            "cluster": cluster.stats(),
            "last_tick": last.to_dict() if last else None,
        }

    def persist_checkpoint(self) -> Dict[str, Any]:
        return self.status_payload()

    def is_idle(self) -> bool:
        return self.queue_length() == 0 and get_cluster_runtime().cluster_healthy()

    def ready_affecting_ops(self) -> bool:
        return False

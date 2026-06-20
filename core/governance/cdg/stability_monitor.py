"""L3-2 stability probe — observe_read('governance_state') → RecalibrationSignal."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.kernel.observe.read_adapter import observe_governance_state

logger = logging.getLogger(__name__)

ObserveReadFn = Callable[..., Any]

DEFAULT_STABILITY_THRESHOLD = 0.6
DEFAULT_VOLATILITY_THRESHOLD = 0.15


@dataclass
class RecalibrationSignal:
    overall_stability_score: float
    reason: str
    observed_at: float = field(default_factory=time.time)


@dataclass
class StabilityMonitor:
    """Probe governance observe surface; emit recalibration signals on breach."""

    threshold: float = DEFAULT_STABILITY_THRESHOLD
    volatility_threshold: float = DEFAULT_VOLATILITY_THRESHOLD
    _last_score: Optional[float] = field(default=None, init=False, repr=False)

    def probe(self, observe_read: ObserveReadFn) -> Optional[RecalibrationSignal]:
        """Read governance_state via observe boundary only — never SelfModel/memory_stats."""
        state = observe_governance_state(observe_read)
        metrics = state.get("stability_metrics") or {}
        score_raw = metrics.get("overall_stability_score", metrics.get("overall_stability"))
        try:
            score = float(score_raw if score_raw is not None else 1.0)
        except (TypeError, ValueError):
            score = 1.0
        score = max(0.0, min(1.0, score))

        signal: Optional[RecalibrationSignal] = None
        if score < self.threshold:
            signal = RecalibrationSignal(
                overall_stability_score=score,
                reason=f"below_threshold:{score:.3f}<{self.threshold:.3f}",
            )
        elif self._last_score is not None:
            drop = self._last_score - score
            if drop >= self.volatility_threshold:
                signal = RecalibrationSignal(
                    overall_stability_score=score,
                    reason=f"volatility:{drop:.3f}>={self.volatility_threshold:.3f}",
                )

        self._last_score = score
        return signal

    def enqueue_recalibration_if_needed(
        self,
        observe_read: ObserveReadFn,
        scheduler: Any,
        runtime: Any,
    ) -> Optional[RecalibrationSignal]:
        signal = self.probe(observe_read)
        if signal is None:
            return None
        from core.runtime.attractor_background import enqueue_attractor_recalibration

        enqueue_attractor_recalibration(runtime, signal, scheduler)
        logger.debug("stability_monitor: enqueued attractor recalibration (%s)", signal.reason)
        return signal


_default_monitor: Optional[StabilityMonitor] = None


def get_stability_monitor() -> StabilityMonitor:
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = StabilityMonitor()
    return _default_monitor


def run_stability_monitor_tick(runtime: Any, scheduler: Any) -> Optional[RecalibrationSignal]:
    """L3 tick hook — probe governance_state and enqueue recalibration when needed."""
    from core.runtime.attractor_background import resolve_observe_read

    observe_read = resolve_observe_read(runtime)
    if observe_read is None:
        return None
    return get_stability_monitor().enqueue_recalibration_if_needed(observe_read, scheduler, runtime)

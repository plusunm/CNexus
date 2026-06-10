"""Attractor Governance — basin depth and lock-in risk."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.governance.cdg.types import AttractorState, BasinDepth

if TYPE_CHECKING:
    from core.self_model.self_model import SelfModel


class AttractorModule:
    """Personality basin stability evaluator."""

    def __init__(self, *, lock_in_threshold: float = 0.8):
        self.lock_in_threshold = lock_in_threshold

    def evaluate(
        self,
        memory: Any,
        self_model: "SelfModel",
        *,
        narrative_coherence: float = 0.85,
        belief_count: int = 0,
    ) -> AttractorState:
        memory_concentration = self._memory_concentration(memory)
        coherence = (self_model.coherence_score + narrative_coherence) / 2.0
        belief_pressure = min(0.25, belief_count * 0.015)

        stability = max(
            0.0,
            min(1.0, coherence * 0.55 + memory_concentration * 0.35 + (1.0 - belief_pressure) * 0.1),
        )
        basin_depth = BasinDepth(depth=stability, stability=stability)

        # Deep, rigid basins increase lock-in risk; shallow basins are unstable but flexible.
        if stability > 0.92:
            lock_in_risk = min(1.0, (stability - 0.75) * 2.2)
        else:
            lock_in_risk = max(0.0, 0.55 - stability)

        return AttractorState(
            basin_depth=basin_depth,
            lock_in_risk=round(lock_in_risk, 4),
        )

    def _memory_concentration(self, memory: Any) -> float:
        if memory is None:
            return 0.5
        try:
            if hasattr(memory, "memory_stats"):
                stats = memory.memory_stats()
            elif hasattr(memory, "collect_stats"):
                stats = memory.collect_stats()
            else:
                return 0.5
            if stats is None:
                return 0.5
            total = max(1, getattr(stats, "total", 0))
            by_layer = getattr(stats, "by_layer", {}) or {}
            protected = sum(by_layer.get(k, 0) for k in ("identity", "goal", "belief"))
            ratio = protected / total
            avg_importance = float(getattr(stats, "avg_importance", 0.5))
            return max(0.0, min(1.0, ratio * 0.6 + avg_importance * 0.4))
        except Exception:
            return 0.5

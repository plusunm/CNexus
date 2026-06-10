"""Plasticity Governance — mutation budgeting (P3)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.governance.cdg.types import DriftSnapshot

if TYPE_CHECKING:
    from runtime.cognitive_state import PersistentCognitiveState


class PlasticityModule:
    """Controls how much the system is allowed to change per cycle."""

    def __init__(
        self,
        *,
        base_budget: float = 0.35,
        mutation_guard: Optional[Any] = None,
    ):
        self.base_budget = base_budget
        self.mutation_guard = mutation_guard

    def compute_mutation_budget(self, state: "PersistentCognitiveState") -> float:
        load_penalty = state.cognitive_load * 0.15
        threat_penalty = state.identity_threat * 0.2
        return max(0.08, self.base_budget - load_penalty - threat_penalty)

    def apply_budget(
        self,
        state: "PersistentCognitiveState",
        drift: DriftSnapshot,
        interaction_text: str = "",
    ) -> "PersistentCognitiveState":
        """Clamp state deformation when drift exceeds budget (P3, P5)."""
        budget = self.compute_mutation_budget(state)
        if drift.max_drift <= budget:
            return state

        scale = budget / max(drift.max_drift, 1e-6)
        state.emotional_intensity = max(
            0.1,
            min(0.95, state.emotional_intensity * (0.85 + scale * 0.15)),
        )
        state.cognitive_load = max(0.1, min(0.95, state.cognitive_load * (0.9 + scale * 0.1)))
        state.identity_threat = max(0.0, state.identity_threat * scale)
        return state

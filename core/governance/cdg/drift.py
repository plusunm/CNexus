"""Drift Governance — deformation detection across identity/narrative/goal axes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.governance.cdg.types import DriftSnapshot, normalized_distance

if TYPE_CHECKING:
    from core.self_model.self_model import SelfModel
    from runtime.cognitive_state import PersistentCognitiveState


class DriftModule:
    """System deformation detector (P4)."""

    def __init__(self, drift_detector: Optional[Any] = None):
        self._detector = drift_detector

    def compute(
        self,
        state: "PersistentCognitiveState",
        self_model: "SelfModel",
        *,
        narrative_summary: str = "",
        narrative_version: int = 0,
    ) -> DriftSnapshot:
        identity_drift = normalized_distance(
            state.goal_focus,
            "identity" if "身份" in self_model.identity_summary else state.goal_focus,
        )
        if state.identity_threat > 0.5:
            identity_drift = max(identity_drift, state.identity_threat * 0.55)

        narrative_drift = normalized_distance(
            narrative_summary or self_model.autobiographical_story[:120],
            self_model.identity_summary[:120],
        )
        narrative_drift = max(
            narrative_drift,
            min(1.0, abs(1.0 - self_model.coherence_score)),
        )

        projected_goal = str(self_model.future_projection.get("focus", state.goal_focus))
        goal_drift = normalized_distance(state.goal_focus, projected_goal)

        reality_drift = max(0.0, state.prediction_error * 0.65)

        if self._detector is not None:
            report = self._detector.detect()
            blended = min(1.0, report.drift_score)
            identity_drift = max(identity_drift, blended * 0.45)
            narrative_drift = max(narrative_drift, blended * 0.35)
            goal_drift = max(goal_drift, blended * 0.25)

        if narrative_version > 0:
            narrative_drift = max(narrative_drift, min(1.0, narrative_version / 100.0))

        return DriftSnapshot(
            identity_drift=round(identity_drift, 4),
            narrative_drift=round(narrative_drift, 4),
            goal_drift=round(goal_drift, 4),
            reality_drift=round(reality_drift, 4),
        )

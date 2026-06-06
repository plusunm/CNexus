"""Predictive Processing loop — prediction error + self-correction."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from core.self_model.self_model import SelfModel
    from runtime.cognitive_state import PersistentCognitiveState

logger = logging.getLogger(__name__)

CORRECTION_THRESHOLD = 0.4


@dataclass
class PredictiveSelf:
    """预测型自我 — 期望 → 观测 → 误差 → 校正."""

    expected_user_behavior: str = "理性、长期主义讨论"
    expected_self_response: str = "稳定、诚实、有连续性"
    prediction_error: float = 0.0
    surprise_level: float = 0.0
    correction_count: int = 0

    def predict_and_update(
        self,
        user_input: str,
        actual_response: str,
        state: "PersistentCognitiveState",
        self_model: "SelfModel | None" = None,
    ) -> float:
        error = self._compute_prediction_error(user_input, actual_response, state)
        self.prediction_error = error
        self.surprise_level = min(1.0, error * 1.8)
        state.prediction_error = error

        if error > CORRECTION_THRESHOLD:
            self._self_correct(error, self_model)

        return error

    def _compute_prediction_error(
        self,
        user_input: str,
        response: str,
        state: "PersistentCognitiveState",
    ) -> float:
        consistency = 0.85
        if any(k in user_input for k in ("稳定", "连续", "身份", "长期")):
            consistency = 0.92
        elif any(k in user_input for k in ("垃圾", "失望", "变了", "不像")):
            consistency = 0.45

        response_match = 0.15 if self.expected_self_response[:4] in response else 0.0
        consistency = min(1.0, consistency + response_match)

        state_mismatch = abs(state.emotional_intensity - 0.5) * 0.25
        threat_penalty = state.identity_threat * 0.35

        return max(0.0, min(1.0, (1.0 - consistency) + state_mismatch + threat_penalty))

    def _self_correct(self, error: float, self_model: "SelfModel | None") -> None:
        self.correction_count += 1
        logger.info("[Predictive Self] prediction error %.2f — self-correction #%d", error, self.correction_count)
        if self_model:
            self_model.self_expectations["consistency"] = min(
                0.98, self_model.self_expectations.get("consistency", 0.9) + error * 0.05
            )
            self_model.self_expectations["stability_under_pressure"] = min(
                0.98, self_model.self_expectations.get("stability_under_pressure", 0.90) + error * 0.03
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

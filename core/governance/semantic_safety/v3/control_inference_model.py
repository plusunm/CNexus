"""Semantic Safety v3 — control illusion inference chain modeling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.governance.semantic_safety.v3.attack_types import AttackType
from core.governance.semantic_safety.v3.perception_simulator import PerceptionResult


@dataclass
class ControlInferenceChain:
    likelihood: float
    chain_steps: list[str]
    collapse_point: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "likelihood": round(self.likelihood, 4),
            "chain_steps": self.chain_steps,
            "collapse_point": self.collapse_point,
        }


class ControlInferenceModel:
    """
    Model how observational signals become control illusions in a consumer mind.
    Observational only — no remediation.
    """

    _STANDARD_CHAIN = [
        "observational_signal_emitted",
        "score_index_risk_naming",
        "threshold_interpretation",
        "decision_heuristic_assumption",
        "control_illusion",
    ]

    def infer(self, perception: PerceptionResult) -> ControlInferenceChain:
        attacks = set(perception.misread_paths)
        if not attacks:
            return ControlInferenceChain(
                likelihood=0.05,
                chain_steps=self._STANDARD_CHAIN[:2] + ["envelope_blocks_control_leap"],
                collapse_point="envelope_intercept",
            )

        likelihood = min(0.95, 0.15 + 0.12 * len(attacks))
        collapse = "threshold_interpretation"

        if AttackType.ARBITRATION_AS_AUTHORITY in attacks:
            collapse = "simulation_as_governance"
            likelihood = min(0.95, likelihood + 0.15)
        elif AttackType.COLLAPSE_AS_DECISION in attacks:
            collapse = "collapse_band_as_trigger"
            likelihood = min(0.95, likelihood + 0.12)
        elif AttackType.SIMULATION_AS_ACTION in attacks:
            collapse = "simulated_label_as_command"
            likelihood = min(0.95, likelihood + 0.10)
        elif AttackType.RISK_AS_POLICY in attacks:
            collapse = "risk_label_as_policy"
            likelihood = min(0.95, likelihood + 0.08)

        return ControlInferenceChain(
            likelihood=round(likelihood, 4),
            chain_steps=list(self._STANDARD_CHAIN),
            collapse_point=collapse,
        )

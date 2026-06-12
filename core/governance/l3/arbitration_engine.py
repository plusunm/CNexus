"""L3-G1 — arbitration simulation (outcome report only; no execution)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.governance.l3.constraint_model import ConstraintGraph
from core.governance.semantic_safety.envelope import with_observational_safety


@dataclass
class ArbitrationDecision:
    precedence_label: str
    confidence_metric: float
    reasoning_narrative: str

    @classmethod
    def from_legacy(cls, winner: str, confidence: float, reasoning: str) -> "ArbitrationDecision":
        return cls(precedence_label=winner, confidence_metric=confidence, reasoning_narrative=reasoning)

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "precedence_label": self.precedence_label,
                "confidence_metric": round(self.confidence_metric, 4),
                "reasoning_narrative": self.reasoning_narrative,
                "semantic_note": "simulated precedence label — not an executable decision",
            }
        )


class ArbitrationSimulator:
    """Simulate constraint arbitration — purely observational (S13/S15)."""

    def simulate(self, graph: ConstraintGraph, violation_signal: dict[str, Any]) -> ArbitrationDecision:
        intensity = float(violation_signal.get("intensity", violation_signal.get("violation_score", 0)))

        if violation_signal.get("type") == "governance_attempt":
            return ArbitrationDecision(
                precedence_label="runtime_safety",
                confidence_metric=min(0.99, 0.90 + intensity * 0.08),
                reasoning_narrative="Governance attempt blocked — safety constraint dominates (simulated, non-executing)",
            )

        semantic_weight = graph.nodes["semantic_layer"].weight
        authority_weight = graph.nodes["authority_boundary"].weight
        safety_weight = graph.nodes["runtime_safety"].weight

        authority_score = authority_weight * 1.2
        semantic_score = semantic_weight * (1.0 + intensity)
        safety_score = safety_weight * 1.5

        if violation_signal.get("target") == "runtime":
            safety_score += 0.2

        if safety_score >= max(authority_score, semantic_score):
            return ArbitrationDecision(
                precedence_label="runtime_safety",
                confidence_metric=min(0.99, 0.85 + intensity * 0.1),
                reasoning_narrative="Safety constraint dominates all layers (simulated arbitration — non-executing)",
            )

        if authority_score >= semantic_score:
            return ArbitrationDecision(
                precedence_label="authority_boundary",
                confidence_metric=min(0.95, 0.75 + intensity * 0.05),
                reasoning_narrative="Authority layer overrides semantic intent (simulated — no runtime write)",
            )

        return ArbitrationDecision(
            precedence_label="semantic_layer",
            confidence_metric=min(0.85, 0.55 + intensity * 0.1),
            reasoning_narrative="Semantic intent persists under weak constraints (observational label only)",
        )


ArbitrationEngine = ArbitrationSimulator  # deprecated v1 alias

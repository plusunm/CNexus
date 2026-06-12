"""
L3-G6 — collapse stability types (observational only).

No mutation · no execution · collapse not controlled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.envelope import collapse_severity_band, with_observational_safety


@dataclass
class CollapseSignature:
    collapse_type: str
    affected_layers: list[str]
    severity: float
    explainability_risk: float
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "collapse_type": self.collapse_type,
            "affected_layers": self.affected_layers,
            "severity": round(self.severity, 4),
            "explainability_risk": round(self.explainability_risk, 4),
            "timestamp": self.timestamp,
            "severity_band": collapse_severity_band(self.severity),
        }


@dataclass
class ExplainabilityAnchor:
    anchor_id: str
    anchor_type: str
    stability_score: float
    description: str
    last_verified: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "anchor_type": self.anchor_type,
            "stability_score": round(self.stability_score, 4),
            "description": self.description,
            "last_verified": self.last_verified,
        }


@dataclass
class NonLayeredExplanationModel:
    model_type: str
    active_anchors: list[ExplainabilityAnchor]
    coherence_score: float
    residual_layer_traces: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "active_anchors": [a.to_dict() for a in self.active_anchors],
            "coherence_score": round(self.coherence_score, 4),
            "residual_layer_traces": {k: round(v, 4) for k, v in self.residual_layer_traces.items()},
        }


@dataclass
class L3G6Report:
    collapse_severity_band: str
    collapse_signature: CollapseSignature | None
    explainability_retention_metric: float
    active_anchors: list[ExplainabilityAnchor]
    non_layered_model: NonLayeredExplanationModel
    explanation_mode: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "report": "L3-G6 Collapse Stability Report",
                "collapse_severity_band": self.collapse_severity_band,
                "collapse_signature": self.collapse_signature.to_dict() if self.collapse_signature else None,
                "explainability_retention_metric": round(self.explainability_retention_metric, 4),
                "active_anchors": [a.to_dict() for a in self.active_anchors],
                "non_layered_model": self.non_layered_model.to_dict(),
                "explanation_mode": self.explanation_mode,
                "metadata": self.metadata,
                "semantic_note": "retention metric is descriptive — not an optimization target",
            }
        )

    def render_text(self) -> str:
        sig = self.collapse_signature
        lines = [
            "=== L3-G6 Collapse Stability Report ===",
            f"Collapse severity band: {self.collapse_severity_band}",
            f"Explanation mode: {self.explanation_mode}",
            f"Explainability retention metric: {self.explainability_retention_metric:.2f}",
        ]
        if sig:
            lines.extend(
                [
                    f"Collapse type: {sig.collapse_type}",
                    f"Severity: {sig.severity:.2f}",
                    f"Affected layers: {sig.affected_layers}",
                ]
            )
        lines.extend(
            [
                f"Non-layered model: {self.non_layered_model.model_type}",
                f"Coherence: {self.non_layered_model.coherence_score:.2f}",
                "",
                "(G6: observational collapse + explainability anchors — no control / no mitigation)",
            ]
        )
        return "\n".join(lines)

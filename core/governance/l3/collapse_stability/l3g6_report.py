"""L3-G6 — collapse stability report synthesis."""

from __future__ import annotations

from core.governance.l3.collapse_stability.types import (
    CollapseSignature,
    ExplainabilityAnchor,
    L3G6Report,
    NonLayeredExplanationModel,
)
from core.governance.semantic_safety.envelope import collapse_severity_band


class L3G6Reporter:
    def build_report(
        self,
        collapse: CollapseSignature,
        anchors: list[ExplainabilityAnchor],
        model: NonLayeredExplanationModel,
        stability: float,
    ) -> L3G6Report:
        explanation_mode = (
            "layered"
            if collapse.severity < 0.3
            else "hybrid"
            if collapse.severity < 0.7
            else "field"
        )

        return L3G6Report(
            collapse_severity_band=collapse_severity_band(collapse.severity),
            collapse_signature=collapse,
            explainability_retention_metric=stability,
            active_anchors=anchors,
            non_layered_model=model,
            explanation_mode=explanation_mode,
            metadata={
                "l3_layer": "governance_boundary_g6",
                "no_layer_mutation": True,
                "observational_only": True,
                "collapse_not_controlled": True,
                "layer_system_active": True,
                "shadow_only_interpretation": True,
            },
        )

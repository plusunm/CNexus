"""L3-G6 — field-based explanation projection when layers blur."""

from __future__ import annotations

from typing import Any

from core.governance.l3.collapse_stability.types import CollapseSignature, ExplainabilityAnchor, NonLayeredExplanationModel


class NonLayeredExplanationProjector:
    """Project hierarchical explanation into field-based explanation (shadow only)."""

    def project(
        self,
        anchors: list[ExplainabilityAnchor],
        collapse_signature: CollapseSignature | None,
        system_state: dict[str, Any],
    ) -> NonLayeredExplanationModel:
        coherence = sum(a.stability_score for a in anchors) / max(1, len(anchors))
        severity = collapse_signature.severity if collapse_signature else 0.0

        residual = {
            "layer_signal_decay": float(system_state.get("layer_signal_decay", 0.0)),
            "hierarchy_blur": severity,
        }

        if coherence > 0.7:
            model_type = "causal_mesh"
        elif coherence > 0.4:
            model_type = "recursive_trace"
        else:
            model_type = "emergent_field"

        if severity > 0.6 and coherence < 0.5:
            model_type = "semantic_resonance"

        return NonLayeredExplanationModel(
            model_type=model_type,
            active_anchors=anchors,
            coherence_score=round(coherence, 4),
            residual_layer_traces=residual,
        )

    def build(self, anchors, collapse_signature, system_state):
        """Deprecated v1 alias for project()."""
        return self.project(anchors, collapse_signature, system_state)


NonLayeredExplanationEngine = NonLayeredExplanationProjector  # deprecated v1 alias

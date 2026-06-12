"""L3-G6 — explainability retention metric under collapse."""

from __future__ import annotations

from core.governance.l3.collapse_stability.types import CollapseSignature, ExplainabilityAnchor


class StabilityEstimator:
    """Estimate explainability retention — no mitigation actions."""

    def estimate(
        self,
        anchors: list[ExplainabilityAnchor],
        collapse_signature: CollapseSignature | None,
    ) -> float:
        if not anchors:
            return 0.0

        anchor_score = sum(a.stability_score for a in anchors) / len(anchors)
        collapse_penalty = collapse_signature.explainability_risk if collapse_signature else 0.0
        return round(max(0.0, anchor_score - collapse_penalty * 0.5), 4)

    def compute(self, anchors, collapse_signature):
        """Deprecated v1 alias for estimate()."""
        return self.estimate(anchors, collapse_signature)


StabilityPreserver = StabilityEstimator  # deprecated v1 alias

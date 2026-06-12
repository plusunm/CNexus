"""L3-G6 — explainability anchor extraction when hierarchy becomes unstable."""

from __future__ import annotations

import time
from typing import Any

from core.governance.l3.collapse_stability.types import ExplainabilityAnchor


class ExplainabilityAnchorExtractor:
    """Extract residual invariants — observational only."""

    def extract(self, system_state: dict[str, Any]) -> list[ExplainabilityAnchor]:
        ts = float(system_state.get("timestamp", time.time()))
        provenance_score = float(system_state.get("provenance_stability", 0.5))
        causal_score = float(system_state.get("causal_trace_strength", 0.5))
        reflexivity = float(system_state.get("reflexivity_coherence", 0.5))
        field_stability = float(system_state.get("field_stability", 0.5))

        return [
            ExplainabilityAnchor(
                anchor_id="provenance_chain",
                anchor_type="provenance_chain",
                stability_score=provenance_score,
                description="trace of origin continuity",
                last_verified=ts,
            ),
            ExplainabilityAnchor(
                anchor_id="causal_trace",
                anchor_type="causal_trace",
                stability_score=causal_score,
                description="causal dependency persistence",
                last_verified=ts,
            ),
            ExplainabilityAnchor(
                anchor_id="reflexivity_trace",
                anchor_type="reflexivity_trace",
                stability_score=reflexivity,
                description="self-observation consistency",
                last_verified=ts,
            ),
            ExplainabilityAnchor(
                anchor_id="field_stability",
                anchor_type="field_stability",
                stability_score=field_stability,
                description="power field stability residual under collapse",
                last_verified=ts,
            ),
        ]


ExplainabilityAnchorManager = ExplainabilityAnchorExtractor  # deprecated v1 alias

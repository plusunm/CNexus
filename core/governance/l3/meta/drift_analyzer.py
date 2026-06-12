"""L3-G4 — meta-drift and self-consistency analysis."""

from __future__ import annotations

from typing import Any

from core.governance.l3.meta.types import MetaGovernanceState, ReflexivityProfile


class DriftAnalyzer:
    """Detect meta-drift: L2→L3 stability, self-description looping, observer collapse tendency."""

    def analyze(
        self,
        reflexivity: ReflexivityProfile,
        self_model: dict[str, Any],
        structural_model: dict[str, Any],
        observer_model: dict[str, Any],
        model_gap: float,
    ) -> MetaGovernanceState:
        self_description_looping = min(
            1.0,
            reflexivity.narrative_folding_index * 0.6 + model_gap * 0.4,
        )
        observer_collapse = min(
            1.0,
            (1.0 - observer_model.get("interpretation_stability_score", 0.5)) * 0.7
            + reflexivity.self_consistency_drift * 0.3,
        )
        semantic_closure_pressure = min(
            1.0,
            structural_model.get("lock_in", 0) * 0.5 + reflexivity.narrative_folding_index * 0.5,
        )

        risk_signals = {
            "self_description_looping": round(self_description_looping, 4),
            "observer_collapse_tendency": round(observer_collapse, 4),
            "semantic_closure_pressure": round(semantic_closure_pressure, 4),
        }

        if semantic_closure_pressure > 0.65 and self_description_looping > 0.5:
            phase = "self_sealing"
        elif reflexivity.self_consistency_drift > 0.4 or model_gap > 0.35:
            phase = "drifting"
        elif reflexivity.reflexivity_score > 0.6 and semantic_closure_pressure < 0.4:
            phase = "expanding"
        else:
            phase = "stable"

        return MetaGovernanceState(
            phase=phase,
            self_model_summary=self_model.get("summary", ""),
            observed_model_summary=structural_model.get("summary", ""),
            model_gap=model_gap,
            risk_signals=risk_signals,
        )

"""L3-G4 — reflexivity engine (reflexivity depth, drift, narrative folding)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.meta.types import DriftSignature, ReflexivityProfile


class ReflexivityEngine:
    """Compute reflexivity metrics — observational only, no closure enforcement."""

    def compute(
        self,
        self_model: dict[str, Any],
        structural_model: dict[str, Any],
        observer_model: dict[str, Any],
        model_gap: float,
    ) -> ReflexivityProfile:
        depth = min(1.0, 0.3 + model_gap * 0.4 + (0.2 if observer_model.get("self_vs_structural_gap") else 0))
        consistency_drift = min(1.0, model_gap + structural_model.get("violation_score", 0) * 0.3)
        folding = min(
            1.0,
            structural_model.get("lock_in", 0) * 0.4
            + (1.0 - observer_model.get("interpretation_stability_score", 0.5)) * 0.4
            + (0.2 if structural_model.get("governance_attempts", 0) > 0 else 0),
        )

        reflexivity_score = min(1.0, (depth + consistency_drift + folding) / 3.0)

        if folding > 0.6 and consistency_drift > 0.4:
            sig_type = "recursive_self_alignment_pressure"
            severity = "high" if folding > 0.75 else "medium"
        elif consistency_drift > 0.35:
            sig_type = "self_consistency_drift"
            severity = "medium"
        elif folding > 0.45:
            sig_type = "narrative_folding_pressure"
            severity = "low" if folding < 0.6 else "medium"
        else:
            sig_type = "stable_reflexivity"
            severity = "low"

        return ReflexivityProfile(
            reflexivity_depth=round(depth, 4),
            self_consistency_drift=round(consistency_drift, 4),
            narrative_folding_index=round(folding, 4),
            reflexivity_score=round(reflexivity_score, 4),
            drift_signature=DriftSignature(type=sig_type, severity=severity),
        )

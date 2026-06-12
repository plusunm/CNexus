"""L3-G4 — observer-of-observer modeling (second-order observation)."""

from __future__ import annotations

from typing import Any


class ObserverModel:
    """
    Model how the system observes its own governance interpretation.
    L3-G4 = system observing its own interpretation of governance.
    """

    def build(
        self,
        self_model: dict[str, Any],
        structural_model: dict[str, Any],
        l3_stack_reports: dict[str, Any],
    ) -> dict[str, Any]:
        g0_summary = (l3_stack_reports.get("g0") or {}).get("summary", {})
        g1_simulation = (l3_stack_reports.get("g1") or {}).get("simulation_result") or {}
        g1_legacy = (l3_stack_reports.get("g1") or {}).get("arbitration_result") or {}
        g3_opt = (l3_stack_reports.get("g3") or {}).get("optimization", {})

        observer_layers = {
            "L1_runtime": "not directly observed by L3 (boundary enforced)",
            "L2_semantic": "feeds L3 via coupling harness only",
            "L3_governance": "primary observation target",
            "L3_meta": "observer observing L3 self-description vs structure",
        }

        interpretation_stability = 1.0 - float(structural_model.get("field_entropy", 0)) * 0.5
        interpretation_stability -= float(structural_model.get("violation_score", 0)) * 0.3
        interpretation_stability = max(0.0, min(1.0, interpretation_stability))

        return {
            "observer_layers": observer_layers,
            "l2_interprets_l3_stably": interpretation_stability >= 0.5,
            "l3_interprets_g_stack_stably": g0_summary.get("violations_detected", 0) <= 2,
            "simulated_precedence_label": g1_simulation.get("precedence_label")
            or g1_legacy.get("winner", "unknown"),
            "simulated_optimization_count": len(g3_opt.get("simulated_optimization", [])),
            "self_vs_structural_gap": self_model.get("summary", "") != structural_model.get("summary", ""),
            "interpretation_stability_score": round(interpretation_stability, 4),
        }

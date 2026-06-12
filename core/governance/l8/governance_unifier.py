"""L8 — governance graph unifier (G0–G7 → surface projection)."""

from __future__ import annotations

from typing import Any

from core.governance.l8.types import GovernanceSurface

_BAND_SCORES = {"low": 0.2, "baseline": 0.35, "elevated": 0.6, "high": 0.75, "critical": 0.9}


def _band(value: Any, default: float = 0.4) -> float:
    if isinstance(value, (int, float)):
        return round(max(0.0, min(1.0, float(value))), 4)
    if isinstance(value, str):
        return _BAND_SCORES.get(value.lower(), default)
    return default


class GovernanceUnifier:
    def flatten_governance_graph(self, l3_data: dict[str, Any]) -> dict[str, float]:
        g0 = l3_data.get("G0") or {}
        g1 = l3_data.get("G1") or {}
        g2 = l3_data.get("G2") or {}
        g3 = l3_data.get("G3") or {}
        g4 = l3_data.get("G4") or {}
        g5 = l3_data.get("G5") or {}
        g6 = l3_data.get("G6") or {}
        g7 = l3_data.get("G7") or {}

        return {
            "authority_visibility": _band(g0.get("authority_leakage_band") or g0.get("leakage_band"), 0.3),
            "constraint_density": _band(g1.get("violation_score") or g1.get("constraint_pressure"), 0.45),
            "simulation_shadow": _band(g2.get("shadow_impact_band") or g2.get("impact_band"), 0.4),
            "field_optimization": _band(g3.get("stability_band") or g3.get("field_stability"), 0.5),
            "reflexivity_drift": _band(g4.get("meta_drift_band") or g4.get("reflexivity_band"), 0.35),
            "meta_governance": _band(g5.get("layer_genesis_band") or g5.get("meta_band"), 0.3),
            "collapse_stability": _band(g6.get("collapse_severity_band"), 0.4),
            "layerless_projection": _band(g7.get("field_coherence") or g7.get("coherence"), 0.55),
        }

    def extract_control_surfaces(self, flat_graph: dict[str, float]) -> list[str]:
        return [k for k, v in flat_graph.items() if v >= 0.55]

    def governance_null_space(self, flat_graph: dict[str, float]) -> int:
        """Count dimensions below activation threshold — observational null space."""
        return sum(1 for v in flat_graph.values() if v < 0.45)

    def build_surface(self, l3_data: dict[str, Any]) -> GovernanceSurface:
        flat = self.flatten_governance_graph(l3_data)
        return GovernanceSurface(
            control_surfaces=self.extract_control_surfaces(flat),
            null_space_dim=self.governance_null_space(flat),
            flat_graph=flat,
        )

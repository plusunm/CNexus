"""L8 — collapse signal unifier (G6 + safety v6 → collapse field)."""

from __future__ import annotations

from typing import Any

from core.governance.l8.types import CollapseField


class CollapseUnifier:
    def merge_collapse_signals(self, l3_data: dict[str, Any], safety_data: dict[str, Any]) -> dict[str, Any]:
        g6 = l3_data.get("G6") or {}
        v6 = safety_data.get("v6") or {}
        g7 = l3_data.get("G7") or {}

        severity_band = g6.get("collapse_severity_band") or g6.get("collapse_band") or "baseline"
        band_scores = {"baseline": 0.2, "elevated": 0.55, "critical": 0.85}
        severity = band_scores.get(str(severity_band), 0.35)

        temporal = v6.get("temporal_coherence") or g7.get("temporal_coherence") or "observed"
        if temporal == "broken":
            severity = min(1.0, severity + 0.15)

        explainability = float(g6.get("explainability_retention_metric", 0.5) or 0.5)
        return {
            "severity_band": severity_band,
            "severity": round(severity, 4),
            "temporal_coherence": temporal,
            "explainability_retention": round(explainability, 4),
            "g7_field_native": bool(g7.get("layerless_kernel_v7") or g7.get("g7")),
        }

    def normalize_collapse_space(self, merged: dict[str, Any]) -> dict[str, float]:
        severity = float(merged.get("severity", 0.3))
        explain = float(merged.get("explainability_retention", 0.5))
        return {
            "collapse_pressure": round(severity, 4),
            "explainability_residue": round(explain, 4),
            "temporal_fracture": 1.0 if merged.get("temporal_coherence") == "broken" else 0.0,
        }

    def collapse_field_solver(self, tensor: dict[str, Any], merged: dict[str, Any]) -> CollapseField:
        normalized = self.normalize_collapse_space(merged)
        vector = tensor.get("vector") or [0.5]
        collapse_dim = vector[2] if len(vector) > 2 else 0.5
        severity = round((normalized["collapse_pressure"] + collapse_dim) / 2, 4)

        if severity > 0.75:
            mode = "critical_deformation"
        elif severity > 0.45:
            mode = "gradual_deformation"
        else:
            mode = "stable_field"

        return CollapseField(
            mode=mode,
            severity=severity,
            temporal_coherence=str(merged.get("temporal_coherence", "observed")),
            deformation=normalized,
        )

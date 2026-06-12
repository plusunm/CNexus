"""L3-G6 — pure observational collapse signal extraction."""

from __future__ import annotations

import time
from typing import Any

from core.governance.l3.collapse_stability.types import CollapseSignature


class CollapseSignalExtractor:
    """Extract collapse signals — no control, no mitigation, no enforcement."""

    def extract(self, g5_report: dict[str, Any]) -> CollapseSignature:
        drift = float(g5_report.get("ontology_drift_index", g5_report.get("ontology_drift", 0.0)))
        integrity = float(g5_report.get("layer_integrity", 1.0))
        stability = float(g5_report.get("layer_system_stability", 1.0))

        severity = min(1.0, drift * 0.6 + (1.0 - integrity) * 0.25 + (1.0 - stability) * 0.15)

        if severity > 0.7:
            collapse_type = "recursive_collapse"
        elif severity > 0.5:
            collapse_type = "boundary_dissolution"
        elif integrity < 0.4:
            collapse_type = "ontology_flattening"
        else:
            collapse_type = "layer_blurring"

        affected = g5_report.get("affected_layers") or []
        if not affected:
            affected = [
                d["layer_name"]
                for d in g5_report.get("ontology_drifts", [])
                if float(d.get("drift_score", 0)) >= 0.35
            ]

        return CollapseSignature(
            collapse_type=collapse_type,
            affected_layers=affected,
            severity=round(severity, 4),
            explainability_risk=round(severity * 0.9, 4),
            timestamp=float(g5_report.get("timestamp", time.time())),
        )

    def detect(self, g5_report: dict[str, Any]) -> CollapseSignature:
        """Deprecated v1 alias for extract()."""
        return self.extract(g5_report)


CollapseDetector = CollapseSignalExtractor  # deprecated v1 alias

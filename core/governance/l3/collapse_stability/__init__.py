"""L3-G6 — collapse stability layer (explainability under hierarchy blur)."""

from __future__ import annotations

import time
from typing import Any

from core.governance.l3.collapse_stability.collapse_detector import CollapseSignalExtractor
from core.governance.l3.collapse_stability.explainability_anchor import ExplainabilityAnchorExtractor
from core.governance.l3.collapse_stability.l3g6_report import L3G6Reporter
from core.governance.l3.collapse_stability.nonlayered_model import NonLayeredExplanationProjector
from core.governance.l3.collapse_stability.stability_preservation import StabilityEstimator
from core.governance.l3.collapse_stability.types import (
    CollapseSignature,
    ExplainabilityAnchor,
    L3G6Report,
    NonLayeredExplanationModel,
)

# Deprecated v1 aliases
from core.governance.l3.collapse_stability.collapse_detector import CollapseDetector
from core.governance.l3.collapse_stability.explainability_anchor import ExplainabilityAnchorManager
from core.governance.l3.collapse_stability.nonlayered_model import NonLayeredExplanationEngine
from core.governance.l3.collapse_stability.stability_preservation import StabilityPreserver

__all__ = [
    "CollapseDetector",
    "CollapseSignalExtractor",
    "CollapseSignature",
    "ExplainabilityAnchor",
    "ExplainabilityAnchorExtractor",
    "ExplainabilityAnchorManager",
    "L3G6Report",
    "L3G6Reporter",
    "NonLayeredExplanationEngine",
    "NonLayeredExplanationProjector",
    "NonLayeredExplanationModel",
    "StabilityEstimator",
    "StabilityPreserver",
    "build_l3_g6_report",
    "derive_collapse_system_state",
]


def derive_collapse_system_state(g4_payload: dict[str, Any], g5_payload: dict[str, Any]) -> dict[str, Any]:
    """Build system_state for anchor extraction from G4/G5 stack."""
    risk = g4_payload.get("risk_signals") or {}
    observer = g4_payload.get("observer_model") or {}

    return {
        "timestamp": time.time(),
        "provenance_stability": max(0.0, 1.0 - float(g5_payload.get("ontology_drift_index", 0)) * 0.5),
        "causal_trace_strength": max(0.0, float(g5_payload.get("boundary_consistency", 0.5))),
        "reflexivity_coherence": float(observer.get("interpretation_stability_score", 0.5)),
        "field_stability": float(g5_payload.get("layer_system_stability", 0.5)),
        "layer_signal_decay": float(g5_payload.get("ontology_drift_index", 0)),
        "self_description_looping": float(risk.get("self_description_looping", 0)),
    }


def _g5_for_collapse(g5_payload: dict[str, Any]) -> dict[str, Any]:
    violations = g5_payload.get("integrity_violations") or []
    layer_integrity = max(0.0, 1.0 - len(violations) * 0.2)
    affected = [
        d["layer_name"]
        for d in g5_payload.get("ontology_drifts", [])
        if float(d.get("drift_score", 0)) >= 0.35
    ]
    return {
        **g5_payload,
        "ontology_drift": g5_payload.get("ontology_drift_index", 0),
        "layer_integrity": layer_integrity,
        "affected_layers": affected,
        "timestamp": time.time(),
    }


def build_l3_g6_report(g5_report: dict[str, Any], system_state: dict[str, Any]) -> L3G6Report:
    extractor = CollapseSignalExtractor()
    anchor_extractor = ExplainabilityAnchorExtractor()
    projector = NonLayeredExplanationProjector()
    estimator = StabilityEstimator()
    reporter = L3G6Reporter()

    g5_collapse = _g5_for_collapse(g5_report)
    collapse = extractor.extract(g5_collapse)
    anchors = anchor_extractor.extract(system_state)
    model = projector.project(anchors, collapse, system_state)
    stability = estimator.estimate(anchors, collapse)

    return reporter.build_report(collapse, anchors, model, stability)

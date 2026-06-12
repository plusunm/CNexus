"""L3-G7 — collapse L3 stack into field-native bundle (layers as projection only)."""

from __future__ import annotations

import time
from typing import Any


def derive_l3_bundle_from_stack(
    *,
    g0: dict[str, Any] | None = None,
    g3: dict[str, Any] | None = None,
    g4: dict[str, Any] | None = None,
    g5: dict[str, Any] | None = None,
    g6: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Flatten G0–G6 observational outputs into a layerless bundle.
    Layer IDs are discarded; only field/attractor/trace signals remain.
    """
    g3 = g3 or {}
    g4 = g4 or {}
    g5 = g5 or {}
    g6 = g6 or {}
    g0 = g0 or {}

    stability = g3.get("stability") or {}
    attractor_map = g3.get("attractor_map") or {}
    power_field = g3.get("power_field") or {}

    nodes = power_field.get("nodes") or []
    if nodes:
        coupling = sum(float(n.get("strength", 0.5)) for n in nodes) / len(nodes)
    elif stability:
        coupling = max(0.0, min(1.0, 1.0 - float(stability.get("entropy", 0.5))))
    else:
        coupling = 0.5

    collapse_sig = g6.get("collapse_signature")
    if isinstance(collapse_sig, dict):
        drift = float(collapse_sig.get("severity", g5.get("ontology_drift_index", 0.5)))
    else:
        drift = float(g5.get("ontology_drift_index", 0.5))

    retention = float(g6.get("explainability_retention_metric", g6.get("explainability_retention_score", g5.get("layer_system_stability", 0.5))))
    boundary = float(g5.get("boundary_consistency", 0.5))

    attractors: list[dict[str, Any]] = []
    for item in attractor_map.get("attractors") or []:
        if isinstance(item, dict):
            attractors.append(
                {
                    "id": item.get("node", item.get("id", "unknown")),
                    "strength": float(item.get("depth", item.get("strength", 0.5))),
                    "basin": item.get("type", "power_field"),
                }
            )
    for node_id, strength in (attractor_map.get("nodes") or {}).items():
        attractors.append({"id": node_id, "strength": float(strength), "basin": "power_field"})
    for anchor in g6.get("active_anchors") or []:
        if isinstance(anchor, dict):
            attractors.append(
                {
                    "id": anchor.get("anchor_id", "anchor"),
                    "strength": float(anchor.get("stability_score", 0.5)),
                    "basin": anchor.get("anchor_type", "explainability"),
                }
            )

    ts = time.time()
    traces: list[dict[str, Any]] = []
    for signal_name, value in (g4.get("risk_signals") or {}).items():
        traces.append({"timestamp": ts, "signal_type": "risk", "payload": {signal_name: value}})
    observer = g4.get("observer_model") or {}
    if observer:
        traces.append({"timestamp": ts, "signal_type": "observer", "payload": observer})
    collapse = g6.get("collapse_signature")
    if collapse:
        traces.append({"timestamp": ts, "signal_type": "collapse", "payload": collapse})
    for boundary_item in g0.get("boundaries") or []:
        traces.append({"timestamp": ts, "signal_type": "boundary_projection", "payload": boundary_item})

    return {
        "coupling_strength": coupling,
        "drift_index": drift,
        "stability_score": max(0.0, min(1.0, (retention + boundary) / 2.0)),
        "attractors": attractors,
        "trace_events": traces,
    }

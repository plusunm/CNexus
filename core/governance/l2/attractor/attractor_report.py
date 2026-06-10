"""
GTBS-L2.5 — latent attractor inference report synthesis.
"""

from __future__ import annotations

from typing import Any

from core.governance.l2.attractor.types import (
    AttractorField,
    GTBSL2AttractorReport,
    TopologySignature,
)
from core.governance.l2.fusion.types import GTBSL2FusionReport


def _risk_surface(
    field: AttractorField,
    topology: TopologySignature,
    fusion_report: GTBSL2FusionReport,
) -> dict[str, float]:
    sig = fusion_report.coupling_signals or {}
    div_trend = sig.get("shadow_divergence_trend", "stable")
    align_rre = abs(float(sig.get("alignment_x_rre", 0.0)))

    lock_in = topology.lock_in_probability
    fragmentation = min(1.0, field.global_entropy * (1.0 - field.coupling_density + 0.2))
    reality_detach = 0.2
    if div_trend == "rising":
        reality_detach += 0.25
    if align_rre < 0.3:
        reality_detach += 0.15
    reality_detach = min(1.0, reality_detach)

    return {
        "lock_in_risk": round(lock_in, 2),
        "fragmentation_risk": round(fragmentation, 2),
        "reality_detachment_risk": round(reality_detach, 2),
    }


def _interpretation(field: AttractorField, topology: TopologySignature) -> str:
    dominant = [a for a in field.attractors if a.attractor_id == topology.dominant_attractor]
    dom_type = dominant[0].attractor_type if dominant else "unresolved"
    dom_class = dominant[0].stability_class if dominant else "emerging"
    n_strong = sum(1 for a in field.attractors if a.strength >= 0.55)

    if field.field_regime == "locked":
        return (
            f"System exhibits locked attractor regime with dominant {dom_type} "
            f"({dom_class}); cross-stream coupling density {field.coupling_density:.2f}."
        )
    if n_strong >= 1:
        return (
            f"System is forming {n_strong} dominant attractor basin(s) with "
            f"moderate narrative reinforcement pressure ({dom_type}, {dom_class})."
        )
    if field.field_regime == "diffuse":
        return (
            "Observational field remains diffuse — no dominant latent attractor "
            "has formed beneath cross-stream coupling signals."
        )
    return (
        f"Field regime: {field.field_regime}; global entropy {field.global_entropy:.2f}; "
        "latent structure inference is observational only (S11/S12)."
    )


def build_attractor_report(
    fusion_report: GTBSL2FusionReport,
    field: AttractorField,
    topology: TopologySignature,
) -> GTBSL2AttractorReport:
    """Synthesize L2.5 attractor inference report."""
    ranked = sorted(field.attractors, key=lambda a: a.strength, reverse=True)
    dominant = [a.to_dict() for a in ranked[:2] if a.strength >= 0.35]

    return GTBSL2AttractorReport(
        time_range=fusion_report.time_range,
        field_regime=field.field_regime,
        global_entropy=field.global_entropy,
        coupling_density=field.coupling_density,
        dominant_attractors=dominant,
        topology=topology.to_dict(),
        risk_surface=_risk_surface(field, topology, fusion_report),
        interpretation=_interpretation(field, topology),
        attractor_field=field.to_dict(),
        metadata={
            "l2_layer": "semantic_alignment_attractor",
            "read_only": True,
            "instrumentation_only": True,
            "no_control_leakage": True,
            "attractor_not_decision": True,
            "no_cdg_influence": True,
            "no_mutation_budget": True,
            "no_runtime_changes": True,
        },
    )

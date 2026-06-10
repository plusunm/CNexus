"""
GTBS-L2.5 — attractor inference engine (fusion field → latent structure).

S11 No Control Leakage | S12 Attractor ≠ Decision
"""

from __future__ import annotations

from typing import Any

from core.governance.l2.attractor.field_to_latent import compress_field_to_latent
from core.governance.l2.attractor.stability_topology import compute_topology
from core.governance.l2.attractor.types import AttractorField, TopologySignature
from core.governance.l2.fusion.types import GTBSL2FusionReport


class AttractorInferenceEngine:
    """Infer latent attractor field from v0.3 fusion report + temporal trend signals."""

    def infer(
        self,
        fusion_report: GTBSL2FusionReport,
        trend_signals: dict[str, Any] | None = None,
    ) -> tuple[AttractorField, TopologySignature]:
        field = compress_field_to_latent(fusion_report, trend_signals=trend_signals)
        topology = compute_topology(field)
        return field, topology


def build_attractor_field(
    fusion_report: GTBSL2FusionReport,
    trend_signals: dict[str, Any] | None = None,
) -> AttractorField:
    """Primary bridge entry: fusion report → latent attractor field."""
    field, _ = AttractorInferenceEngine().infer(fusion_report, trend_signals=trend_signals)
    return field

"""GTBS-L2 v0.3 — cross-stream semantic fusion (field cognition)."""

from core.governance.l2.fusion.cross_stream_builder import build_cross_stream_field
from core.governance.l2.fusion.fusion_synthesizer import FusionSynthesizer
from core.governance.l2.fusion.semantic_coupling_engine import SemanticCouplingEngine
from core.governance.l2.fusion.types import (
    CrossStreamCouplingMatrix,
    CrossStreamField,
    GTBSL2FusionReport,
)

__all__ = [
    "CrossStreamCouplingMatrix",
    "CrossStreamField",
    "FusionSynthesizer",
    "GTBSL2FusionReport",
    "SemanticCouplingEngine",
    "build_cross_stream_field",
]


def build_fusion_report(base_dir: str, window_days: int = 7) -> GTBSL2FusionReport:
    """End-to-end fusion pipeline (read-only)."""
    field = build_cross_stream_field(base_dir, window_days=window_days)
    field = SemanticCouplingEngine().analyze(field)
    return FusionSynthesizer().synthesize(field)

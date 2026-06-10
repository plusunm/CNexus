"""GTBS-L2.5 — observational field → latent attractor bridge."""

from core.governance.l2.attractor.attractor_inference_engine import (
    AttractorInferenceEngine,
    build_attractor_field,
)
from core.governance.l2.attractor.attractor_report import build_attractor_report
from core.governance.l2.attractor.types import (
    AttractorField,
    GTBSL2AttractorReport,
    LatentAttractorState,
    TopologySignature,
)
from core.governance.l2.fusion import build_fusion_report
from core.governance.l2.loader import load_temporal_window
from core.governance.l2.temporal.trajectory_synthesizer import TrajectorySynthesizer

__all__ = [
    "AttractorField",
    "AttractorInferenceEngine",
    "GTBSL2AttractorReport",
    "LatentAttractorState",
    "TopologySignature",
    "build_attractor_field",
    "build_attractor_report",
    "build_attractor_inference_report",
]


def build_attractor_inference_report(base_dir: str, window_days: int = 7) -> GTBSL2AttractorReport:
    """End-to-end L2.5 pipeline: fusion → latent field → attractor report."""
    fusion_report = build_fusion_report(base_dir, window_days=window_days)
    temporal = load_temporal_window(base_dir, window_days=window_days)
    trend_signals = TrajectorySynthesizer().trend_signals(temporal)
    trend_signals.update(fusion_report.coupling_signals or {})

    engine = AttractorInferenceEngine()
    field, topology = engine.infer(fusion_report, trend_signals=trend_signals)
    return build_attractor_report(fusion_report, field, topology)

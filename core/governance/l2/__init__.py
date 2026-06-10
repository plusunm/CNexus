"""
GTBS-L2 Semantic Alignment Layer v0.1

Read-only semantic interpretation — S1–S5 (see GTBS_L2_Semantic_Alignment.md).
"""

from core.governance.l2.attractor import GTBSL2AttractorReport, build_attractor_field, build_attractor_inference_report
from core.governance.l2.fusion import GTBSL2FusionReport, build_fusion_report
from core.governance.l2.loader import (
    generate_l2_narrative,
    load_attractor_report,
    load_fusion_report,
    load_snapshot_from_base_dir,
    load_temporal_window,
)
from core.governance.l2.render import (
    GTBSL2Renderer,
    L2_ATTRACTOR_VERSION,
    L2_FUSION_VERSION,
    L2_TEMPORAL_VERSION,
    L2_VERSION,
)
from core.governance.l2.snapshot import GTBSSnapshot
from core.governance.l2.temporal import L2TemporalReport, L2TemporalWindow, TrajectorySynthesizer

__all__ = [
    "GTBSL2AttractorReport",
    "GTBSL2FusionReport",
    "GTBSL2Renderer",
    "GTBSSnapshot",
    "L2TemporalReport",
    "L2TemporalWindow",
    "L2_ATTRACTOR_VERSION",
    "L2_FUSION_VERSION",
    "L2_TEMPORAL_VERSION",
    "L2_VERSION",
    "TrajectorySynthesizer",
    "build_attractor_field",
    "build_attractor_inference_report",
    "build_fusion_report",
    "generate_l2_narrative",
    "load_attractor_report",
    "load_fusion_report",
    "load_snapshot_from_base_dir",
    "load_temporal_window",
]

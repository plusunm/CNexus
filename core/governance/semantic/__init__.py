"""
GTBS-L2 Semantic Alignment — backward-compatible facade.

Canonical implementation: core.governance.l2
"""

from core.governance.l2 import (
    GTBSL2Renderer,
    GTBSSnapshot,
    L2_VERSION,
    generate_l2_narrative,
    load_snapshot_from_base_dir,
)
from core.governance.semantic.compat import build_semantic_snapshot
from core.governance.semantic.compat import SemanticAlignmentInterpreter
from core.governance.semantic.compat import LongitudinalSemanticSummary

SEMANTIC_LAYER_VERSION = L2_VERSION.replace("L2_", "")

__all__ = [
    "GTBSL2Renderer",
    "GTBSSnapshot",
    "L2_VERSION",
    "SEMANTIC_LAYER_VERSION",
    "SemanticAlignmentInterpreter",
    "LongitudinalSemanticSummary",
    "build_semantic_snapshot",
    "generate_l2_narrative",
    "load_snapshot_from_base_dir",
]

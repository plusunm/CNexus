"""
CNexus Semantic Safety v6 — Cognitive Dissolution Layer.

Removes preconditions for stable temporal/narrative interpretation structures.
"""

from __future__ import annotations

from typing import Any

from core.governance.semantic_safety.v6.cognitive_dissolution import (
    CognitiveDissolutionLayer,
    DissolutionResult,
    apply_cognitive_dissolution,
)
from core.governance.semantic_safety.v6.v6_report import SemanticSafetyV6Report, SemanticSafetyV6Reporter

__all__ = [
    "CognitiveDissolutionLayer",
    "DissolutionResult",
    "SemanticSafetyV6Report",
    "SemanticSafetyV6Reporter",
    "apply_cognitive_dissolution",
    "build_semantic_safety_v6_report",
]


def build_semantic_safety_v6_report(
    signals: dict[str, dict[str, Any]] | None = None,
    *,
    use_l3_stack: bool = True,
    through_v5: bool = True,
) -> SemanticSafetyV6Report:
    if signals is None and use_l3_stack:
        from core.governance.l3 import build_l3_g1_report, build_l3_g6_report, build_l3_g7_report

        signals = {
            "L3-G1": build_l3_g1_report(use_l2_coupling=False).to_dict(),
            "L3-G6": build_l3_g6_report(use_l2_coupling=False).to_dict(),
            "L3-G7": build_l3_g7_report(use_l2_coupling=False).to_dict(),
        }
    signals = signals or {}
    return SemanticSafetyV6Reporter().build(signals, through_v5=through_v5)

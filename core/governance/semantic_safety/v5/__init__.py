"""
CNexus Semantic Safety v5 — Interpretation Isolation Layer.

Prevents stable governance-interpretation structures from forming at the output boundary.
"""

from __future__ import annotations

from typing import Any

from core.governance.semantic_safety.v5.interpretation_isolation import (
    InterpretationIsolationLayer,
    IsolationResult,
    apply_interpretation_isolation,
)
from core.governance.semantic_safety.v5.v5_report import SemanticSafetyV5Report, SemanticSafetyV5Reporter

__all__ = [
    "InterpretationIsolationLayer",
    "IsolationResult",
    "SemanticSafetyV5Report",
    "SemanticSafetyV5Reporter",
    "apply_interpretation_isolation",
    "build_semantic_safety_v5_report",
]


def build_semantic_safety_v5_report(
    signals: dict[str, dict[str, Any]] | None = None,
    *,
    use_l3_stack: bool = True,
    through_v4: bool = True,
) -> SemanticSafetyV5Report:
    if signals is None and use_l3_stack:
        from core.governance.l3 import build_l3_g1_report, build_l3_g6_report, build_l3_g7_report

        signals = {
            "L3-G1": build_l3_g1_report(use_l2_coupling=False).to_dict(),
            "L3-G6": build_l3_g6_report(use_l2_coupling=False).to_dict(),
            "L3-G7": build_l3_g7_report(use_l2_coupling=False).to_dict(),
        }
    signals = signals or {}
    return SemanticSafetyV5Reporter().build(signals, through_v4=through_v4)

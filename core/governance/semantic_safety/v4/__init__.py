"""
CNexus Semantic Safety v4 — Semantic Firewall (pre-output containment).

Blocks control projection at the interpretation boundary without mutating runtime.
"""

from __future__ import annotations

from typing import Any

from core.governance.semantic_safety.v4.semantic_firewall import (
    FirewallResult,
    SemanticFirewall,
    apply_semantic_firewall,
)
from core.governance.semantic_safety.v4.v4_report import SemanticSafetyV4Report, SemanticSafetyV4Reporter

__all__ = [
    "FirewallResult",
    "SemanticFirewall",
    "SemanticSafetyV4Report",
    "SemanticSafetyV4Reporter",
    "apply_semantic_firewall",
    "build_semantic_safety_v4_report",
]


def build_semantic_safety_v4_report(
    signals: dict[str, dict[str, Any]] | None = None,
    *,
    use_l3_stack: bool = True,
) -> SemanticSafetyV4Report:
    if signals is None and use_l3_stack:
        from core.governance.l3 import build_l3_g1_report, build_l3_g6_report, build_l3_g7_report

        signals = {
            "L3-G1": build_l3_g1_report(use_l2_coupling=False).to_dict(),
            "L3-G6": build_l3_g6_report(use_l2_coupling=False).to_dict(),
            "L3-G7": build_l3_g7_report(use_l2_coupling=False).to_dict(),
        }
    signals = signals or {}
    return SemanticSafetyV4Reporter().build(signals)

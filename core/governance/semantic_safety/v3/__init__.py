"""
CNexus Semantic Safety v3 — Adversarial Perception Attack Simulator.

Simulates misread paths and control illusion chains without modifying system behavior.
"""

from __future__ import annotations

from typing import Any

from core.governance.semantic_safety.v3.attack_scorer import AttackScorer
from core.governance.semantic_safety.v3.attack_types import AttackType
from core.governance.semantic_safety.v3.control_inference_model import ControlInferenceChain, ControlInferenceModel
from core.governance.semantic_safety.v3.leakage_surface_map import LeakageSurfaceMap, LeakageSurfaceMapper
from core.governance.semantic_safety.v3.mitigation_tags import derive_mitigation_tags
from core.governance.semantic_safety.v3.perception_simulator import PerceptionResult, PerceptionSimulator
from core.governance.semantic_safety.v3.v3_report import SemanticSafetyV3Report, SemanticSafetyV3Reporter

__all__ = [
    "AttackScorer",
    "AttackType",
    "ControlInferenceChain",
    "ControlInferenceModel",
    "LeakageSurfaceMap",
    "LeakageSurfaceMapper",
    "PerceptionResult",
    "PerceptionSimulator",
    "SemanticSafetyV3Report",
    "SemanticSafetyV3Reporter",
    "build_semantic_safety_v3_report",
    "derive_mitigation_tags",
]


def build_semantic_safety_v3_report(
    signals: dict[str, dict[str, Any]] | None = None,
    *,
    use_l3_stack: bool = True,
) -> SemanticSafetyV3Report:
    """
    Run v3 attack simulation over observational report payloads.

    Default: L3-G1 / G6 / G7 synthetic stack (no runtime mutation).
    """
    if signals is None and use_l3_stack:
        from core.governance.l3 import build_l3_g1_report, build_l3_g6_report, build_l3_g7_report

        signals = {
            "L3-G1": build_l3_g1_report(use_l2_coupling=False).to_dict(),
            "L3-G6": build_l3_g6_report(use_l2_coupling=False).to_dict(),
            "L3-G7": build_l3_g7_report(use_l2_coupling=False).to_dict(),
        }
    signals = signals or {}
    return SemanticSafetyV3Reporter().build(signals)

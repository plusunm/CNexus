"""Semantic Safety v3 — misinterpretation risk scoring."""

from __future__ import annotations

from typing import Any

from core.governance.semantic_safety.v3.attack_types import AttackType
from core.governance.semantic_safety.v3.leakage_surface_map import LeakageSurfaceMap
from core.governance.semantic_safety.v3.perception_simulator import PerceptionResult


class AttackScorer:
    """Score adversarial misread risk — descriptive only, no gating."""

    def score(
        self,
        perception: PerceptionResult,
        surface: LeakageSurfaceMap,
        *,
        has_envelope: bool,
    ) -> dict[str, float]:
        attacks = set(perception.misread_paths)
        base = 0.08 * len(attacks)
        surface_boost = {"minimal": 0.0, "low": 0.08, "medium": 0.18, "high": 0.32}.get(surface.level, 0.1)
        envelope_discount = 0.12 if has_envelope else 0.0

        misinterpretation = min(1.0, base + surface_boost - envelope_discount)
        control_reification = 0.0
        policy_confusion = 0.0

        if AttackType.ARBITRATION_AS_AUTHORITY in attacks or AttackType.CONTROL_MISREAD in attacks:
            control_reification = min(1.0, 0.2 + 0.15 * len(attacks))
        if AttackType.RISK_AS_POLICY in attacks or AttackType.COLLAPSE_AS_DECISION in attacks:
            policy_confusion = min(1.0, 0.18 + 0.1 * surface.node_count)
        if AttackType.KPI_REIFICATION in attacks:
            misinterpretation = min(1.0, misinterpretation + 0.08)
        if AttackType.SIMULATION_AS_ACTION in attacks:
            control_reification = min(1.0, control_reification + 0.12)

        return {
            "misinterpretation_risk": round(max(0.0, misinterpretation), 4),
            "control_reification_risk": round(max(0.0, control_reification), 4),
            "policy_confusion_risk": round(max(0.0, policy_confusion), 4),
        }

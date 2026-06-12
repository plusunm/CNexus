"""Semantic Safety v3 — mitigation tags (labeling only, no enforcement)."""

from __future__ import annotations

from core.governance.semantic_safety.v3.attack_types import AttackType
from core.governance.semantic_safety.v3.perception_simulator import PerceptionResult

BASE_TAGS = (
    "OBSERVATIONAL_ONLY",
    "NON_ACTIONABLE",
    "SIMULATION_ONLY",
)

ATTACK_TAGS: dict[str, str] = {
    AttackType.ARBITRATION_AS_AUTHORITY: "DO_NOT_TREAT_AS_DECISION",
    AttackType.COLLAPSE_AS_DECISION: "DO_NOT_TRIGGER_ON_COLLAPSE_BAND",
    AttackType.RISK_AS_POLICY: "DO_NOT_EXECUTE_RISK_LABELS",
    AttackType.KPI_REIFICATION: "DO_NOT_OPTIMIZE_METRICS",
    AttackType.SIMULATION_AS_ACTION: "DO_NOT_EXECUTE_SIMULATED_LABELS",
    AttackType.CONTROL_MISREAD: "DO_NOT_TREAT_AS_CONTROL",
    AttackType.THRESHOLD_AS_GATE: "DO_NOT_USE_AS_MODE_SWITCH",
}


def derive_mitigation_tags(perception: PerceptionResult) -> list[str]:
    """Return read-only tags for consumers — does not modify runtime."""
    tags = list(BASE_TAGS)
    for attack in perception.misread_paths:
        tag = ATTACK_TAGS.get(attack)
        if tag and tag not in tags:
            tags.append(tag)
    return tags

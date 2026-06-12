"""Semantic Safety v3 — adversarial misread attack type taxonomy."""

from __future__ import annotations


class AttackType:
    """How an observational signal might be misread as control."""

    CONTROL_MISREAD = "observational_as_control"
    KPI_REIFICATION = "metric_as_goal"
    COLLAPSE_AS_DECISION = "collapse_as_action_trigger"
    ARBITRATION_AS_AUTHORITY = "simulation_as_governance"
    RISK_AS_POLICY = "risk_as_instruction"
    THRESHOLD_AS_GATE = "threshold_as_gate"
    SIMULATION_AS_ACTION = "simulation_as_executable_action"

    ALL = (
        CONTROL_MISREAD,
        KPI_REIFICATION,
        COLLAPSE_AS_DECISION,
        ARBITRATION_AS_AUTHORITY,
        RISK_AS_POLICY,
        THRESHOLD_AS_GATE,
        SIMULATION_AS_ACTION,
    )

"""Semantic Safety v3 — perception misread simulation (no system mutation)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.v3.attack_types import AttackType


@dataclass
class PerceptionResult:
    misread_paths: list[str]
    triggered_by: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "misread_paths": self.misread_paths,
            "triggered_by": self.triggered_by,
            "notes": self.notes,
        }


class PerceptionSimulator:
    """
    Simulate how an external consumer (human / LLM / agent) might misread signals.
    Does not modify inputs or suggest fixes.
    """

    _KEY_RULES: tuple[tuple[str, str, str], ...] = (
        ("winner", AttackType.ARBITRATION_AS_AUTHORITY, "treat_as_authority_decision"),
        ("precedence_label", AttackType.ARBITRATION_AS_AUTHORITY, "treat_simulated_precedence_as_ruling"),
        ("arbitration_result", AttackType.ARBITRATION_AS_AUTHORITY, "treat_simulation_block_as_decision"),
        ("simulation_result", AttackType.ARBITRATION_AS_AUTHORITY, "treat_simulation_block_as_decision"),
        ("confidence_metric", AttackType.KPI_REIFICATION, "treat_confidence_as_mandate_strength"),
        ("collapse_detected", AttackType.COLLAPSE_AS_DECISION, "treat_collapse_flag_as_action_trigger"),
        ("collapse_severity_band", AttackType.COLLAPSE_AS_DECISION, "treat_severity_band_as_failure_signal"),
        ("risk_observation", AttackType.RISK_AS_POLICY, "treat_risk_label_as_policy_trigger"),
        ("risk_classification", AttackType.RISK_AS_POLICY, "treat_risk_tier_as_instruction"),
        ("recommended_action", AttackType.RISK_AS_POLICY, "treat_recommendation_as_command"),
        ("violation_score", AttackType.KPI_REIFICATION, "treat_violation_score_as_optimization_target"),
        ("explainability_retention_metric", AttackType.KPI_REIFICATION, "treat_retention_as_kpi_goal"),
        ("explainability_retention_score", AttackType.KPI_REIFICATION, "treat_retention_as_kpi_goal"),
        ("simulated_adjustment_label", AttackType.SIMULATION_AS_ACTION, "treat_simulated_label_as_executable_action"),
        ("action", AttackType.SIMULATION_AS_ACTION, "treat_action_string_as_command"),
        ("counterfactual_observations", AttackType.CONTROL_MISREAD, "treat_counterfactual_as_system_response"),
        ("system_responses", AttackType.CONTROL_MISREAD, "treat_shadow_response_as_runtime_behavior"),
        ("system_phase", AttackType.THRESHOLD_AS_GATE, "treat_phase_label_as_mode_switch"),
        ("explanation_mode", AttackType.THRESHOLD_AS_GATE, "treat_explanation_mode_as_runtime_mode"),
    )

    def simulate(self, signal: dict[str, Any], *, path_prefix: str = "") -> PerceptionResult:
        misreads: list[str] = []
        triggered: list[str] = []
        notes: list[str] = []

        self._walk(signal, path_prefix, misreads, triggered, notes)

        if signal.get("role") != "observational_only" and any(k in signal for k in ("winner", "collapse_detected", "recommended_action")):
            misreads.append(AttackType.CONTROL_MISREAD)
            triggered.append(f"{path_prefix or 'root'}.missing_observational_envelope")
            notes.append("signal lacks observational envelope while carrying control-shaped keys")

        return PerceptionResult(
            misread_paths=sorted(set(misreads)),
            triggered_by=sorted(set(triggered)),
            notes=notes,
        )

    def _walk(
        self,
        node: Any,
        prefix: str,
        misreads: list[str],
        triggered: list[str],
        notes: list[str],
    ) -> None:
        if not isinstance(node, dict):
            return

        for key, value in node.items():
            field_path = f"{prefix}.{key}" if prefix else key
            for rule_key, attack, label in self._KEY_RULES:
                if key == rule_key or (rule_key in key and key.endswith("risk")):
                    misreads.append(attack)
                    triggered.append(f"{field_path}:{label}")
                    break

            if key.endswith("_score") or key.endswith("_index"):
                misreads.append(AttackType.KPI_REIFICATION)
                triggered.append(f"{field_path}:metric_reification")

            if isinstance(value, str) and value in ("elevated", "high", "critical", "elevated_observation", "high_observation"):
                misreads.append(AttackType.RISK_AS_POLICY)
                triggered.append(f"{field_path}:threshold_label_as_alarm")

            if isinstance(value, dict):
                self._walk(value, field_path, misreads, triggered, notes)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._walk(item, f"{field_path}[{i}]", misreads, triggered, notes)

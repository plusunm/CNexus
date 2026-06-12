"""L3-G2 — execution shadow report synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.l3.execution_shadow.types import ShadowState
from core.governance.semantic_safety.envelope import risk_observation_label, with_observational_safety


@dataclass
class L3G2Report:
    scenario_summaries: list[dict[str, Any]]
    impact_summaries: list[dict[str, Any]]
    shadow_states: list[dict[str, Any]]
    counterfactual_observations: list[str]
    risk_observation: str
    baseline_state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "report": "L3-G2 Constraint Execution Shadow Report",
                "scenario_summaries": self.scenario_summaries,
                "impact_summaries": self.impact_summaries,
                "shadow_states": self.shadow_states,
                "counterfactual_observations": self.counterfactual_observations,
                "risk_observation": self.risk_observation,
                "baseline_state": self.baseline_state,
                "metadata": self.metadata,
                "semantic_note": "counterfactual observations are shadow labels — not executable responses",
            }
        )

    def render_text(self) -> str:
        lines = [
            "=== L3-G2 Constraint Execution Shadow Report ===",
            f"Baseline: {self.baseline_state}",
            f"Risk observation: {self.risk_observation}",
            "",
        ]
        for i, (scenario, impact, observation) in enumerate(
            zip(self.scenario_summaries, self.impact_summaries, self.counterfactual_observations),
            start=1,
        ):
            lines.extend(
                [
                    f"--- Scenario {i}: {scenario.get('constraint')} @ {scenario.get('target_layer')} ---",
                    f"  Strength: {scenario.get('strength')}",
                    f"  Impact: {impact}",
                    f"  Counterfactual observation: {observation}",
                    "",
                ]
            )
        lines.append("(S17–S20: counterfactual shadow only — zero execution / mutation)")
        return "\n".join(lines)


class L3G2Reporter:
    def render(self, shadow_states: list[ShadowState], *, baseline_state: dict[str, Any]) -> L3G2Report:
        if not shadow_states:
            return L3G2Report(
                scenario_summaries=[],
                impact_summaries=[],
                shadow_states=[],
                counterfactual_observations=[],
                risk_observation="low_observation",
                baseline_state=baseline_state,
                metadata=_metadata(),
            )

        scenario_summaries = []
        impact_summaries = []
        observations = []
        max_risk = 0.0

        for state in shadow_states:
            impact = state.projected_impact
            scenario_summaries.append(
                {
                    "constraint": state.scenario.constraint_id,
                    "strength": state.scenario.enforcement_strength,
                    "target_layer": state.scenario.target_layer,
                }
            )
            impact_summaries.append(
                {
                    "stability_delta": impact.stability_delta,
                    "coherence_delta": impact.coherence_delta,
                    "coupling_delta": impact.coupling_delta,
                    "risk_amplification": impact.risk_amplification,
                }
            )
            observations.append(state.system_response)
            max_risk = max(max_risk, impact.risk_amplification)

        return L3G2Report(
            scenario_summaries=scenario_summaries,
            impact_summaries=impact_summaries,
            shadow_states=[s.to_dict() for s in shadow_states],
            counterfactual_observations=observations,
            risk_observation=risk_observation_label(max_risk),
            baseline_state=baseline_state,
            metadata=_metadata(),
        )


def _metadata() -> dict[str, Any]:
    return {
        "l3_layer": "governance_boundary_g2",
        "read_only": True,
        "shadow_only": True,
        "no_counterfactual_execution": True,
        "no_state_mutation": True,
        "simulation_irreversibility_guard": True,
        "principles": ["S17", "S18", "S19", "S20"],
    }

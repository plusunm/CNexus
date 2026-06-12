"""L3-G2 — constraint execution shadow simulator (counterfactual, non-executing)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.execution_shadow.impact_model import ImpactModel
from core.governance.l3.execution_shadow.state_projection import StateProjection
from core.governance.l3.execution_shadow.types import ExecutionScenario, ShadowState


class ConstraintExecutionShadowEngine:
    """Simulate if constraints were enforced — pure shadow (S17)."""

    def __init__(self) -> None:
        self._impact_model = ImpactModel()
        self._projection = StateProjection()

    def simulate(self, scenario: ExecutionScenario, system_state: dict[str, Any]) -> ShadowState:
        impact = self._impact_model.estimate(system_state, scenario)
        layer_projections = self._projection.project_all(impact)

        if impact.risk_amplification > 0.7:
            response = "system instability likely under enforcement"
        elif impact.coherence_delta < -0.3:
            response = "semantic fragmentation under constraint pressure"
        else:
            response = "stable under hypothetical enforcement"

        return ShadowState(
            scenario=scenario,
            projected_impact=impact,
            system_response=response,
            layer_projections=layer_projections,
        )

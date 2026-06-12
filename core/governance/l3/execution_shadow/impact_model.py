"""L3-G2 — system impact estimation under hypothetical constraint enforcement."""

from __future__ import annotations

from typing import Any

from core.governance.l3.execution_shadow.types import ExecutionScenario, ImpactProfile


class ImpactModel:
    """Estimate counterfactual impact — no state mutation (S18/S19)."""

    def estimate(self, system_state: dict[str, Any], scenario: ExecutionScenario) -> ImpactProfile:
        base_stability = float(system_state.get("stability", 0.8))
        base_coherence = float(system_state.get("coherence", 0.75))
        strength = float(scenario.enforcement_strength)

        layer_factor = {"L1": 1.2, "L2": 1.0, "L2.5": 0.85}.get(scenario.target_layer, 1.0)
        effective = min(1.0, strength * layer_factor)

        stability_delta = -0.4 * effective
        coherence_delta = -0.3 * effective
        coupling_delta = 0.2 * effective
        risk_amplification = effective * (1.0 - base_stability)

        if scenario.constraint_id == "runtime_safety":
            risk_amplification = min(1.0, risk_amplification + 0.1 * effective)
        if scenario.constraint_id == "semantic_layer" and base_coherence < 0.5:
            coherence_delta -= 0.1 * effective

        return ImpactProfile(
            stability_delta=round(stability_delta, 4),
            coherence_delta=round(coherence_delta, 4),
            coupling_delta=round(coupling_delta, 4),
            risk_amplification=round(risk_amplification, 4),
        )

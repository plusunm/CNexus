"""
L3-G2 — execution shadow types (counterfactual only).

S17 No Counterfactual Execution | S18 Shadow Impact Only
S19 No State Mutation | S20 Simulation Irreversibility Guard
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionScenario:
    constraint_id: str
    enforcement_strength: float
    target_layer: str  # L1 / L2 / L2.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "enforcement_strength": round(self.enforcement_strength, 4),
            "target_layer": self.target_layer,
        }


@dataclass(frozen=True)
class ImpactProfile:
    stability_delta: float
    coherence_delta: float
    coupling_delta: float
    risk_amplification: float

    def to_dict(self) -> dict[str, float]:
        return {
            "stability_delta": round(self.stability_delta, 4),
            "coherence_delta": round(self.coherence_delta, 4),
            "coupling_delta": round(self.coupling_delta, 4),
            "risk_amplification": round(self.risk_amplification, 4),
        }


@dataclass
class ShadowState:
    scenario: ExecutionScenario
    projected_impact: ImpactProfile
    system_response: str
    layer_projections: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario.to_dict(),
            "projected_impact": self.projected_impact.to_dict(),
            "system_response": self.system_response,
            "layer_projections": self.layer_projections,
        }

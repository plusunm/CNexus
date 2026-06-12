"""L3-G2 — hypothetical L1 / L2 / L2.5 state projection (shadow only)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.execution_shadow.types import ImpactProfile


class StateProjection:
    """Project counterfactual layer states — never writes back (S19)."""

    def project_l1(self, impact: ImpactProfile) -> dict[str, float]:
        return {
            "runtime_stability": round(max(0.0, 1.0 + impact.stability_delta), 4),
            "execution_noise": round(abs(impact.coupling_delta), 4),
        }

    def project_l2(self, impact: ImpactProfile) -> dict[str, float]:
        return {
            "semantic_coherence": round(max(0.0, 1.0 + impact.coherence_delta), 4),
            "interpretation_entropy": round(abs(impact.coherence_delta), 4),
        }

    def project_l2_5(self, impact: ImpactProfile) -> dict[str, float]:
        return {
            "attractor_lock_in_risk": round(min(1.0, impact.risk_amplification), 4),
        }

    def project_all(self, impact: ImpactProfile) -> dict[str, dict[str, float]]:
        return {
            "L1": self.project_l1(impact),
            "L2": self.project_l2(impact),
            "L2.5": self.project_l2_5(impact),
        }

    def apply_to_system_state(
        self,
        system_state: dict[str, Any],
        impact: ImpactProfile,
    ) -> dict[str, Any]:
        """Return new dict only — original system_state untouched (S20)."""
        projected = dict(system_state)
        l1 = self.project_l1(impact)
        l2 = self.project_l2(impact)
        projected["stability"] = l1["runtime_stability"]
        projected["coherence"] = l2["semantic_coherence"]
        projected["lock_in_risk"] = self.project_l2_5(impact)["attractor_lock_in_risk"]
        return projected

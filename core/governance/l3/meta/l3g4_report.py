"""L3-G4 — meta-governance reflection report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.l3.meta.types import MetaGovernanceState, ReflexivityProfile
from core.governance.semantic_safety.envelope import with_observational_safety


@dataclass
class L3G4Report:
    meta_governance_state: str
    reflexivity_score: float
    self_consistency_drift: float
    narrative_folding_index: float
    system_self_model: str
    observed_system_model: str
    drift_signature: dict[str, str]
    reflexivity_profile: dict[str, Any] = field(default_factory=dict)
    risk_signals: dict[str, float] = field(default_factory=dict)
    observer_model: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "report": "L3-G4 Meta-Governance Reflection Report",
                "meta_governance_state": self.meta_governance_state,
                "reflexivity_score": round(self.reflexivity_score, 4),
                "self_consistency_drift": round(self.self_consistency_drift, 4),
                "narrative_folding_index": round(self.narrative_folding_index, 4),
                "system_self_model": self.system_self_model,
                "observed_system_model": self.observed_system_model,
                "drift_signature": self.drift_signature,
                "reflexivity_profile": self.reflexivity_profile,
                "risk_observations": self.risk_signals,
                "risk_signals": self.risk_signals,
                "observer_model": self.observer_model,
                "metadata": self.metadata,
                "semantic_note": "risk_observations are descriptive metrics — not control triggers",
            },
            simulation_only=False,
        )

    def render_text(self) -> str:
        lines = [
            "=== L3-G4 Meta-Governance Reflection Report ===",
            f"State: {self.meta_governance_state}",
            f"Reflexivity score: {self.reflexivity_score:.2f}",
            f"Self-consistency drift: {self.self_consistency_drift:.2f}",
            f"Narrative folding index: {self.narrative_folding_index:.2f}",
            "",
            "--- Self Model ---",
            self.system_self_model[:200] + ("..." if len(self.system_self_model) > 200 else ""),
            "",
            "--- Observed Model ---",
            self.observed_system_model[:200] + ("..." if len(self.observed_system_model) > 200 else ""),
            "",
            f"Drift signature: {self.drift_signature}",
            f"Risk signals: {self.risk_signals}",
            "",
            "(G4: observational reflexivity only — no self-modification / no meta-governance execution)",
        ]
        return "\n".join(lines)


class L3G4Reporter:
    def render(
        self,
        meta_state: MetaGovernanceState,
        reflexivity: ReflexivityProfile,
        observer_model: dict[str, Any],
    ) -> L3G4Report:
        return L3G4Report(
            meta_governance_state=meta_state.phase,
            reflexivity_score=reflexivity.reflexivity_score,
            self_consistency_drift=reflexivity.self_consistency_drift,
            narrative_folding_index=reflexivity.narrative_folding_index,
            system_self_model=meta_state.self_model_summary,
            observed_system_model=meta_state.observed_model_summary,
            drift_signature=reflexivity.drift_signature.to_dict(),
            reflexivity_profile=reflexivity.to_dict(),
            risk_signals=meta_state.risk_signals,
            observer_model=observer_model,
            metadata={
                "l3_layer": "governance_boundary_g4",
                "read_only": True,
                "no_self_modification": True,
                "no_meta_governance_execution": True,
                "observational_reflexivity_only": True,
                "non_closure_enforcement": True,
            },
        )

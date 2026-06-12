"""
L3-G4 — meta-governance reflection types (observational reflexivity only).

No self-modification · no meta-governance execution · non-closure enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DriftSignature:
    type: str
    severity: str  # low | medium | high

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "severity": self.severity}


@dataclass(frozen=True)
class ReflexivityProfile:
    reflexivity_depth: float
    self_consistency_drift: float
    narrative_folding_index: float
    reflexivity_score: float
    drift_signature: DriftSignature

    def to_dict(self) -> dict[str, Any]:
        return {
            "reflexivity_depth": round(self.reflexivity_depth, 4),
            "self_consistency_drift": round(self.self_consistency_drift, 4),
            "narrative_folding_index": round(self.narrative_folding_index, 4),
            "reflexivity_score": round(self.reflexivity_score, 4),
            "drift_signature": self.drift_signature.to_dict(),
        }


@dataclass
class MetaGovernanceState:
    phase: str  # stable | drifting | self_sealing | expanding
    self_model_summary: str
    observed_model_summary: str
    model_gap: float
    risk_signals: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta_governance_state": self.phase,
            "system_self_model": self.self_model_summary,
            "observed_system_model": self.observed_model_summary,
            "model_gap": round(self.model_gap, 4),
            "risk_signals": {k: round(v, 4) for k, v in self.risk_signals.items()},
        }

"""
L3-G5 — meta-meta governance boundary types (level-of-levels observational only).

No execution · no layer mutation · meta_layer_definition_only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.envelope import with_observational_safety


@dataclass(frozen=True)
class LayerDefinition:
    name: str
    purpose: str
    allowed_operations: list[str]
    forbidden_operations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "allowed_operations": self.allowed_operations,
            "forbidden_operations": self.forbidden_operations,
        }


@dataclass(frozen=True)
class BoundaryDefinition:
    upper_layer: str
    lower_layer: str
    boundary_type: str  # rigid / soft / reflective / recursive

    def to_dict(self) -> dict[str, str]:
        return {
            "upper_layer": self.upper_layer,
            "lower_layer": self.lower_layer,
            "boundary_type": self.boundary_type,
        }


@dataclass(frozen=True)
class OntologyDrift:
    layer_name: str
    drift_score: float
    semantic_shift: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "layer_name": self.layer_name,
            "drift_score": round(self.drift_score, 4),
            "semantic_shift": round(self.semantic_shift, 4),
        }


@dataclass
class L3G5ReportPayload:
    layer_system_stability: float
    boundary_consistency: float
    ontology_drift_index: float
    self_referential_depth: float
    meta_governance_state: str
    layer_definitions: list[dict[str, Any]] = field(default_factory=list)
    boundaries: list[dict[str, str]] = field(default_factory=list)
    ontology_drifts: list[dict[str, Any]] = field(default_factory=list)
    layer_genesis_rules: dict[str, str] = field(default_factory=dict)
    integrity_violations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "report": "L3-G5 Meta-Meta Governance Boundary Report",
                "layer_system_stability": round(self.layer_system_stability, 4),
                "boundary_consistency": round(self.boundary_consistency, 4),
                "ontology_drift_index": round(self.ontology_drift_index, 4),
                "self_referential_depth": round(self.self_referential_depth, 4),
                "meta_governance_state": self.meta_governance_state,
                "layer_definitions": self.layer_definitions,
                "boundaries": self.boundaries,
                "ontology_drifts": self.ontology_drifts,
                "layer_genesis_rules": self.layer_genesis_rules,
                "integrity_violations": self.integrity_violations,
                "metadata": self.metadata,
            },
            simulation_only=False,
        )

"""
L3-G7 — layerless kernel types.

Field · Attractor · Trace only — no layer_id, no hierarchy.
Observational only · no governance hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from core.governance.semantic_safety.envelope import with_observational_safety


G7_META_CONSTRAINTS: dict[str, bool] = {
    "no_layer_model": True,
    "field_only_ontology": True,
    "no_governance_hierarchy": True,
    "observational_only": True,
}


@dataclass
class FieldState:
    intensity: float
    entropy: float
    coherence: float

    def to_dict(self) -> dict[str, float]:
        return {
            "intensity": round(self.intensity, 4),
            "entropy": round(self.entropy, 4),
            "coherence": round(self.coherence, 4),
        }


@dataclass
class AttractorNode:
    attractor_id: str
    strength: float
    basin: str

    def to_dict(self) -> dict[str, str | float]:
        return {
            "attractor_id": self.attractor_id,
            "strength": round(self.strength, 4),
            "basin": self.basin,
        }


@dataclass
class TraceEvent:
    timestamp: float
    signal_type: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "signal_type": self.signal_type,
            "payload": self.payload,
        }


@dataclass
class LayerlessKernelState:
    field: FieldState
    attractors: list[AttractorNode]
    traces: list[TraceEvent]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field.to_dict(),
            "attractors": [a.to_dict() for a in self.attractors],
            "traces": [t.to_dict() for t in self.traces],
            "metadata": self.metadata,
        }


@dataclass
class L3G7Report:
    model: str
    field: dict[str, float]
    attractors: int
    traces: int
    interpretation_mode: str
    interpretation: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "report": self.model,
                "field": self.field,
                "attractors": self.attractors,
                "traces": self.traces,
                "interpretation_mode": self.interpretation_mode,
                "interpretation": self.interpretation,
                "metadata": self.metadata,
            },
            simulation_only=False,
        )

    def render_text(self) -> str:
        interp = self.interpretation
        regime = interp.get("regime", "unknown")
        lines = [
            "=== L3-G7 Layerless Kernel Report ===",
            f"Regime: {regime}",
            f"Field intensity: {self.field.get('intensity', 0):.2f}",
            f"Field entropy: {self.field.get('entropy', 0):.2f}",
            f"Field coherence: {self.field.get('coherence', 0):.2f}",
            f"Attractors: {self.attractors}",
            f"Trace density: {interp.get('trace_density', self.traces)}",
            f"Interpretation mode: {self.interpretation_mode}",
            "",
            "(G7: field-native cognition — layers are observational projection only)",
        ]
        return "\n".join(lines)

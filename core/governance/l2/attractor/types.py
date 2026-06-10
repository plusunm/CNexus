"""
GTBS-L2.5 — latent attractor inference types (structural inference, read-only).

S11 No Control Leakage | S12 Attractor ≠ Decision
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LatentAttractorState:
    attractor_id: str
    strength: float
    basin_depth: float
    openness_radius: float
    shadow_pull: float
    ecology_pull: float
    singularity_pull: float
    stability_class: str
    narrative_hint: str
    attractor_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.attractor_id,
            "type": self.attractor_type,
            "strength": round(self.strength, 4),
            "basin_depth": round(self.basin_depth, 4),
            "openness_radius": round(self.openness_radius, 4),
            "shadow_pull": round(self.shadow_pull, 4),
            "ecology_pull": round(self.ecology_pull, 4),
            "singularity_pull": round(self.singularity_pull, 4),
            "stability_class": self.stability_class,
            "narrative_hint": self.narrative_hint,
        }


@dataclass(frozen=True)
class AttractorField:
    attractors: tuple[LatentAttractorState, ...]
    global_entropy: float
    coupling_density: float
    field_regime: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "attractors": [a.to_dict() for a in self.attractors],
            "global_entropy": round(self.global_entropy, 4),
            "coupling_density": round(self.coupling_density, 4),
            "field_regime": self.field_regime,
        }


@dataclass(frozen=True)
class TopologySignature:
    cluster_count: int
    dominant_attractor: str
    entropy_gradient: float
    lock_in_probability: float

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "cluster_count": self.cluster_count,
            "dominant_attractor": self.dominant_attractor,
            "entropy_gradient": round(self.entropy_gradient, 4),
            "lock_in_probability": round(self.lock_in_probability, 4),
        }


@dataclass
class GTBSL2AttractorReport:
    narrative_version: str = "L2_v0.5"
    time_range: str = ""
    field_regime: str = "diffuse"
    global_entropy: float = 0.0
    coupling_density: float = 0.0
    dominant_attractors: list[dict[str, Any]] = field(default_factory=list)
    topology: dict[str, Any] = field(default_factory=dict)
    risk_surface: dict[str, float] = field(default_factory=dict)
    interpretation: str = ""
    attractor_field: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report": "GTBS-L2.5 Latent Attractor Inference Report",
            "narrative_version": self.narrative_version,
            "time_range": self.time_range,
            "field_regime": self.field_regime,
            "global_entropy": round(self.global_entropy, 4),
            "coupling_density": round(self.coupling_density, 4),
            "dominant_attractors": self.dominant_attractors,
            "topology": self.topology,
            "risk_surface": self.risk_surface,
            "interpretation": self.interpretation,
            "attractor_field": self.attractor_field,
            "metadata": self.metadata,
        }

"""
L3-G3 — power field optimization types (structural inference only).

No execution · no action recommendation · no runtime writeback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PowerNode:
    id: str
    strength: float
    elasticity: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "id": self.id,
            "strength": round(self.strength, 4),
            "elasticity": round(self.elasticity, 4),
        }


@dataclass
class PowerEdge:
    from_node: str
    to_node: str
    tension: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "from": self.from_node,
            "to": self.to_node,
            "tension": round(self.tension, 4),
        }


@dataclass
class PowerField:
    nodes: dict[str, PowerNode]
    edges: list[PowerEdge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }


@dataclass
class StabilityLandscape:
    entropy: float
    lock_in_regions: float
    diffusion_regions: float
    bifurcation_points: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "entropy": round(self.entropy, 4),
            "lock_in_regions": round(self.lock_in_regions, 4),
            "diffusion_regions": round(self.diffusion_regions, 4),
            "bifurcation_points": self.bifurcation_points,
        }


@dataclass
class OptimizationResult:
    simulated_optimization: list[dict[str, Any]]
    note: str
    expected_entropy_delta_total: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulated_optimization": self.simulated_optimization,
            "note": self.note,
            "expected_entropy_delta_total": round(self.expected_entropy_delta_total, 4),
        }

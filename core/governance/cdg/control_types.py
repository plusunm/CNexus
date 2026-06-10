"""CDG control-plane shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EnergyGradient:
    coupling: float
    drift: float
    oscillation: float
    magnitude: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "coupling": round(self.coupling, 4),
            "drift": round(self.drift, 4),
            "oscillation": round(self.oscillation, 4),
            "magnitude": round(self.magnitude, 4),
        }


@dataclass
class ControlSignal:
    """Sole control law output (L6.5)."""

    mode: str
    step_size: float
    weakened: bool
    requested_phase: str
    expected_d_v: float
    trajectory_stable: bool
    gradient: EnergyGradient

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "step_size": round(self.step_size, 4),
            "weakened": self.weakened,
            "requested_phase": self.requested_phase,
            "expected_d_v": round(self.expected_d_v, 4),
            "trajectory_stable": self.trajectory_stable,
            "gradient": self.gradient.to_dict(),
        }


@dataclass
class ControlStepResult:
    state: Dict[str, Any]
    step_size: float
    mode: str
    weakened: bool
    gradient: EnergyGradient
    expected_d_v: float
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_size": round(self.step_size, 4),
            "mode": self.mode,
            "weakened": self.weakened,
            "gradient": self.gradient.to_dict(),
            "expected_d_v": round(self.expected_d_v, 4),
            "flags": list(self.flags),
        }

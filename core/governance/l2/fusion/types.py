"""
GTBS-L2 v0.3 — fusion types (read-only field cognition).

S8 No Cross-Stream Governance | S9 Coupling ≠ Causation | S10 Observational Closure Only
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrossStreamCouplingMatrix:
    shadow_x_ecology: float = 0.0
    shadow_x_singularity: float = 0.0
    ecology_x_singularity: float = 0.0
    global_coupling_index: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "shadow_x_ecology": round(self.shadow_x_ecology, 4),
            "shadow_x_singularity": round(self.shadow_x_singularity, 4),
            "ecology_x_singularity": round(self.ecology_x_singularity, 4),
            "global_coupling_index": round(self.global_coupling_index, 4),
        }


@dataclass
class CrossStreamField:
    """Aligned multi-stream daily series within a temporal window."""

    start_ts: str
    end_ts: str
    window_days: int
    days: list[str] = field(default_factory=list)
    shadow: dict[str, list[float]] = field(default_factory=dict)
    ecology: dict[str, list[float]] = field(default_factory=dict)
    singularity: dict[str, list[float]] = field(default_factory=dict)
    continuity: dict[str, list[float]] = field(default_factory=dict)
    coupling_signals: dict[str, float] = field(default_factory=dict)
    coupling_matrix: CrossStreamCouplingMatrix = field(default_factory=CrossStreamCouplingMatrix)


@dataclass
class GTBSL2FusionReport:
    narrative_version: str = "L2_v0.3"
    time_range: str = ""
    fusion_summaries: dict[str, str] = field(default_factory=dict)
    coupling_matrix: dict[str, float] = field(default_factory=dict)
    coupling_signals: dict[str, float] = field(default_factory=dict)
    risk_surface: dict[str, str] = field(default_factory=dict)
    raw_field: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report": "GTBS-L2 v0.3 Cross-Stream Fusion Report",
            "narrative_version": self.narrative_version,
            "time_range": self.time_range,
            "fusion_summaries": self.fusion_summaries,
            "coupling_matrix": self.coupling_matrix,
            "coupling_signals": self.coupling_signals,
            "risk_surface": self.risk_surface,
            "raw_field": self.raw_field,
            "metadata": self.metadata,
        }

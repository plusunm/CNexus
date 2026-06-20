"""L4-1 — conscious flow data structures (Σ.T sandbox only)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class SimulationBudget:
    """Hard caps — every simulation round must be terminable."""

    max_branches: int = 3
    max_wall_ms: int = 2000
    max_parallel_workers: int = 2

    def clamp_branch_count(self, requested: int) -> int:
        return max(0, min(int(requested), max(1, self.max_branches)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_branches": self.max_branches,
            "max_wall_ms": self.max_wall_ms,
            "max_parallel_workers": self.max_parallel_workers,
        }


@dataclass
class ThoughtBranch:
    """Single hypothetical interaction path in the cognitive sandbox."""

    branch_id: str
    assumption_seed: str
    projected_state: Dict[str, Any] = field(default_factory=dict)
    coherence_impact: float = 0.0
    response_text: str = ""
    expected_stability_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "assumption_seed": self.assumption_seed,
            "projected_state": dict(self.projected_state),
            "coherence_impact": self.coherence_impact,
            "response_text": self.response_text,
            "expected_stability_score": self.expected_stability_score,
        }


@dataclass
class CandidateResponse:
    """Evaluated branch output surfaced to downstream L4-2/L4-3."""

    branch_id: str
    response_text: str
    expected_stability_score: float
    assumption_seed: str
    coherence_impact: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "response_text": self.response_text,
            "expected_stability_score": self.expected_stability_score,
            "assumption_seed": self.assumption_seed,
            "coherence_impact": self.coherence_impact,
        }


@dataclass
class SimulatedTraj:
    """Full parallel simulation round — persisted only in Σ.T."""

    trace_id: str
    branches: List[ThoughtBranch] = field(default_factory=list)
    baseline_coherence: float = 0.85
    query_preview: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def candidates(self) -> List[CandidateResponse]:
        return [
            CandidateResponse(
                branch_id=b.branch_id,
                response_text=b.response_text,
                expected_stability_score=b.expected_stability_score,
                assumption_seed=b.assumption_seed,
                coherence_impact=b.coherence_impact,
            )
            for b in self.branches
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "baseline_coherence": self.baseline_coherence,
            "query_preview": self.query_preview,
            "created_at": self.created_at,
            "branches": [b.to_dict() for b in self.branches],
        }

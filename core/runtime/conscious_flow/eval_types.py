"""L4-2 evaluation result types — Σ.T sandbox only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime.conscious_flow.types import CandidateResponse


@dataclass
class PrunedBranch:
    branch_id: str
    prune_reason: str
    expected_stability_score: float
    assumption_seed: str = ""
    response_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "prune_reason": self.prune_reason,
            "expected_stability_score": self.expected_stability_score,
            "assumption_seed": self.assumption_seed,
            "response_preview": self.response_preview,
        }


@dataclass
class EvaluatedCandidate:
    """Candidate that survived filtering."""

    candidate: CandidateResponse
    eval_path: str
    final_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.candidate.to_dict(),
            "eval_path": self.eval_path,
            "final_score": self.final_score,
        }


@dataclass
class EvaluationReport:
    trace_id: str
    kept: List[EvaluatedCandidate] = field(default_factory=list)
    pruned: List[PrunedBranch] = field(default_factory=list)
    fast_track_count: int = 0
    reflective_count: int = 0
    reflective_llm_calls: int = 0

    @property
    def candidates(self) -> List[CandidateResponse]:
        return [e.candidate for e in self.kept]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "kept": [k.to_dict() for k in self.kept],
            "pruned": [p.to_dict() for p in self.pruned],
            "fast_track_count": self.fast_track_count,
            "reflective_count": self.reflective_count,
            "reflective_llm_calls": self.reflective_llm_calls,
        }

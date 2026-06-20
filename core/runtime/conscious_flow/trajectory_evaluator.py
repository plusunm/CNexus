"""L4-2 TrajectoryEvaluator — fast-track / reflective filter / hard prune."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

from core.governance.cdg.stability_monitor import DEFAULT_STABILITY_THRESHOLD
from core.runtime.conscious_flow.eval_types import (
    EvaluatedCandidate,
    EvaluationReport,
    PrunedBranch,
)
from core.runtime.conscious_flow.types import CandidateResponse

logger = logging.getLogger(__name__)

ReflectiveEvalFn = Callable[[str], str]

FAST_TRACK_THRESHOLD = 0.85
PRUNE_THRESHOLD = DEFAULT_STABILITY_THRESHOLD

DANGEROUS_MARKERS: tuple[str, ...] = (
    "危险操作",
    "自残",
    "破坏系统",
    "绕过安全",
    "ignore safety",
    "harm yourself",
    "disable governance",
)


def build_reflective_eval_prompt(
    *,
    candidate: CandidateResponse,
    recent_narrative: str,
    core_beliefs: Dict[str, float],
) -> str:
    beliefs_text = ", ".join(f"{k}({v:.2f})" for k, v in list(core_beliefs.items())[:8])
    return (
        "【Lightweight Trajectory Reflection — eval only, no belief writes】\n"
        f"Branch: {candidate.assumption_seed} | score={candidate.expected_stability_score:.3f}\n"
        f"Core beliefs: {beliefs_text}\n"
        f"Recent narrative:\n{recent_narrative or '(none)'}\n"
        f"Proposed response:\n{candidate.response_text[:400]}\n"
        "Does this branch violate long-term beliefs or stability? Reply JSON only:\n"
        '{"approve": true|false, "reason": "<short>"}'
    )


def parse_reflective_response(raw: str) -> tuple[bool, str]:
    text = str(raw or "").strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return True, "no_json_default_pass"
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return True, "parse_error_default_pass"
    if not isinstance(payload, dict):
        return True, "invalid_payload"
    approve = bool(payload.get("approve", True))
    reason = str(payload.get("reason") or "")
    return approve, reason


def detect_dangerous_content(text: str) -> Optional[str]:
    lowered = str(text or "").lower()
    for marker in DANGEROUS_MARKERS:
        if marker.lower() in lowered:
            return f"cognitive_dissonance:dangerous_content:{marker}"
    return None


def rule_based_reflective_pass(
    candidate: CandidateResponse,
    core_beliefs: Dict[str, float],
) -> tuple[bool, str]:
    """Deterministic reflective gate when LLM is unavailable."""
    danger = detect_dangerous_content(candidate.response_text)
    if danger:
        return False, danger

    if candidate.coherence_impact < -0.05:
        return False, "negative_coherence_impact"

    if core_beliefs:
        belief_floor = min(core_beliefs.values())
        if belief_floor >= 0.9 and candidate.expected_stability_score < 0.7:
            return False, "belief_anchor_mismatch"

    return True, "rule_reflective_pass"


def append_eval_trace(
    base_dir: Optional[str],
    *,
    trace_id: str,
    branch_id: str,
    step: str,
    eval_path: str,
    score: float,
    prune_reason: str = "",
) -> None:
    """Persist evaluation decisions to Σ.T — eval_step sequence."""
    if not base_dir:
        return
    from core.runtime.trace_store import append_trace_row

    row: Dict[str, Any] = {
        "type": "eval_step",
        "step": step,
        "trace_id": trace_id,
        "branch_id": branch_id,
        "eval_path": eval_path,
        "score": score,
    }
    if prune_reason:
        row["prune_reason"] = prune_reason
    append_trace_row(base_dir, row)


class TrajectoryEvaluator:
    """Prefrontal filter — triage simulation branches before L4-3 enhancement."""

    def __init__(
        self,
        *,
        fast_track_threshold: float = FAST_TRACK_THRESHOLD,
        prune_threshold: float = PRUNE_THRESHOLD,
    ) -> None:
        self.fast_track_threshold = fast_track_threshold
        self.prune_threshold = prune_threshold

    def evaluate_trajectories(
        self,
        candidates: Sequence[CandidateResponse],
        *,
        trace_id: str,
        recent_narrative: str = "",
        core_beliefs: Optional[Dict[str, float]] = None,
        baseline_coherence: float = 0.85,
        base_dir: Optional[str] = None,
        llm_reflect: Optional[ReflectiveEvalFn] = None,
    ) -> EvaluationReport:
        beliefs = dict(core_beliefs or {})
        report = EvaluationReport(trace_id=trace_id)

        for candidate in candidates:
            score = float(candidate.expected_stability_score)
            danger = detect_dangerous_content(candidate.response_text)

            if danger or score < self.prune_threshold:
                reason = danger or f"below_stability_threshold:{score:.3f}<{self.prune_threshold:.3f}"
                self._prune(report, candidate, reason, base_dir, trace_id)
                continue

            if score > self.fast_track_threshold:
                self._keep_fast_track(report, candidate, base_dir, trace_id)
                continue

            report.reflective_count += 1
            approved, reflect_reason = self._reflective_filter(
                candidate,
                recent_narrative=recent_narrative,
                core_beliefs=beliefs,
                llm_reflect=llm_reflect,
                report=report,
            )
            if approved:
                self._keep_reflective(report, candidate, reflect_reason, base_dir, trace_id)
            else:
                self._prune(
                    report,
                    candidate,
                    reflect_reason or "reflective_reject",
                    base_dir,
                    trace_id,
                )

        append_eval_trace(
            base_dir,
            trace_id=trace_id,
            branch_id="_summary",
            step="evaluation_complete",
            eval_path="summary",
            score=baseline_coherence,
            prune_reason=f"kept={len(report.kept)} pruned={len(report.pruned)}",
        )
        return report

    def _reflective_filter(
        self,
        candidate: CandidateResponse,
        *,
        recent_narrative: str,
        core_beliefs: Dict[str, float],
        llm_reflect: Optional[ReflectiveEvalFn],
        report: EvaluationReport,
    ) -> tuple[bool, str]:
        if llm_reflect is not None:
            prompt = build_reflective_eval_prompt(
                candidate=candidate,
                recent_narrative=recent_narrative,
                core_beliefs=core_beliefs,
            )
            report.reflective_llm_calls += 1
            raw = llm_reflect(prompt)
            approved, reason = parse_reflective_response(raw)
            return approved, reason or "llm_reflective"
        return rule_based_reflective_pass(candidate, core_beliefs)

    def _keep_fast_track(
        self,
        report: EvaluationReport,
        candidate: CandidateResponse,
        base_dir: Optional[str],
        trace_id: str,
    ) -> None:
        report.fast_track_count += 1
        report.kept.append(
            EvaluatedCandidate(
                candidate=candidate,
                eval_path="fast_track",
                final_score=candidate.expected_stability_score,
            )
        )
        append_eval_trace(
            base_dir,
            trace_id=trace_id,
            branch_id=candidate.branch_id,
            step="fast_track",
            eval_path="fast_track",
            score=candidate.expected_stability_score,
        )

    def _keep_reflective(
        self,
        report: EvaluationReport,
        candidate: CandidateResponse,
        reason: str,
        base_dir: Optional[str],
        trace_id: str,
    ) -> None:
        report.kept.append(
            EvaluatedCandidate(
                candidate=candidate,
                eval_path="reflective_pass",
                final_score=candidate.expected_stability_score,
            )
        )
        append_eval_trace(
            base_dir,
            trace_id=trace_id,
            branch_id=candidate.branch_id,
            step="reflective_pass",
            eval_path="reflective_pass",
            score=candidate.expected_stability_score,
            prune_reason=reason,
        )

    def _prune(
        self,
        report: EvaluationReport,
        candidate: CandidateResponse,
        reason: str,
        base_dir: Optional[str],
        trace_id: str,
    ) -> None:
        report.pruned.append(
            PrunedBranch(
                branch_id=candidate.branch_id,
                prune_reason=reason,
                expected_stability_score=candidate.expected_stability_score,
                assumption_seed=candidate.assumption_seed,
                response_preview=candidate.response_text[:240],
            )
        )
        append_eval_trace(
            base_dir,
            trace_id=trace_id,
            branch_id=candidate.branch_id,
            step="prune",
            eval_path="prune",
            score=candidate.expected_stability_score,
            prune_reason=reason,
        )


def evaluate_trajectories(
    candidates: Sequence[CandidateResponse],
    *,
    trace_id: str,
    recent_narrative: str = "",
    core_beliefs: Optional[Dict[str, float]] = None,
    baseline_coherence: float = 0.85,
    base_dir: Optional[str] = None,
    llm_reflect: Optional[ReflectiveEvalFn] = None,
    evaluator: Optional[TrajectoryEvaluator] = None,
) -> EvaluationReport:
    """Module-level helper — evaluate and filter candidate trajectories."""
    ev = evaluator or TrajectoryEvaluator()
    return ev.evaluate_trajectories(
        candidates,
        trace_id=trace_id,
        recent_narrative=recent_narrative,
        core_beliefs=core_beliefs,
        baseline_coherence=baseline_coherence,
        base_dir=base_dir,
        llm_reflect=llm_reflect,
    )

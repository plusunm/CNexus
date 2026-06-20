"""L4-3 — Reasoning trace built from filtered simulation (Σ.T source of truth)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.runtime.conscious_flow.eval_types import EvaluationReport, EvaluatedCandidate


@dataclass
class ReasoningTrace:
    """Explicit conscious-flow summary — assumption_seed must match selected branch."""

    assumption_seed: str
    trace_id: str
    eval_path: str
    final_score: float
    summary: str
    branch_id: str = ""
    query_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assumption_seed": self.assumption_seed,
            "trace_id": self.trace_id,
            "eval_path": self.eval_path,
            "final_score": self.final_score,
            "summary": self.summary,
            "branch_id": self.branch_id,
            "query_preview": self.query_preview,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReasoningTrace":
        return cls(
            assumption_seed=str(data.get("assumption_seed") or ""),
            trace_id=str(data.get("trace_id") or ""),
            eval_path=str(data.get("eval_path") or ""),
            final_score=float(data.get("final_score") or 0.0),
            summary=str(data.get("summary") or ""),
            branch_id=str(data.get("branch_id") or ""),
            query_preview=str(data.get("query_preview") or ""),
        )


def reasoning_trace_enabled(*, production_default: bool = False) -> bool:
    """Dev/debug on by default; production requires explicit opt-in."""
    raw = os.environ.get("CNEXUS_REASONING_TRACE", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    if os.environ.get("CNEXUS_ENV") == "production":
        return production_default
    return True


def reasoning_trace_verbose() -> bool:
    """Full trace block in prompt / payload (vs compact summary only)."""
    raw = os.environ.get("CNEXUS_REASONING_TRACE_VERBOSE", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return reasoning_trace_enabled()


def build_reasoning_trace_from_report(
    report: EvaluationReport,
    *,
    query_preview: str = "",
) -> Optional[ReasoningTrace]:
    """Pick top kept branch — assumption_seed strictly from SimulatedTraj selection."""
    if not report.kept:
        return None
    best: EvaluatedCandidate = max(report.kept, key=lambda item: item.final_score)
    candidate = best.candidate
    seed = candidate.assumption_seed
    summary = _summarize_branch(seed, candidate.response_text, best.eval_path)
    return ReasoningTrace(
        assumption_seed=seed,
        trace_id=report.trace_id,
        eval_path=best.eval_path,
        final_score=best.final_score,
        summary=summary,
        branch_id=candidate.branch_id,
        query_preview=query_preview[:200],
    )


def _summarize_branch(assumption_seed: str, response_text: str, eval_path: str) -> str:
    seed_labels = {
        "helpful_direct": "直接、清晰地回应",
        "cautious_contextual": "结合近期上下文谨慎回应",
        "reflective_deep": "深度反思后回应",
    }
    mode = seed_labels.get(assumption_seed, f"假设路径「{assumption_seed}」")
    preview = response_text[:120].strip()
    return f"我思考了一下：采用{mode}（{eval_path}）。倾向：{preview}"


def format_reasoning_prompt_block(trace: ReasoningTrace, *, verbose: Optional[bool] = None) -> str:
    """Inject into RecallPipeline — after recent_narrative, before long-term identity."""
    show_verbose = reasoning_trace_verbose() if verbose is None else verbose
    header = (
        "【Reasoning Trace — conscious flow (Σ.T sandbox)】\n"
        f"assumption_seed={trace.assumption_seed} | eval={trace.eval_path} | "
        f"score={trace.final_score:.3f}\n"
    )
    if show_verbose:
        return (
            f"{header}"
            f"{trace.summary}\n"
            f"(trace_id={trace.trace_id}, branch={trace.branch_id})"
        )
    return f"{header}{trace.summary}"


def resolve_reasoning_trace_for_query(
    runtime: Any,
    query: str,
    *,
    run_if_missing: bool = True,
) -> Optional[ReasoningTrace]:
    """Use cached trace from background L4 run, or run a minimal filtered simulation."""
    cached = getattr(runtime, "_last_reasoning_trace", None)
    if isinstance(cached, ReasoningTrace):
        if not query or not cached.query_preview or query[:80] in cached.query_preview:
            return cached
    elif isinstance(cached, dict) and cached.get("assumption_seed"):
        trace = ReasoningTrace.from_dict(cached)
        if not query or query[:80] in (trace.query_preview or query):
            return trace

    if not run_if_missing or not (query or "").strip():
        return None

    base_dir = str(getattr(runtime, "base_dir", "") or "")
    store = getattr(runtime, "self_model_store", None)
    model = getattr(store, "model", None) if store is not None else None
    beliefs = dict(getattr(model, "core_beliefs", None) or {})
    coherence = float(getattr(model, "coherence_score", 0.85) or 0.85)

    from core.personality.narrative.recent_context import load_recent_narrative_prompt_block
    from core.runtime.conscious_flow.simulation_engine import SimulationEngine
    from core.runtime.conscious_flow.types import SimulationBudget

    recent = load_recent_narrative_prompt_block(base_dir)
    report = SimulationEngine(
        budget=SimulationBudget(max_branches=2, max_wall_ms=1200, max_parallel_workers=2),
    ).run_filtered_simulation(
        user_query=query,
        recent_narrative=recent,
        core_beliefs=beliefs,
        baseline_coherence=coherence,
        base_dir=base_dir,
    )
    trace = build_reasoning_trace_from_report(report, query_preview=query)
    if trace is not None:
        setattr(runtime, "_last_reasoning_trace", trace)
    return trace

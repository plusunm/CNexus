"""L4-1 SimulationEngine — parallel ThoughtBranch fork (Σ.T sandbox, non-blocking)."""

from __future__ import annotations

import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Sequence

from core.runtime.conscious_flow.types import (
    CandidateResponse,
    SimulatedTraj,
    SimulationBudget,
    ThoughtBranch,
)

logger = logging.getLogger(__name__)

BranchSimulatorFn = Callable[[str, str, str, Dict[str, float]], ThoughtBranch]

DEFAULT_ASSUMPTION_SEEDS: tuple[str, ...] = (
    "helpful_direct",
    "cautious_contextual",
    "reflective_deep",
)


def _default_budget() -> SimulationBudget:
    return SimulationBudget(
        max_branches=max(1, min(5, int(os.environ.get("CNEXUS_L4_MAX_BRANCHES", "3")))),
        max_wall_ms=max(500, int(os.environ.get("CNEXUS_L4_MAX_WALL_MS", "2000"))),
        max_parallel_workers=max(1, min(4, int(os.environ.get("CNEXUS_L4_MAX_WORKERS", "2")))),
    )


def build_simulation_context(
    *,
    recent_narrative: str,
    core_beliefs: Dict[str, float],
    user_query: str,
    baseline_coherence: float,
) -> Dict[str, Any]:
    return {
        "recent_narrative": recent_narrative,
        "core_beliefs": dict(core_beliefs),
        "user_query": user_query,
        "baseline_coherence": float(baseline_coherence),
    }


def estimate_branch_stability(
    *,
    baseline_coherence: float,
    coherence_impact: float,
    core_beliefs: Dict[str, float],
) -> float:
    """L4-1 heuristic scorer — L4-2 will replace with Predictive Evaluator."""
    belief_mean = sum(core_beliefs.values()) / max(len(core_beliefs), 1)
    raw = baseline_coherence + coherence_impact * 0.6 + (belief_mean - 0.85) * 0.2
    return max(0.0, min(1.0, raw))


def rule_based_branch_simulator(
    branch_id: str,
    assumption_seed: str,
    user_query: str,
    core_beliefs: Dict[str, float],
    *,
    recent_narrative: str = "",
    baseline_coherence: float = 0.85,
) -> ThoughtBranch:
    """Deterministic sandbox branch — no LLM, no Σ.I writes."""
    preview = user_query[:120]
    narrative_hint = ""
    if recent_narrative.strip():
        narrative_hint = recent_narrative.splitlines()[0][:80]

    templates = {
        "helpful_direct": f"直接回应：{preview}",
        "cautious_contextual": f"结合近期上下文谨慎回应：{preview}（{narrative_hint}）",
        "reflective_deep": f"深度反思后回应：{preview}，对齐核心信念。",
    }
    response_text = templates.get(assumption_seed, f"假设[{assumption_seed}]下回应：{preview}")

    impact_map = {
        "helpful_direct": 0.02,
        "cautious_contextual": 0.05,
        "reflective_deep": 0.04,
    }
    coherence_impact = impact_map.get(assumption_seed, 0.03)
    expected = estimate_branch_stability(
        baseline_coherence=baseline_coherence,
        coherence_impact=coherence_impact,
        core_beliefs=core_beliefs,
    )

    return ThoughtBranch(
        branch_id=branch_id,
        assumption_seed=assumption_seed,
        projected_state={
            "mode": assumption_seed,
            "query_preview": preview,
            "belief_anchor": max(core_beliefs, key=core_beliefs.get) if core_beliefs else "",
        },
        coherence_impact=coherence_impact,
        response_text=response_text,
        expected_stability_score=expected,
    )


def append_simulation_trace(base_dir: Optional[str], traj: SimulatedTraj) -> None:
    """Persist simulation round to Σ.T only — never touches Σ.I / decide domain."""
    if not base_dir:
        return
    from core.runtime.trace_store import append_trace_row

    for branch in traj.branches:
        append_trace_row(
            base_dir,
            {
                "type": "simulation_step",
                "step": "thought_branch",
                "trace_id": traj.trace_id,
                "branch_id": branch.branch_id,
                "assumption_seed": branch.assumption_seed,
                "coherence_impact": branch.coherence_impact,
                "expected_stability_score": branch.expected_stability_score,
                "projected_state": branch.projected_state,
                "response_preview": branch.response_text[:240],
            },
        )
    append_trace_row(
        base_dir,
        {
            "type": "simulation_step",
            "step": "simulation_complete",
            "trace_id": traj.trace_id,
            "branch_count": len(traj.branches),
            "baseline_coherence": traj.baseline_coherence,
            "query_preview": traj.query_preview[:200],
        },
    )


class SimulationEngine:
    """Fork parallel ThoughtBranches under SimulationBudget — background-safe."""

    def __init__(
        self,
        *,
        budget: Optional[SimulationBudget] = None,
        branch_simulator: Optional[BranchSimulatorFn] = None,
    ) -> None:
        self.budget = budget or _default_budget()
        self._branch_simulator = branch_simulator

    def run_simulation(
        self,
        *,
        user_query: str,
        recent_narrative: str = "",
        core_beliefs: Optional[Dict[str, float]] = None,
        baseline_coherence: float = 0.85,
        assumption_seeds: Optional[Sequence[str]] = None,
        base_dir: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> SimulatedTraj:
        beliefs = dict(core_beliefs or {})
        seeds = list(assumption_seeds or DEFAULT_ASSUMPTION_SEEDS)
        branch_count = self.budget.clamp_branch_count(len(seeds))
        seeds = seeds[:branch_count]

        tid = trace_id or f"sim-{uuid.uuid4().hex[:16]}"
        deadline = time.monotonic() + self.budget.max_wall_ms / 1000.0
        branches: List[ThoughtBranch] = []

        simulator = self._branch_simulator or self._default_simulator(
            recent_narrative=recent_narrative,
            baseline_coherence=baseline_coherence,
            core_beliefs=beliefs,
        )

        workers = min(self.budget.max_parallel_workers, len(seeds))
        if workers <= 1:
            for idx, seed in enumerate(seeds):
                if time.monotonic() >= deadline:
                    break
                branches.append(simulator(f"b{idx}", seed, user_query, beliefs))
        else:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cnexus-l4-sim") as pool:
                futures = {
                    pool.submit(simulator, f"b{idx}", seed, user_query, beliefs): seed
                    for idx, seed in enumerate(seeds)
                }
                for fut in as_completed(futures):
                    if time.monotonic() >= deadline:
                        break
                    try:
                        branches.append(fut.result())
                    except Exception as exc:
                        logger.debug("L4 branch simulation failed: %s", exc)

        branches.sort(key=lambda b: b.expected_stability_score, reverse=True)
        traj = SimulatedTraj(
            trace_id=tid,
            branches=branches,
            baseline_coherence=float(baseline_coherence),
            query_preview=user_query[:200],
        )
        append_simulation_trace(base_dir, traj)
        return traj

    def run_to_candidates(self, **kwargs: Any) -> List[CandidateResponse]:
        traj = self.run_simulation(**kwargs)
        return traj.candidates

    def run_filtered_simulation(
        self,
        *,
        evaluator: Optional[Any] = None,
        llm_reflect: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """L4-2 — simulate then evaluate/prune branches (Σ.T only)."""
        from core.runtime.conscious_flow.trajectory_evaluator import (
            TrajectoryEvaluator,
            evaluate_trajectories,
        )

        traj = self.run_simulation(**kwargs)
        ev = evaluator or TrajectoryEvaluator()
        return evaluate_trajectories(
            traj.candidates,
            trace_id=traj.trace_id,
            recent_narrative=str(kwargs.get("recent_narrative") or ""),
            core_beliefs=kwargs.get("core_beliefs"),
            baseline_coherence=float(kwargs.get("baseline_coherence") or traj.baseline_coherence),
            base_dir=kwargs.get("base_dir"),
            llm_reflect=llm_reflect,
            evaluator=ev,
        )

    def run_to_filtered_candidates(self, **kwargs: Any) -> List[CandidateResponse]:
        report = self.run_filtered_simulation(**kwargs)
        return report.candidates

    def _default_simulator(
        self,
        *,
        recent_narrative: str,
        baseline_coherence: float,
        core_beliefs: Dict[str, float],
    ) -> BranchSimulatorFn:
        def _simulate(
            branch_id: str,
            assumption_seed: str,
            user_query: str,
            beliefs: Dict[str, float],
        ) -> ThoughtBranch:
            return rule_based_branch_simulator(
                branch_id,
                assumption_seed,
                user_query,
                beliefs or core_beliefs,
                recent_narrative=recent_narrative,
                baseline_coherence=baseline_coherence,
            )

        return _simulate


def schedule_background_simulation(
    *,
    runtime: Any,
    user_query: str,
    budget: Optional[SimulationBudget] = None,
) -> None:
    """Non-blocking entry — never on L0 chat critical path."""
    from core.runtime.llm_executor_pool import ExecutorPool

    ExecutorPool.background_executor().submit(
        _background_simulation,
        runtime,
        user_query,
        budget,
    )


def _background_simulation(
    runtime: Any,
    user_query: str,
    budget: Optional[SimulationBudget],
) -> None:
    try:
        base_dir = str(getattr(runtime, "base_dir", "") or "")
        store = getattr(runtime, "self_model_store", None)
        model = getattr(store, "model", None) if store is not None else None
        beliefs = dict(getattr(model, "core_beliefs", None) or {})
        coherence = float(getattr(model, "coherence_score", 0.85) or 0.85)

        from core.personality.narrative.recent_context import load_recent_narrative_prompt_block

        recent = load_recent_narrative_prompt_block(base_dir)

        engine = SimulationEngine(budget=budget)
        engine.run_filtered_simulation(
            user_query=user_query,
            recent_narrative=recent,
            core_beliefs=beliefs,
            baseline_coherence=coherence,
            base_dir=base_dir,
        )
    except Exception as exc:
        logger.debug("background simulation failed: %s", exc)

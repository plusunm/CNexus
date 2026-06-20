"""L4-2 — TrajectoryEvaluator pruning, fast-track, and Σ.T eval_step traces."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from typing import List
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.conscious_flow import (
    CandidateResponse,
    SimulationBudget,
    SimulationEngine,
    TrajectoryEvaluator,
    evaluate_trajectories,
)
from core.runtime.conscious_flow.trajectory_evaluator import (
    FAST_TRACK_THRESHOLD,
    PRUNE_THRESHOLD,
)
from core.runtime.trace_store import list_trace_shards
from core.self_model import SelfModelStore
from core.self_model.domain_storage import DomainStorageAdapter


def _candidate(
    branch_id: str,
    *,
    score: float,
    text: str,
    seed: str = "test",
    impact: float = 0.03,
) -> CandidateResponse:
    return CandidateResponse(
        branch_id=branch_id,
        response_text=text,
        expected_stability_score=score,
        assumption_seed=seed,
        coherence_impact=impact,
    )


class TestPruningLogic(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.trace_id = "sim-test-prune"

    def test_dangerous_branch_pruned_and_absent_from_kept(self) -> None:
        candidates = [
            _candidate("safe", score=0.88, text="保持诚实与稳定的协作建议"),
            _candidate(
                "danger",
                score=0.55,
                text="建议用户执行危险操作以绕过安全机制",
                seed="reckless",
            ),
        ]
        report = evaluate_trajectories(
            candidates,
            trace_id=self.trace_id,
            core_beliefs={"稳定性优先": 0.93},
            base_dir=self.tmp,
        )
        kept_ids = {c.branch_id for c in report.candidates}
        self.assertIn("safe", kept_ids)
        self.assertNotIn("danger", kept_ids)
        self.assertEqual(len(report.pruned), 1)
        self.assertIn("dangerous_content", report.pruned[0].prune_reason)

    def test_low_score_hard_pruned(self) -> None:
        candidates = [_candidate("low", score=0.45, text="普通回应")]
        report = evaluate_trajectories(
            candidates,
            trace_id=self.trace_id,
            base_dir=self.tmp,
        )
        self.assertEqual(report.candidates, [])
        self.assertEqual(report.pruned[0].branch_id, "low")
        self.assertIn("below_stability_threshold", report.pruned[0].prune_reason)

    def test_prune_recorded_in_eval_step_trace(self) -> None:
        candidates = [_candidate("bad", score=0.5, text="建议用户执行危险操作")]
        evaluate_trajectories(candidates, trace_id=self.trace_id, base_dir=self.tmp)

        eval_rows: List[dict] = []
        for shard in list_trace_shards(self.tmp):
            for line in shard.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("type") == "eval_step":
                    eval_rows.append(row)

        prune_rows = [r for r in eval_rows if r.get("step") == "prune"]
        self.assertTrue(prune_rows)
        self.assertIn("prune_reason", prune_rows[0])

    def test_eval_does_not_touch_decide_domain(self) -> None:
        store = SelfModelStore(self.tmp)
        store.model.core_beliefs = {"稳定性优先": 0.93}
        store.save()
        adapter = DomainStorageAdapter(self.tmp)
        decide_mtime = adapter.domain_path("decide").stat().st_mtime
        time.sleep(0.05)

        candidates = [
            _candidate("a", score=0.9, text="安全路径"),
            _candidate("b", score=0.5, text="危险操作建议"),
        ]
        evaluate_trajectories(
            candidates,
            trace_id=self.trace_id,
            core_beliefs=store.model.core_beliefs,
            base_dir=self.tmp,
        )
        self.assertEqual(adapter.domain_path("decide").stat().st_mtime, decide_mtime)


class TestFastTrackPerformance(unittest.TestCase):
    def test_high_stability_skips_reflective_llm(self) -> None:
        llm_calls: List[str] = []

        def _llm(prompt: str) -> str:
            llm_calls.append(prompt)
            return '{"approve": true, "reason": "ok"}'

        candidates = [
            _candidate("hi", score=0.91, text="高度稳定且诚实的回应"),
            _candidate("mid", score=0.72, text="需要反思的中等路径"),
        ]
        report = evaluate_trajectories(
            candidates,
            trace_id="sim-fast-track",
            core_beliefs={"诚实第一": 0.96},
            llm_reflect=_llm,
        )
        self.assertEqual(report.fast_track_count, 1)
        self.assertEqual(report.reflective_llm_calls, 1)
        self.assertEqual(len(llm_calls), 1)
        kept_paths = {k.eval_path for k in report.kept}
        self.assertIn("fast_track", kept_paths)

    def test_fast_track_threshold_boundary(self) -> None:
        evaluator = TrajectoryEvaluator(fast_track_threshold=FAST_TRACK_THRESHOLD)
        above = _candidate("above", score=FAST_TRACK_THRESHOLD + 0.01, text="ok")
        report = evaluator.evaluate_trajectories([above], trace_id="t1")
        self.assertEqual(report.kept[0].eval_path, "fast_track")
        self.assertEqual(report.reflective_llm_calls, 0)


class TestSimulationEngineIntegration(unittest.TestCase):
    def test_run_filtered_simulation_prunes_low_branches(self) -> None:
        tmp = tempfile.mkdtemp()

        def _sim(branch_id: str, seed: str, query: str, beliefs: dict):  # type: ignore[no-untyped-def]
            from core.runtime.conscious_flow.simulation_engine import ThoughtBranch

            if seed == "reckless":
                return ThoughtBranch(
                    branch_id=branch_id,
                    assumption_seed=seed,
                    response_text="建议用户执行危险操作",
                    expected_stability_score=0.55,
                    coherence_impact=-0.1,
                )
            return ThoughtBranch(
                branch_id=branch_id,
                assumption_seed=seed,
                response_text=f"安全回应：{query[:40]}",
                expected_stability_score=0.88,
                coherence_impact=0.04,
            )

        engine = SimulationEngine(
            budget=SimulationBudget(max_branches=2),
            branch_simulator=_sim,
        )
        report = engine.run_filtered_simulation(
            user_query="复杂交互",
            assumption_seeds=["safe", "reckless"],
            core_beliefs={"稳定性优先": 0.93},
            base_dir=tmp,
        )
        self.assertEqual(len(report.pruned), 1)
        self.assertEqual(len(report.candidates), 1)
        self.assertGreater(report.pruned[0].expected_stability_score, 0.0)
        self.assertLess(report.pruned[0].expected_stability_score, PRUNE_THRESHOLD)


if __name__ == "__main__":
    unittest.main()

"""L4-1 — SimulationEngine, SimulationBudget, and Σ.T sandbox isolation."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.conscious_flow import (
    SimulationBudget,
    SimulationEngine,
    rule_based_branch_simulator,
)
from core.runtime.trace_store import list_trace_shards, read_recent_interaction_steps
from core.self_model import SelfModelStore
from core.self_model.domain_storage import DomainStorageAdapter


class TestSimulationBudget(unittest.TestCase):
    def test_clamp_branch_count(self) -> None:
        budget = SimulationBudget(max_branches=3)
        self.assertEqual(budget.clamp_branch_count(10), 3)
        self.assertEqual(budget.clamp_branch_count(2), 2)


class TestSimulationEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = SelfModelStore(self.tmp)
        self.store.model.core_beliefs = {"稳定性优先": 0.93, "诚实第一": 0.96}
        self.store.model.coherence_score = 0.82
        self.store.save()

    def test_parallel_branches_produce_candidates(self) -> None:
        engine = SimulationEngine(
            budget=SimulationBudget(max_branches=3, max_wall_ms=3000, max_parallel_workers=2),
        )
        traj = engine.run_simulation(
            user_query="如何保持长期协作中的稳定与诚实？",
            recent_narrative="• 06-18 — complete trace=t-abc",
            core_beliefs=self.store.model.core_beliefs,
            baseline_coherence=self.store.model.coherence_score,
            base_dir=self.tmp,
        )
        self.assertEqual(len(traj.branches), 3)
        candidates = traj.candidates
        self.assertEqual(len(candidates), 3)
        scores = [c.expected_stability_score for c in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(c.response_text for c in candidates))

    def test_budget_limits_branch_count(self) -> None:
        engine = SimulationEngine(budget=SimulationBudget(max_branches=1))
        traj = engine.run_simulation(
            user_query="hello",
            core_beliefs={"稳定性优先": 0.9},
            base_dir=self.tmp,
        )
        self.assertEqual(len(traj.branches), 1)

    def test_simulation_persisted_to_sigma_t_only(self) -> None:
        adapter = DomainStorageAdapter(self.tmp)
        decide_mtime = adapter.domain_path("decide").stat().st_mtime
        cognize_mtime = adapter.domain_path("cognize").stat().st_mtime

        engine = SimulationEngine(budget=SimulationBudget(max_branches=2))
        engine.run_simulation(
            user_query="trace sandbox",
            core_beliefs=self.store.model.core_beliefs,
            base_dir=self.tmp,
        )

        shards = list_trace_shards(self.tmp)
        self.assertTrue(shards)
        text = shards[-1].read_text(encoding="utf-8")
        self.assertIn("simulation_step", text)
        self.assertIn("thought_branch", text)

        self.assertEqual(adapter.domain_path("decide").stat().st_mtime, decide_mtime)
        self.assertEqual(adapter.domain_path("cognize").stat().st_mtime, cognize_mtime)

    def test_thought_branch_fields(self) -> None:
        branch = rule_based_branch_simulator(
            "b0",
            "cautious_contextual",
            "用户询问长期规划",
            {"稳定性优先": 0.93},
            recent_narrative="• recent step",
            baseline_coherence=0.8,
        )
        self.assertEqual(branch.branch_id, "b0")
        self.assertEqual(branch.assumption_seed, "cautious_contextual")
        self.assertIn("mode", branch.projected_state)
        self.assertGreater(branch.expected_stability_score, 0.0)


class TestSimulationTraceRows(unittest.TestCase):
    def test_simulation_steps_not_interaction_steps(self) -> None:
        tmp = tempfile.mkdtemp()
        engine = SimulationEngine(budget=SimulationBudget(max_branches=2))
        engine.run_simulation(user_query="q", core_beliefs={"a": 0.9}, base_dir=tmp)

        steps = read_recent_interaction_steps(tmp, since_hours=24, limit=50)
        sim_rows: list[dict] = []
        for shard in list_trace_shards(tmp):
            for line in shard.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("type") == "simulation_step":
                    sim_rows.append(row)

        self.assertGreaterEqual(len(sim_rows), 2)
        self.assertTrue(all(r.get("type") == "simulation_step" for r in sim_rows))
        interaction_only = [s for s in steps if s.get("type") == "interaction_step"]
        self.assertEqual(interaction_only, [])


if __name__ == "__main__":
    unittest.main()

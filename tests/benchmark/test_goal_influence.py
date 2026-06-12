"""Goal influence benchmark — current goal should outweigh stale episodic memory."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime
from memory.runtime_guard import runtime_write_context


class TestGoalInfluenceBenchmark(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir)

    def test_goal_context_outranks_stale_episodic_preference(self):
        with runtime_write_context():
            self.runtime.capture(
                "user",
                "旧偏好：优先短期效率与快速交付",
                layer="episodic",
                importance=0.95,
            )
            self.runtime.capture(
                "user",
                "长期目标：维护系统稳定性与认知连续性",
                layer="goal",
                importance=0.9,
                context={"goal_motivation": 0.9, "goal_priority": 0.85},
            )

        context = self.runtime.recall("系统维护策略")
        self.assertIn("Intent Context", context)
        self.assertIn("稳定性", context)

        explain = self.runtime.recall_pipeline.last_explain
        ranking = explain.get("ranking") or []
        goal_boost_hits = [row for row in ranking if row.get("goal_boost") or row.get("attention_boost")]
        self.assertTrue(
            "稳定性" in context or "连续性" in context or goal_boost_hits,
            "recall should surface goal-aligned context",
        )

        goals = self.runtime.goal_manager.active_goals(1)
        self.assertGreater(len(goals), 0)
        self.assertIn("稳定", goals[0].description)

        boost = self.runtime.goal_manager.motivation_boost()
        self.assertGreater(boost, 0.0)


if __name__ == "__main__":
    unittest.main()

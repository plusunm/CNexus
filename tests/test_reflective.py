import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory import BrainMemoryRuntime


class TestReflectiveContinuity(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = BrainMemoryRuntime(project_root=self._tmpdir, base_dir="memory")

    def test_trait_based_reflection(self):
        record = self.runtime.trait_based_reflection(
            content="最近我容易把主观感受当作客观事实",
            traits=["主观臆断", "情绪化"],
        )
        self.assertEqual(record.traits, ["主观臆断", "情绪化"])
        self.assertGreater(len(record.action_steps), 0)
        self.assertEqual(record.status, "active")
        self.assertEqual(len(self.runtime.reflection_pipeline.records), 1)

    def test_auto_trait_detection(self):
        record = self.runtime.trait_based_reflection(
            content="我今天很冲动，情绪上来就做了决定",
        )
        self.assertIn("情绪化", record.traits)

    def test_reflection_updates_belief_and_narrative(self):
        before_beliefs = len(self.runtime.belief_engine.graph.beliefs)
        before_goals = len(self.runtime.narrative.narrative.long_term_goals)

        self.runtime.trait_based_reflection(
            content="最近容易把主观感受当作客观事实",
            traits=["主观臆断"],
        )

        self.assertGreater(len(self.runtime.belief_engine.graph.beliefs), before_beliefs)
        self.assertGreaterEqual(len(self.runtime.narrative.narrative.long_term_goals), before_goals)


if __name__ == "__main__":
    unittest.main()

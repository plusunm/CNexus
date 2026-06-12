import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory import BrainMemoryRuntime, create_runtime


class TestModuleWiring(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = create_runtime(project_root=self._tmpdir, base_dir="memory")

    def test_facade_create_runtime(self):
        self.assertIsNotNone(self.runtime.storage)
        self.assertIsNotNone(self.runtime.reflection_pipeline)
        self.assertIsNotNone(self.runtime.stability.detector.reflection)

    def test_recall_syncs_attention_state(self):
        self.runtime.capture("user", "长期目标是维护身份连续性", layer="goal", importance=0.9)
        self.runtime.recall("我的长期目标")
        self.assertGreaterEqual(self.runtime.state.cognitive_load, 0.0)
        snapshot = self.runtime.memory.get_attention_snapshot()
        self.assertGreaterEqual(snapshot.get("last_sync_turn", 0), 1)

    def test_get_full_status(self):
        status = self.runtime.get_full_status()
        self.assertEqual(status["version"], "1.0.0-g1")
        self.assertIn("personality", status["layers"])

    def test_reflection_persists_to_store(self):
        record = self.runtime.trait_based_reflection("容易主观臆断", traits=["主观臆断"])
        self.assertTrue(self.runtime.reflective_store.get(record.reflection_id))

    def test_governance_includes_reflection(self):
        self.runtime.trait_based_reflection("测试反思", traits=["急躁"])
        report = self.runtime.run_governance_cycle()
        self.assertIn("reflection_summary", report)


if __name__ == "__main__":
    unittest.main()

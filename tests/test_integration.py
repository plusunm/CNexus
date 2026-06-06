import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory import BrainMemoryRuntime


class TestBrainMemoryRuntime(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = BrainMemoryRuntime(
            base_dir="memory",
            project_root=self._tmpdir,
        )

    def test_full_stability_cycle(self):
        mid = self.runtime.capture(
            "user", "长期目标是维护身份连续性", layer="goal", importance=0.92
        )
        self.assertIsNotNone(mid)
        self.assertNotIn("denied", str(mid).lower())

        context = self.runtime.recall("我的身份和目标")
        self.assertIn("Identity", context)

        report = self.runtime.run_governance_cycle()
        self.assertGreater(report["stability_metrics"]["overall_stability_score"], 0.75)

        validation = self.runtime.run_validation_suite(days=30)
        self.assertGreater(validation["overall_stability_score"], 0.7)

    def test_write_gate(self):
        result = self.runtime.capture("toolResult", "{" * 100, importance=0.1)
        self.assertIn("denied", str(result).lower())


if __name__ == "__main__":
    unittest.main()

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory import create_runtime
from core.runtime_profile import apply_runtime_profile


class TestCaptureCognition(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = create_runtime(
            project_root=self._tmpdir,
            base_dir="memory",
        )
        self.runtime.config["capture_cognize_default"] = True

    def test_process_capture_cognition_runs_reflection(self):
        before = len(self.runtime.reflection_pipeline.records)
        out = self.runtime.process_capture_cognition(
            "导入了一段关于长期目标的新材料",
            layer="episodic",
            memory_id="mem-1",
            trigger_governance=False,
        )
        self.assertNotIn("skipped", out)
        self.assertIn("reflection_id", out)
        self.assertGreater(len(self.runtime.reflection_pipeline.records), before)

    def test_capture_cognize_can_be_skipped(self):
        out = self.runtime.process_capture_cognition("", trigger_governance=False)
        self.assertTrue(out.get("skipped"))


class TestGovernanceLoopState(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = create_runtime(
            project_root=self._tmpdir,
            base_dir="memory",
        )

    def test_run_governance_sets_last_run_at(self):
        self.assertIsNone(self.runtime._last_governance_at)
        self.runtime.run_governance_cycle()
        self.assertIsNotNone(self.runtime._last_governance_at)

    def test_get_current_state_exposes_governance_loop(self):
        self.runtime.run_governance_cycle()
        state = self.runtime.get_current_state()
        loop = state.get("governance_loop") or {}
        self.assertTrue(loop.get("background_enabled"))
        self.assertIsNotNone(loop.get("last_run_at"))


class TestChatFullLoopConfig(unittest.TestCase):
    def test_auto_mode_applies_compute_policy(self):
        merged = apply_runtime_profile(
            {
                "runtime_mode": "auto",
                "compute": {"override": {"ram_gb": 16, "cpu_cores": 8, "gpu": False}},
            }
        )
        self.assertEqual(merged["runtime_envelope"], "safe_baseline")
        self.assertFalse(merged.get("chat_default_full_cognitive_loop"))

    def test_unrestricted_mode_keeps_full_loop(self):
        with patch.dict(os.environ, {"CNEXUS_RUNTIME_MODE": "unrestricted"}):
            merged = apply_runtime_profile(
                {
                    "runtime_mode": "auto",
                    "compute": {"override": {"ram_gb": 16, "cpu_cores": 8, "gpu": False}},
                }
            )
        self.assertTrue(merged.get("chat_default_full_cognitive_loop"))


if __name__ == "__main__":
    unittest.main()

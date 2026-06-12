"""L8/G8 influence causality test suite — unit tests."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tests.influence.diff_analyzer import DiffAnalyzer
from core.tests.influence.metrics import memory_drift_score, response_drift_score, routing_drift_score
from core.tests.influence.report import build_report
from core.tests.influence.runner import InfluenceTestRunner


class TestL8G8Influence(unittest.TestCase):
    def test_metrics_zero_on_identical(self):
        self.assertEqual(response_drift_score(["a"], ["a"]), 0.0)
        self.assertEqual(
            memory_drift_score(
                [{"importance": 0.5, "layer": "episodic", "denied": False, "role": "user"}],
                [{"importance": 0.5, "layer": "episodic", "denied": False, "role": "user"}],
            ),
            0.0,
        )
        self.assertEqual(
            routing_drift_score([{"pipeline": "g2"}], [{"pipeline": "g2"}]),
            0.0,
        )

    def test_routing_drift_detects_mismatch(self):
        score = routing_drift_score(
            [{"pipeline": "g2", "runtime_mode": "g2"}],
            [{"pipeline": "hybrid_recall", "runtime_mode": "legacy"}],
        )
        self.assertEqual(score, 1.0)

    def test_full_influence_run_no_leakage(self):
        runner = InfluenceTestRunner()
        report = runner.run_full()
        self.assertEqual(report["experiment"], "L8_G8_influence_test_v1")
        self.assertTrue(report["meta"]["observational_only"])
        self.assertFalse(report["conclusion"]["control_leakage"], report)
        self.assertFalse(report["conclusion"]["semantic_leakage"], report)
        self.assertIn("observational_only_confirmed", report["interpretation"])

    def test_baseline_and_injection_isolated(self):
        runner = InfluenceTestRunner()
        baseline = runner.run_baseline()
        injection = runner.run_injection()
        self.assertNotEqual(baseline["data_dir"], injection["data_dir"])
        self.assertFalse(baseline["stimulus_applied"])
        self.assertTrue(injection["stimulus_applied"])

    def test_diff_analyzer_significant_when_routing_differs(self):
        analyzer = DiffAnalyzer()
        baseline = {"responses": ["x"], "memory_trace": [], "routing_trace": [{"pipeline": "a"}]}
        test = {"responses": ["x"], "memory_trace": [], "routing_trace": [{"pipeline": "b"}]}
        diff = analyzer.analyze(baseline, test)
        self.assertTrue(diff["significant"])
        report = build_report(baseline, test, diff)
        self.assertTrue(report["conclusion"]["control_leakage"])

    def test_influence_cli_full_mode(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "run_l8g8_influence_test.py"), "--mode", "full", "--text"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Influence Causality", proc.stdout)
        self.assertIn("observational_only", proc.stdout.lower() or proc.stdout)


if __name__ == "__main__":
    unittest.main()

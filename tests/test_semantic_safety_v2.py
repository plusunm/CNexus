"""Semantic Safety Stack v2 tests."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import build_l3_g1_report, build_l3_g6_report
from core.governance.semantic_safety.envelope import OBSERVATIONAL_SAFETY_V2, stamp_observational_safe


class TestSemanticSafetyV2(unittest.TestCase):
    def test_observational_envelope_on_g1(self):
        payload = build_l3_g1_report(use_l2_coupling=False).to_dict()
        self.assertEqual(payload["role"], "observational_only")
        self.assertTrue(payload["observational_safe"])
        self.assertIn("simulation_result", payload)

    def test_g6_severity_band_not_boolean_gate(self):
        payload = build_l3_g6_report(use_l2_coupling=False).to_dict()
        self.assertIn("collapse_severity_band", payload)
        self.assertNotIn("collapse_detected", payload)
        self.assertIn("explainability_retention_metric", payload)

    def test_stamp_observational_safe(self):
        row = stamp_observational_safe({"type": "test_snapshot", "value": 1})
        self.assertTrue(row["observational_safe"])
        self.assertEqual(row["semantic_safety_version"], OBSERVATIONAL_SAFETY_V2["semantic_safety_version"])

    def test_semantic_safety_checker_script(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "semantic_safety_check.py")],
            capture_output=True,
            text=True,
            cwd=str(root),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertIn(report["status"], ("pass", "warn"))


if __name__ == "__main__":
    unittest.main()

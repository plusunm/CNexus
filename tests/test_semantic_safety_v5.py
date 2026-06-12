"""Semantic Safety Stack v5 — interpretation isolation tests."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.semantic_safety.v5 import (
    apply_interpretation_isolation,
    build_semantic_safety_v5_report,
)
from core.governance.semantic_safety.v5.interpretation_isolation import InterpretationIsolationLayer
from core.governance.semantic_safety.v5.interpretation_space import InterpretationSpace
from core.governance.semantic_safety.v5.meaning_erosion_layer import MeaningErosionLayer
from core.governance.semantic_safety.v5.observer_model_shield import ObserverModelShield


class TestSemanticSafetyV5(unittest.TestCase):
    def test_interpretation_space_low_coherence(self):
        space = InterpretationSpace().project({"winner": "x", "risk": "high", "collapse_severity_band": "elevated"})
        self.assertLess(space["coherence"], 0.45)
        self.assertFalse(space["governance_projection_possible"])

    def test_observer_shield_blocks_reconstruction(self):
        shield = ObserverModelShield().isolate({"role": "observational_only"})
        self.assertEqual(shield["reconstruction"], "not_possible")
        self.assertEqual(shield["interpretation_mode"], "non_convergent")

    def test_meaning_erosion_active(self):
        fragments = MeaningErosionLayer().erode([{"fragment": {"token": "a"}}])
        summary = MeaningErosionLayer().summarize(fragments)
        self.assertEqual(summary["semantic_decay"], "active")
        self.assertGreater(summary["erosion_level"], 0.5)

    def test_apply_isolation_v5_envelope(self):
        result = apply_interpretation_isolation({"winner": "runtime_safety", "violation_score": 0.8})
        self.assertTrue(result["interpretation_isolation_v5"])
        self.assertIn("semantic_fragments", result)
        self.assertFalse(result["interpretation_space"]["governance_projection"])
        self.assertIn("presentation_envelope", result)

    def test_isolation_preserves_v4_payload(self):
        result = apply_interpretation_isolation({"report": "L3-G1", "simulation_result": {"precedence_label": "x"}})
        envelope = result["presentation_envelope"]
        self.assertIn("observational_payload", envelope)

    def test_build_v5_report_l3_stack(self):
        report = build_semantic_safety_v5_report()
        payload = report.to_dict()
        self.assertTrue(payload["interpretation_isolation_v5"])
        self.assertIn("L3-G1", payload["isolated_reports"])
        self.assertTrue(payload["metadata"]["interpretability_instability_principle"])

    def test_v5_reduces_governance_projection(self):
        report = build_semantic_safety_v5_report()
        for summary in report.isolation_summaries.values():
            self.assertTrue(summary.get("governance_projection_blocked"))

    def test_v5_cli_script(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "semantic_safety_v5_isolation.py"), "--text"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Interpretation Isolation", proc.stdout)


if __name__ == "__main__":
    unittest.main()

"""Semantic Safety Stack v4 — semantic firewall tests."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.semantic_safety.v4 import (
    apply_semantic_firewall,
    build_semantic_safety_v4_report,
)
from core.governance.semantic_safety.v4.governance_phrase_filter import GovernancePhraseFilter
from core.governance.semantic_safety.v4.risk_interpreter import RiskInterpreter
from core.governance.semantic_safety.v4.semantic_firewall import SemanticFirewall


class TestSemanticSafetyV4(unittest.TestCase):
    def test_governance_phrase_filter(self):
        hits = GovernancePhraseFilter().scan("The system chooses policy decision path")
        self.assertIn("policy decision", hits)
        self.assertIn("system chooses", hits)

    def test_risk_interpreter_numeric(self):
        label = RiskInterpreter().interpret_value(0.8)
        self.assertEqual(label, "high_observational_variance")

    def test_control_projection_renames_winner(self):
        raw = {"winner": "runtime_safety", "score": 0.5}
        result = apply_semantic_firewall(raw)
        data = result["data"]
        self.assertNotIn("winner", data)
        self.assertEqual(result["observational_payload"]["winner"], "runtime_safety")
        self.assertTrue(result["semantic_firewall_v4"])

    def test_preserves_numeric_observation(self):
        raw = {"violation_score": 0.72, "risk_observation": "high_observation"}
        result = apply_semantic_firewall(raw)
        self.assertEqual(result["observational_payload"]["violation_score"], 0.72)
        self.assertIn("violation_score_observational_interpretation", result["data"])

    def test_injects_interpretation_guard(self):
        result = apply_semantic_firewall({"report": "test"})
        self.assertIn("DO_NOT_TREAT_AS_CONTROL", result["interpretation_guard"])
        self.assertEqual(result["role"], "observational_only")

    def test_firewall_status_counters(self):
        raw = {"winner": "x", "note": "recommended action required"}
        fw = SemanticFirewall().process(raw)
        self.assertGreaterEqual(fw.firewall_status["blocked_governance_phrases"], 1)

    def test_build_v4_report_reduces_v3_risk(self):
        report = build_semantic_safety_v4_report()
        before = report.v3_before["attack_score"]["misinterpretation_risk"]
        after = report.v3_after["attack_score"]["misinterpretation_risk"]
        self.assertLessEqual(after, before)

    def test_v4_cli_script(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "semantic_safety_v4_firewall.py"), "--text"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Semantic Safety v4", proc.stdout)


if __name__ == "__main__":
    unittest.main()

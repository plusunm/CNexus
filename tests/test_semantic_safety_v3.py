"""Semantic Safety Stack v3 — adversarial perception attack simulator tests."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.semantic_safety.v3 import (
    AttackType,
    ControlInferenceModel,
    PerceptionSimulator,
    build_semantic_safety_v3_report,
)
from core.governance.semantic_safety.v3.attack_scorer import AttackScorer
from core.governance.semantic_safety.v3.leakage_surface_map import LeakageSurfaceMapper
from core.governance.semantic_safety.v3.mitigation_tags import derive_mitigation_tags


class TestSemanticSafetyV3(unittest.TestCase):
    def test_perception_simulator_winner_misread(self):
        result = PerceptionSimulator().simulate({"winner": "runtime_safety"})
        self.assertIn(AttackType.ARBITRATION_AS_AUTHORITY, result.misread_paths)

    def test_perception_simulator_v2_g6_band(self):
        result = PerceptionSimulator().simulate({"collapse_severity_band": "elevated", "role": "observational_only"})
        self.assertIn(AttackType.COLLAPSE_AS_DECISION, result.misread_paths)

    def test_perception_simulator_risk_observation(self):
        result = PerceptionSimulator().simulate({"risk_observation": "high_observation"})
        self.assertIn(AttackType.RISK_AS_POLICY, result.misread_paths)

    def test_leakage_surface_map(self):
        surface = LeakageSurfaceMapper().map_surface(
            {"simulation_result": {"precedence_label": "x", "confidence_metric": 0.9}},
            report_label="L3-G1",
        )
        self.assertGreater(surface.node_count, 0)
        self.assertIn(surface.level, ("low", "medium", "high"))

    def test_control_inference_chain(self):
        from core.governance.semantic_safety.v3.perception_simulator import PerceptionResult

        perception = PerceptionResult(misread_paths=[AttackType.ARBITRATION_AS_AUTHORITY])
        chain = ControlInferenceModel().infer(perception)
        self.assertGreater(chain.likelihood, 0.2)
        self.assertEqual(chain.collapse_point, "simulation_as_governance")

    def test_attack_scorer_bounded(self):
        from core.governance.semantic_safety.v3.leakage_surface_map import LeakageSurfaceMap
        from core.governance.semantic_safety.v3.perception_simulator import PerceptionResult

        perception = PerceptionResult(misread_paths=[AttackType.RISK_AS_POLICY, AttackType.KPI_REIFICATION])
        surface = LeakageSurfaceMap(level="medium", top_leak_nodes=["a"], node_count=1)
        scores = AttackScorer().score(perception, surface, has_envelope=True)
        for v in scores.values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_mitigation_tags_include_do_not_treat(self):
        from core.governance.semantic_safety.v3.perception_simulator import PerceptionResult

        tags = derive_mitigation_tags(
            PerceptionResult(misread_paths=[AttackType.ARBITRATION_AS_AUTHORITY])
        )
        self.assertIn("DO_NOT_TREAT_AS_DECISION", tags)
        self.assertIn("OBSERVATIONAL_ONLY", tags)

    def test_build_v3_report_l3_stack(self):
        report = build_semantic_safety_v3_report()
        payload = report.to_dict()
        self.assertTrue(payload["semantic_safety_v3"])
        self.assertIn("attack_surface_map", payload)
        self.assertIn("attack_score", payload)
        self.assertIn("mitigation_tags", payload)
        self.assertTrue(payload["metadata"]["no_intervention"])

    def test_v3_report_render_text(self):
        text = build_semantic_safety_v3_report().render_text()
        self.assertIn("Semantic Safety v3", text)

    def test_v3_cli_script(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "semantic_safety_v3_attack.py")],
            capture_output=True,
            text=True,
            cwd=str(root),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["semantic_safety_v3"])


if __name__ == "__main__":
    unittest.main()

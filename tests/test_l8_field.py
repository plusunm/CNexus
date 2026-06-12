"""L8 — unified collapse & governance kernel tests."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l8 import (
    L8_CONSTRAINTS,
    CollapseUnifier,
    GovernanceUnifier,
    SafetyUnifier,
    SemanticTensorCore,
    UnifiedKernel,
    build_l8_report,
    build_l8_unified_state,
)


def _minimal_l3() -> dict:
    return {
        "G0": {"authority_leakage_band": "baseline"},
        "G1": {"violation_score": 0.4},
        "G2": {"shadow_impact_band": "low"},
        "G3": {"stability_band": "baseline"},
        "G4": {"meta_drift_band": "low"},
        "G5": {"layer_genesis_band": "baseline"},
        "G6": {"collapse_severity_band": "elevated", "explainability_retention_metric": 0.6},
        "G7": {"field_coherence": 0.55, "layerless_kernel_v7": True},
    }


def _minimal_safety() -> dict:
    return {
        "v1": {"semantic_safety_v1": True},
        "v2": {"semantic_safety_version": "2.0.0", "observational_only": True},
        "v3": {"adversarial_perception_v3": True},
        "v4": {"semantic_firewall_v4": True},
        "v5": {"interpretation_isolation_v5": True},
        "v6": {"cognitive_dissolution_v6": True, "temporal_coherence": "broken"},
        "v7": {"status": "reserved"},
    }


class TestL8UnifiedKernel(unittest.TestCase):
    def test_l8_constraints_frozen(self):
        self.assertTrue(L8_CONSTRAINTS["no_control_execution"])
        self.assertTrue(L8_CONSTRAINTS["tensor_only_representation"])

    def test_semantic_tensor_core_five_dimensions(self):
        core = SemanticTensorCore()
        tensor = core.tensorize({"stream_density": 0.6}, {"simulation_shadow": 0.4}, {"constraint_strength": 0.7})
        projected = core.project(tensor)
        self.assertEqual(len(projected["vector"]), 5)
        self.assertIn("collapsed_scalar", projected)

    def test_governance_unifier_flatten(self):
        flat = GovernanceUnifier().flatten_governance_graph(_minimal_l3())
        self.assertIn("authority_visibility", flat)
        self.assertEqual(len(flat), 8)

    def test_collapse_unifier_field_solver(self):
        core = SemanticTensorCore()
        tensor = core.project(core.tensorize({}, {"collapse_stability": 0.7}, {}))
        merged = CollapseUnifier().merge_collapse_signals(_minimal_l3(), _minimal_safety())
        field = CollapseUnifier().collapse_field_solver(tensor, merged)
        self.assertIn(field.mode, ("stable_field", "gradual_deformation", "critical_deformation"))

    def test_safety_envelope_builder(self):
        env = SafetyUnifier().safety_envelope_builder(_minimal_safety())
        self.assertIn("v6", env.versions)
        self.assertGreater(env.constraint_strength, 0)

    def test_unified_kernel_project(self):
        state = UnifiedKernel().project_unified_state(_minimal_l3(), _minimal_safety())
        self.assertIn("vector", state.semantic_tensor)
        self.assertIn("mode", state.collapse_field)
        self.assertGreaterEqual(state.stability_index, 0.0)

    def test_build_l8_unified_state_manual(self):
        state = build_l8_unified_state(_minimal_l3(), _minimal_safety(), auto_collect=False)
        self.assertGreater(state.coherence_index, 0)

    def test_build_l8_report_metadata(self):
        report = build_l8_report(
            _minimal_l3(),
            _minimal_safety(),
            auto_collect=False,
        )
        self.assertTrue(report.metadata["convergence_not_expansion"])
        self.assertTrue(report.constraints["no_governance_activation"])

    def test_build_l8_auto_collect(self):
        report = build_l8_report()
        payload = report.to_dict()
        self.assertIn("semantic_tensor", payload["unified_state"])

    def test_l8_cli_script(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "l8_field_report.py"), "--text"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Unified Collapse", proc.stdout)


if __name__ == "__main__":
    unittest.main()

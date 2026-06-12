"""L3-G6 collapse stability layer tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import build_l3_g6_report
from core.governance.l3.collapse_stability import (
    CollapseDetector,
    ExplainabilityAnchorManager,
    NonLayeredExplanationEngine,
    StabilityPreserver,
    build_l3_g6_report as assemble_g6,
    derive_collapse_system_state,
)
from core.governance.l3.collapse_stability.l3g6_report import L3G6Reporter
from core.governance.l3.collapse_stability.types import CollapseSignature


class TestL3G6(unittest.TestCase):
    def test_collapse_detector_low_severity(self):
        sig = CollapseDetector().detect(
            {
                "ontology_drift_index": 0.1,
                "layer_integrity": 0.9,
                "layer_system_stability": 0.85,
                "timestamp": 1.0,
            }
        )
        self.assertEqual(sig.collapse_type, "layer_blurring")
        self.assertLess(sig.severity, 0.5)

    def test_collapse_detector_high_severity(self):
        sig = CollapseDetector().detect(
            {
                "ontology_drift_index": 0.9,
                "layer_integrity": 0.2,
                "layer_system_stability": 0.2,
                "timestamp": 2.0,
            }
        )
        self.assertEqual(sig.collapse_type, "recursive_collapse")
        self.assertGreater(sig.severity, 0.7)

    def test_explainability_anchors(self):
        anchors = ExplainabilityAnchorManager().extract({"provenance_stability": 0.8, "timestamp": 3.0})
        self.assertEqual(len(anchors), 4)
        self.assertEqual(anchors[0].anchor_type, "provenance_chain")

    def test_nonlayered_model_coherence(self):
        anchors = ExplainabilityAnchorManager().extract(
            {
                "provenance_stability": 0.9,
                "causal_trace_strength": 0.85,
                "reflexivity_coherence": 0.8,
                "field_stability": 0.75,
            }
        )
        collapse = CollapseSignature("layer_blurring", [], 0.2, 0.18, 4.0)
        model = NonLayeredExplanationEngine().build(anchors, collapse, {"layer_signal_decay": 0.1})
        self.assertEqual(model.model_type, "causal_mesh")
        self.assertGreater(model.coherence_score, 0.7)

    def test_stability_preserver_penalty(self):
        anchors = ExplainabilityAnchorManager().extract({"provenance_stability": 0.6})
        collapse = CollapseSignature("recursive_collapse", ["L3"], 0.9, 0.81, 5.0)
        score = StabilityPreserver().compute(anchors, collapse)
        self.assertLess(score, 0.6)
        self.assertGreaterEqual(score, 0.0)

    def test_l3g6_reporter_metadata(self):
        anchors = ExplainabilityAnchorManager().extract({})
        collapse = CollapseSignature("boundary_dissolution", ["L2"], 0.55, 0.5, 6.0)
        model = NonLayeredExplanationEngine().build(anchors, collapse, {})
        stability = StabilityPreserver().compute(anchors, collapse)
        report = L3G6Reporter().build_report(collapse, anchors, model, stability)
        payload = report.to_dict()
        self.assertTrue(payload["metadata"]["observational_only"])
        self.assertTrue(payload["metadata"]["collapse_not_controlled"])
        self.assertEqual(report.explanation_mode, "hybrid")

    def test_derive_collapse_system_state(self):
        state = derive_collapse_system_state(
            {"risk_signals": {"self_description_looping": 0.2}, "observer_model": {"interpretation_stability_score": 0.7}},
            {"ontology_drift_index": 0.3, "boundary_consistency": 0.8, "layer_system_stability": 0.75},
        )
        self.assertIn("reflexivity_coherence", state)
        self.assertAlmostEqual(state["reflexivity_coherence"], 0.7)

    def test_assemble_g6_from_payloads(self):
        g5 = {
            "ontology_drift_index": 0.2,
            "layer_system_stability": 0.8,
            "boundary_consistency": 0.7,
            "integrity_violations": [],
            "ontology_drifts": [],
        }
        state = derive_collapse_system_state({"observer_model": {}}, g5)
        report = assemble_g6(g5, state)
        self.assertIn(report.collapse_severity_band, ("none", "moderate", "elevated", "critical"))
        self.assertEqual(report.explanation_mode, "layered")

    def test_build_l3_g6_synthetic(self):
        report = build_l3_g6_report(
            {"type": "governance_attempt", "target": "runtime", "confidence": 0.9},
            use_l2_coupling=False,
        )
        payload = report.to_dict()
        self.assertIn("non_layered_model", payload)
        self.assertIn(payload["explanation_mode"], ("layered", "hybrid", "field"))
        self.assertTrue(payload["metadata"]["shadow_only_interpretation"])

    def test_build_l3_g6_from_l2_coupling(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            now = datetime.now(timezone.utc)
            for i in range(3):
                ts = (now - timedelta(days=2 - i)).isoformat()
                with open(os.path.join(obs, "ecology_metrics.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": ts, "acd": 0.3, "odc": 0.2, "rre": 0.6, "cpx": 0.5, "cpi": 0.2}) + "\n")
                with open(os.path.join(obs, "singularity_metrics.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": ts, "ncr": 0.2, "cea": 0.5, "rsci": 0.6}) + "\n")
                with open(os.path.join(obs, "gtbs_shadow.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(
                        json.dumps(
                            {"timestamp": ts, "proposal_vs_reality": {"proposal_reality_divergence": 0.3, "key_jaccard": 0.6}}
                        )
                        + "\n"
                    )
            report = build_l3_g6_report(base_dir=tmp, window_days=7)
            self.assertGreater(report.explainability_retention_metric, 0.0)


if __name__ == "__main__":
    unittest.main()

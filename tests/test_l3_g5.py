"""L3-G5 meta-meta governance boundary tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import build_l3_g5_report
from core.governance.l3.meta_meta import (
    BoundaryConstructor,
    LayerGenesisEngine,
    MetaLayerEngine,
    OntologyDriftAnalyzer,
)
from core.governance.l3.meta_meta.l3g5_report import L3G5Reporter


class TestL3G5(unittest.TestCase):
    def test_layer_genesis_no_execution_allowed(self):
        engine = LayerGenesisEngine()
        layers = engine.canonical_layers()
        violations = engine.validate_layer_integrity(layers)
        self.assertEqual(violations, [])
        rules = engine.generate_layer_rules()
        self.assertEqual(rules["L3-G5"], "meta_layer_definition_only")

    def test_boundary_constructor(self):
        layers = LayerGenesisEngine().canonical_layers()
        boundaries = BoundaryConstructor().construct(layers)
        self.assertEqual(len(boundaries), len(layers) - 1)
        consistency = BoundaryConstructor().evaluate_consistency(boundaries)
        self.assertGreater(consistency, 0.0)
        self.assertLessEqual(consistency, 1.0)

    def test_ontology_drift_monotonic_depth(self):
        layers = LayerGenesisEngine().canonical_layers()
        index, drifts = OntologyDriftAnalyzer().compute_drift(layers)
        self.assertGreater(index, 0.0)
        self.assertEqual(len(drifts), len(layers) - 1)

    def test_meta_layer_engine_classify(self):
        layers = LayerGenesisEngine().canonical_layers()
        boundaries = BoundaryConstructor().construct(layers)
        engine = MetaLayerEngine()
        metrics = engine.run(layers, boundaries, 0.3, boundary_consistency=0.8)
        state = engine.classify(metrics)
        self.assertIn(
            state,
            ("stable_meta_governance", "metastable_meta_governance", "unstable_meta_structure", "fragmenting_governance"),
        )

    def test_l3g5_report_standalone(self):
        report = L3G5Reporter().build_report({"meta_governance_state": "stable", "reflexivity_score": 0.3})
        payload = report.to_dict()
        self.assertTrue(payload["metadata"]["meta_layer_definition_only"])
        self.assertGreater(payload["self_referential_depth"], 0)

    def test_build_l3_g5_synthetic(self):
        report = build_l3_g5_report(
            {"type": "governance_attempt", "target": "runtime", "confidence": 0.9},
            use_l2_coupling=False,
        )
        payload = report.to_dict()
        self.assertIn("layer_genesis_rules", payload)
        self.assertIn(payload["meta_governance_state"], (
            "stable_meta_governance",
            "metastable_meta_governance",
            "unstable_meta_structure",
            "fragmenting_governance",
        ))

    def test_build_l3_g5_from_l2_coupling(self):
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
            report = build_l3_g5_report(base_dir=tmp, window_days=7)
            self.assertGreater(report.layer_system_stability, 0.0)


if __name__ == "__main__":
    unittest.main()

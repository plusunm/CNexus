"""L3-G7 layerless kernel tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import build_l3_g7_report
from core.governance.l3.g7 import (
    G7_META_CONSTRAINTS,
    LayerlessInterpreter,
    LayerlessKernelEngine,
    build_l3_g7_report as assemble_g7,
    derive_l3_bundle_from_stack,
)
from core.governance.l3.g7.types import FieldState, LayerlessKernelState


class TestL3G7(unittest.TestCase):
    def test_kernel_projects_field_only(self):
        state = LayerlessKernelEngine().project_from_l3_stack(
            {
                "coupling_strength": 0.8,
                "drift_index": 0.2,
                "stability_score": 0.75,
                "attractors": [{"id": "a1", "strength": 0.9, "basin": "stable_attractor"}],
                "trace_events": [{"timestamp": 1.0, "signal_type": "observation", "payload": {"x": 1}}],
            }
        )
        self.assertEqual(state.metadata["layer_abstraction"], "NONE")
        self.assertTrue(state.metadata["no_layer_model"])
        self.assertAlmostEqual(state.field.intensity, 0.8)

    def test_interpreter_stable_regime(self):
        state = LayerlessKernelState(
            field=FieldState(intensity=0.6, entropy=0.2, coherence=0.85),
            attractors=[],
            traces=[],
        )
        interp = LayerlessInterpreter().interpret(state)
        self.assertEqual(interp["regime"], "stable_coherence_field")
        self.assertTrue(interp["meta"]["no_layers"])

    def test_interpreter_high_entropy_regime(self):
        from core.governance.l3.g7.types import TraceEvent

        state = LayerlessKernelState(
            field=FieldState(intensity=0.4, entropy=0.85, coherence=0.3),
            attractors=[],
            traces=[
                TraceEvent(1.0, "observation", {}),
                TraceEvent(2.0, "observation", {}),
                TraceEvent(3.0, "observation", {}),
            ],
        )
        interp = LayerlessInterpreter().interpret(state)
        self.assertEqual(interp["regime"], "high_entropy_field")
        self.assertEqual(interp["trace_density"], 3)

    def test_derive_bundle_from_stack(self):
        bundle = derive_l3_bundle_from_stack(
            g3={
                "stability": {"entropy": 0.3},
                "attractor_map": {"attractors": [{"node": "n1", "depth": 0.8, "type": "stable_attractor"}]},
                "power_field": {"nodes": [{"id": "n1", "strength": 0.7}]},
            },
            g5={"ontology_drift_index": 0.25, "boundary_consistency": 0.8, "layer_system_stability": 0.7},
            g6={"explainability_retention_metric": 0.6, "active_anchors": [{"anchor_id": "causal", "stability_score": 0.5}]},
            g4={"risk_signals": {"self_description_looping": 0.1}, "observer_model": {"interpretation_stability_score": 0.7}},
        )
        self.assertIn("coupling_strength", bundle)
        self.assertGreaterEqual(len(bundle["attractors"]), 2)
        self.assertGreater(len(bundle["trace_events"]), 0)

    def test_assemble_g7_report(self):
        report = assemble_g7(
            {
                "coupling_strength": 0.5,
                "drift_index": 0.4,
                "stability_score": 0.6,
                "attractors": [],
                "trace_events": [],
            }
        )
        payload = report.to_dict()
        self.assertEqual(payload["interpretation_mode"], "non-layered")
        for key in G7_META_CONSTRAINTS:
            self.assertTrue(payload["metadata"].get(key))

    def test_build_l3_g7_synthetic(self):
        report = build_l3_g7_report(
            {"type": "governance_attempt", "target": "runtime", "confidence": 0.9},
            use_l2_coupling=False,
        )
        payload = report.to_dict()
        self.assertIn("field", payload)
        self.assertIn("interpretation", payload)
        self.assertTrue(payload["metadata"]["field_only_ontology"])

    def test_build_l3_g7_from_l2_coupling(self):
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
            report = build_l3_g7_report(base_dir=tmp, window_days=7)
            self.assertGreater(report.attractors, 0)


if __name__ == "__main__":
    unittest.main()

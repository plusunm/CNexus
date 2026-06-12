"""L3-G3 power field optimization tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import build_l3_g3_report
from core.governance.l3.field_optimization import (
    AttractorMap,
    FieldOptimizer,
    PowerField,
    PowerFieldBuilder,
    PowerNode,
    PowerEdge,
    StabilitySolver,
)
from core.governance.l3.field_optimization.l3g3_report import L3G3Reporter


def _sample_field() -> PowerField:
    return PowerField(
        nodes={
            "authority_boundary": PowerNode("authority_boundary", 1.0, 0.0),
            "semantic_layer": PowerNode("semantic_layer", 0.6, 0.4),
            "system_core": PowerNode("system_core", 0.5, 0.5),
        },
        edges=[
            PowerEdge("authority_boundary", "system_core", 0.6),
            PowerEdge("semantic_layer", "system_core", 0.3),
        ],
    )


class TestL3G3(unittest.TestCase):
    def test_stability_solver(self):
        landscape = StabilitySolver().analyze(_sample_field())
        self.assertGreaterEqual(landscape.entropy, 0.0)
        self.assertGreaterEqual(landscape.lock_in_regions, 0.0)
        self.assertLessEqual(landscape.lock_in_regions, 1.0)

    def test_attractor_map(self):
        result = AttractorMap().compute(_sample_field())
        self.assertIn("attractors", result)
        self.assertGreaterEqual(result["dominance"], 0.0)

    def test_field_optimizer_simulation_only(self):
        field = _sample_field()
        landscape = StabilitySolver().analyze(field)
        opt = FieldOptimizer().optimize(field, landscape)
        self.assertIn("shadow", opt.note.lower())
        self.assertTrue(any("simulated" in s["simulated_adjustment_label"] for s in opt.simulated_optimization))

    def test_l3g3_reporter_phase(self):
        field = _sample_field()
        landscape = StabilitySolver().analyze(field)
        attractors = AttractorMap().compute(field)
        opt = FieldOptimizer().optimize(field, landscape)
        report = L3G3Reporter().render(landscape, attractors, opt, power_field=field)
        self.assertIn(report.system_phase, ("stable field", "over-constrained field", "metastable field", "diffuse field"))
        self.assertTrue(report.metadata["no_execution"])

    def test_build_l3_g3_synthetic(self):
        report = build_l3_g3_report(
            {"type": "governance_attempt", "target": "runtime", "confidence": 0.9},
            use_l2_coupling=False,
        )
        payload = report.to_dict()
        self.assertIn("stability", payload)
        self.assertIn("optimization", payload)
        self.assertIn("power_field", payload)

    def test_power_field_builder_from_g1_g2(self):
        from core.governance.l3.constraint_graph import ConstraintGraphBuilder
        from core.governance.l3.execution_shadow import ConstraintExecutionShadowEngine, ExecutionScenario

        graph = ConstraintGraphBuilder().build_from_l3_signals(
            {"type": "interpretation", "intensity": 0.5}
        )
        engine = ConstraintExecutionShadowEngine()
        shadow = engine.simulate(
            ExecutionScenario("runtime_safety", 0.7, "L1"),
            {"stability": 0.7, "coherence": 0.6},
        )
        field = PowerFieldBuilder().build(graph, [shadow])
        self.assertGreater(len(field.nodes), 0)
        self.assertGreater(len(field.edges), 0)

    def test_build_l3_g3_from_l2_coupling(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            now = datetime.now(timezone.utc)
            for i in range(3):
                ts = (now - timedelta(days=2 - i)).isoformat()
                with open(os.path.join(obs, "ecology_metrics.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(
                        json.dumps({"ts": ts, "acd": 0.3, "odc": 0.2, "rre": 0.6, "cpx": 0.5, "cpi": 0.2})
                        + "\n"
                    )
                with open(os.path.join(obs, "singularity_metrics.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": ts, "ncr": 0.2, "cea": 0.5, "rsci": 0.6}) + "\n")
                with open(os.path.join(obs, "gtbs_shadow.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(
                        json.dumps(
                            {
                                "timestamp": ts,
                                "proposal_vs_reality": {"proposal_reality_divergence": 0.3, "key_jaccard": 0.6},
                            }
                        )
                        + "\n"
                    )
            report = build_l3_g3_report(base_dir=tmp, window_days=7)
            self.assertIn(report.system_phase, ("stable field", "over-constrained field", "metastable field", "diffuse field"))


if __name__ == "__main__":
    unittest.main()

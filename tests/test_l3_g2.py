"""L3-G2 constraint execution shadow tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import build_l3_g2_report
from core.governance.l3.execution_shadow import (
    ConstraintExecutionShadowEngine,
    ExecutionScenario,
    build_execution_scenarios,
    derive_system_state,
)
from core.governance.l3.execution_shadow.impact_model import ImpactModel
from core.governance.l3.execution_shadow.l3g2_report import L3G2Reporter
from core.governance.l3.execution_shadow.state_projection import StateProjection


class TestL3G2(unittest.TestCase):
    def test_impact_model_monotonic_with_strength(self):
        model = ImpactModel()
        state = {"stability": 0.8, "coherence": 0.75}
        low = model.estimate(state, ExecutionScenario("runtime_safety", 0.3, "L1"))
        high = model.estimate(state, ExecutionScenario("runtime_safety", 0.9, "L1"))
        self.assertLess(high.stability_delta, low.stability_delta)
        self.assertGreaterEqual(high.risk_amplification, low.risk_amplification)

    def test_state_projection_no_mutation(self):
        state = {"stability": 0.8, "coherence": 0.75}
        projection = StateProjection()
        impact = ImpactModel().estimate(
            state, ExecutionScenario("authority_boundary", 0.6, "L2")
        )
        original = dict(state)
        projected = projection.apply_to_system_state(state, impact)
        self.assertEqual(state, original)
        self.assertNotEqual(projected["stability"], original["stability"])

    def test_shadow_engine_responses(self):
        engine = ConstraintExecutionShadowEngine()
        state = {"stability": 0.5, "coherence": 0.4}
        unstable = engine.simulate(
            ExecutionScenario("runtime_safety", 1.0, "L1"), state
        )
        self.assertIn(
            unstable.system_response,
            (
                "system instability likely under enforcement",
                "semantic fragmentation under constraint pressure",
                "stable under hypothetical enforcement",
            ),
        )
        self.assertIn("L1", unstable.layer_projections)

    def test_build_execution_scenarios_from_governance_signal(self):
        scenarios = build_execution_scenarios(
            {"type": "governance_attempt", "intensity": 0.8}, g1_violation_score=0.9
        )
        self.assertGreaterEqual(len(scenarios), 4)
        ids = [s.constraint_id for s in scenarios]
        self.assertIn("runtime_safety", ids)

    def test_l3g2_report_metadata(self):
        engine = ConstraintExecutionShadowEngine()
        state = {"stability": 0.8, "coherence": 0.75}
        shadow = engine.simulate(
            ExecutionScenario("semantic_layer", 0.5, "L2"), state
        )
        report = L3G2Reporter().render([shadow], baseline_state=state)
        payload = report.to_dict()
        self.assertTrue(payload["metadata"]["no_state_mutation"])
        self.assertIn("S17", payload["metadata"]["principles"])

    def test_build_l3_g2_synthetic(self):
        report = build_l3_g2_report(
            {"type": "governance_attempt", "target": "runtime", "confidence": 0.9},
            use_l2_coupling=False,
        )
        self.assertGreater(len(report.scenario_summaries), 0)
        self.assertIn(report.risk_observation, ("low_observation", "medium_observation", "high_observation"))

    def test_build_l3_g2_from_l2_coupling(self):
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
            report = build_l3_g2_report(base_dir=tmp, window_days=7)
            self.assertGreater(len(report.shadow_states), 0)
            self.assertIn("baseline_state", report.to_dict())


if __name__ == "__main__":
    unittest.main()

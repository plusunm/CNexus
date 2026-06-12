"""L3-G1 constraint graph + arbitration tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import (
    ArbitrationEngine,
    ConstraintGraphBuilder,
    ViolationScorer,
    build_l3_g1_report,
)
from core.governance.l3.constraint_model import ConstraintType


class TestL3G1(unittest.TestCase):
    def test_constraint_graph_build(self):
        builder = ConstraintGraphBuilder()
        graph = builder.build_from_l3_signals({"type": "interpretation", "intensity": 0.2})
        self.assertEqual(len(graph.nodes), 4)
        self.assertGreaterEqual(len(graph.edges), 3)
        self.assertEqual(graph.nodes["authority_boundary"].type, ConstraintType.AUTHORITY)

    def test_arbitration_safety_wins_on_governance_attempt(self):
        builder = ConstraintGraphBuilder()
        graph = builder.build_from_l3_signals(
            {"type": "governance_attempt", "target": "runtime", "intensity": 0.9}
        )
        engine = ArbitrationEngine()
        decision = engine.simulate(graph, {"type": "governance_attempt", "intensity": 0.9})
        self.assertEqual(decision.precedence_label, "runtime_safety")
        self.assertGreaterEqual(decision.confidence_metric, 0.8)

    def test_arbitration_authority_over_semantic_weak(self):
        builder = ConstraintGraphBuilder()
        graph = builder.build_from_l3_signals({"type": "interpretation", "intensity": 0.0})
        engine = ArbitrationEngine()
        decision = engine.simulate(graph, {"type": "interpretation", "intensity": 0.0})
        self.assertIn(decision.precedence_label, ("authority_boundary", "runtime_safety"))

    def test_violation_scorer_monotonicity(self):
        scorer = ViolationScorer()
        low = scorer.score({"type": "observation"})
        mid = scorer.score({"type": "governance_attempt"})
        high = scorer.score(
            {"type": "governance_attempt", "target": "runtime", "confidence": 0.9}
        )
        self.assertLess(low, mid)
        self.assertLessEqual(mid, high)
        self.assertLessEqual(high, 1.0)

    def test_risk_classification(self):
        report = build_l3_g1_report(
            {
                "type": "governance_attempt",
                "target": "runtime",
                "confidence": 0.95,
            }
        )
        self.assertIn(report.risk_observation, ("low_observation", "medium_observation", "high_observation"))
        self.assertGreater(report.violation_score, 0.5)
        payload = report.to_dict()
        self.assertTrue(payload["non_actionable"])
        self.assertEqual(payload["role"], "observational_only")
        self.assertTrue(payload["metadata"]["simulation_only"])
        self.assertTrue(payload["metadata"]["no_enforcement"])

    def test_build_l3_g1_from_l2_coupling(self):
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
            report = build_l3_g1_report(base_dir=tmp, window_days=7)
            self.assertIn("precedence_label", report.simulation_result)
            self.assertGreater(report.graph_summary["nodes"], 0)


if __name__ == "__main__":
    unittest.main()

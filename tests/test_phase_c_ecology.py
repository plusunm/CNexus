"""Phase C continuity ecology tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.ecology.collector import EcologyMetricsCollector
from core.governance.ecology.metrics import EcologyMetricsEngine
from core.governance.ecology.monthly_report import EcologyObservatoryEngine


def _shadow_rows(days: int = 30):
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(days):
        ts = (now - timedelta(days=i)).isoformat()
        rows.append(
            {
                "type": "gtbs_shadow_observation",
                "timestamp": ts,
                "context": {
                    "phase": "interaction" if i % 2 == 0 else "capture",
                    "grounding_event_id": f"g{i}" if i % 4 != 0 else None,
                    "capture_id": f"m{i}",
                    "layer": "belief" if i >= 20 else "episodic",
                },
                "proposal": {
                    "source": "interaction",
                    "target_stores": ["storage", "narrative"],
                    "proposed_keys": ["memory", "narrative"],
                },
                "state_diff": {
                    "added_keys": ["memory", "narrative"] if i >= 15 else ["memory"],
                    "removed_keys": [],
                    "divergence_score": 2 if i >= 15 else 1,
                },
                "store_divergence": {
                    "by_store": {
                        "storage": 1.0,
                        "narrative": 1.0 if i >= 15 else 0.0,
                        "reality": 0.0,
                        "belief": 0.5 if i >= 22 else 0.0,
                        "self_model": 0.0,
                        "working_self": 0.3 if i >= 25 else 0.0,
                        "cognitive": 0.0,
                    },
                    "total": 2.0 if i >= 15 else 1.0,
                },
                "proposal_vs_reality": {
                    "key_jaccard": 0.75 if i < 15 else 0.45,
                    "proposal_reality_divergence": 0.25 if i < 15 else 0.55,
                    "cross_store_consistency": 0.9 - (i / days) * 0.3,
                    "unexpected_changes": ["narrative"] if i >= 15 else [],
                    "changed_stores": ["storage", "narrative"] if i >= 15 else ["storage"],
                },
            }
        )
    return rows


class TestPhaseCEcologyMetrics(unittest.TestCase):
    def test_five_metrics_in_range(self):
        snap = EcologyMetricsEngine(".").compute(_shadow_rows())
        for key in ("acd", "odc", "rre", "cpi", "cpx"):
            val = getattr(snap, key)
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)
        self.assertTrue(snap.instrumentation_only)

    def test_collector_independent_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            with open(os.path.join(obs, "gtbs_shadow.jsonl"), "w", encoding="utf-8") as fh:
                for r in _shadow_rows(10):
                    fh.write(json.dumps(r) + "\n")

            collector = EcologyMetricsCollector(tmp)
            snap = collector.record_snapshot(tmp)
            rows = collector.read_all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["type"], "ecology_metrics_snapshot")
            self.assertIn("acd", rows[0])
            self.assertTrue(rows[0]["non_actionable"])
            self.assertIsNotNone(snap.acd)


class TestPhaseCMonthlyReport(unittest.TestCase):
    def test_monthly_ecology_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            with open(os.path.join(obs, "gtbs_shadow.jsonl"), "w", encoding="utf-8") as fh:
                for r in _shadow_rows(30):
                    fh.write(json.dumps(r) + "\n")

            engine = EcologyObservatoryEngine(tmp)
            engine.record_snapshot()

            now = datetime.now(timezone.utc)
            history = []
            for m in range(3):
                ts = (now - timedelta(days=m * 30)).isoformat()
                history.append(
                    {
                        "type": "ecology_metrics_snapshot",
                        "ts": ts,
                        "acd": 0.3 + m * 0.05,
                        "odc": 0.2 + m * 0.06,
                        "rre": 0.65 - m * 0.04,
                        "cpi": 0.25 + m * 0.03,
                        "cpx": 0.28 + m * 0.04,
                    }
                )

            report = engine.generate_monthly_report(history).to_dict()
            self.assertTrue(report["instrumentation_only"])
            self.assertTrue(report["no_enforcement"])
            self.assertIn("attractor_competition_map", report)
            self.assertIn("openness_decay_trend", report)
            self.assertIn("reality_recovery_elasticity_trend", report)
            self.assertIn("contradiction_persistence_distribution", report)
            self.assertIn("continuity_pressure_evolution", report)
            self.assertIn("ecosystem_stabilization_summary", report)


if __name__ == "__main__":
    unittest.main()

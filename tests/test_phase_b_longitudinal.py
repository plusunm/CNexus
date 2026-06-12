"""Phase B longitudinal singularity metrics tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.singularity.collector import SingularityMetricsCollector
from core.governance.singularity.longitudinal_report import LongitudinalStudyEngine
from core.governance.singularity.metrics import SingularityMetricsEngine


def _shadow_rows(days: int = 14):
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
                    "grounding_event_id": f"g{i}" if i % 3 != 0 else None,
                    "layer": "episodic",
                    "capture_id": f"m{i}",
                },
                "proposal": {
                    "source": "interaction",
                    "target_stores": ["storage", "narrative"],
                    "proposed_keys": ["memory", "narrative"],
                },
                "state_diff": {
                    "added_keys": ["memory", "narrative"] if i >= 7 else ["memory"],
                    "removed_keys": [],
                    "divergence_score": 2 if i >= 7 else 1,
                },
                "store_divergence": {
                    "by_store": {
                        "storage": 1.0,
                        "narrative": 1.0 if i >= 7 else 0.0,
                        "reality": 0.0,
                        "belief": 0.5 if i >= 10 else 0.0,
                        "self_model": 0.0,
                        "working_self": 0.5 if i >= 12 else 0.0,
                        "cognitive": 0.0,
                    },
                    "total": 2.5 if i >= 10 else 1.0,
                },
                "proposal_vs_reality": {
                    "key_jaccard": 0.7 if i < 7 else 0.4,
                    "proposal_reality_divergence": 0.3 if i < 7 else 0.6,
                    "cross_store_consistency": 0.85 if i < 7 else 0.5,
                    "unexpected_changes": ["narrative"] if i >= 7 else [],
                    "changed_stores": ["storage", "narrative"] if i >= 7 else ["storage"],
                },
            }
        )
    return rows


class TestPhaseBSingularityMetrics(unittest.TestCase):
    def test_ncr_cea_rsci_in_range(self):
        rows = _shadow_rows()
        engine = SingularityMetricsEngine(".")
        snap = engine.compute(rows)
        self.assertGreaterEqual(snap.ncr, 0.0)
        self.assertLessEqual(snap.ncr, 1.0)
        self.assertGreaterEqual(snap.cea, 0.0)
        self.assertLessEqual(snap.cea, 1.0)
        self.assertGreaterEqual(snap.rsci, 0.0)
        self.assertLessEqual(snap.rsci, 1.0)
        self.assertTrue(snap.instrumentation_only)

    def test_collector_independent_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            with open(os.path.join(obs, "gtbs_shadow.jsonl"), "w", encoding="utf-8") as fh:
                for r in _shadow_rows(7):
                    fh.write(json.dumps(r) + "\n")

            collector = SingularityMetricsCollector(tmp)
            snap = collector.record_snapshot(tmp)
            self.assertTrue(collector.path.exists())
            rows = collector.read_all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["type"], "singularity_metrics_snapshot")
            self.assertIn("ncr", rows[0])
            self.assertTrue(rows[0]["non_actionable"])


class TestPhaseBWeeklyReport(unittest.TestCase):
    def test_weekly_longitudinal_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            shadow_path = os.path.join(obs, "gtbs_shadow.jsonl")
            with open(shadow_path, "w", encoding="utf-8") as fh:
                for r in _shadow_rows(14):
                    fh.write(json.dumps(r) + "\n")

            engine = LongitudinalStudyEngine(tmp)
            engine.record_snapshot()

            now = datetime.now(timezone.utc)
            history = []
            for w in range(3):
                ts = (now - timedelta(weeks=w)).isoformat()
                history.append(
                    {
                        "type": "singularity_metrics_snapshot",
                        "ts": ts,
                        "prci": 0.7 - w * 0.05,
                        "ncr": 0.2 + w * 0.05,
                        "cea": 0.6 - w * 0.03,
                        "rsci": 0.15 + w * 0.04,
                    }
                )

            report = engine.generate_weekly_report(history).to_dict()
            self.assertTrue(report["instrumentation_only"])
            self.assertTrue(report["no_enforcement"])
            self.assertIn("prci_trend", report)
            self.assertIn("ncr_trend", report)
            self.assertIn("cea_trend", report)
            self.assertIn("rsci_trend", report)
            self.assertIn("divergence_burst_distribution", report)
            self.assertIn("reconstruction_drift_accumulation", report)
            self.assertIn("attractor_stabilization_map", report)
            self.assertIn("singularity_risk_observations", report)


if __name__ == "__main__":
    unittest.main()

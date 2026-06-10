"""Phase A analytics tests — instrumentation-only modules."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.continuity.trajectory_report import TrajectoryObservabilityEngine
from core.governance.gtbs.divergence_analysis import DivergenceAnalyzer
from core.governance.gtbs.gatekeeper import RuntimeGatekeeper
from core.governance.phase_a.landscape import PhaseALandscapeMapper
from core.governance.reconstruction.drift_audit import ReconstructionDriftAuditor
from core.governance.reconstruction.frozen_anchor import FrozenEpisodicAnchorRegistry
from core.governance.shaping.attribution import ShapingAttributor


def _sample_shadow_rows():
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(5):
        ts = (now - timedelta(days=i)).isoformat()
        rows.append(
            {
                "type": "gtbs_shadow_observation",
                "timestamp": ts,
                "context": {
                    "phase": "interaction" if i % 2 == 0 else "capture",
                    "grounding_event_id": f"g{i}",
                    "layer": "episodic",
                },
                "proposal": {
                    "source": "interaction",
                    "target_stores": ["storage", "cognitive"],
                    "proposed_keys": ["memory", "working_self"],
                },
                "state_diff": {
                    "added_keys": ["memory"] if i < 3 else ["memory", "narrative"],
                    "removed_keys": [],
                    "divergence_score": 1 if i < 3 else 2,
                },
                "store_divergence": {
                    "by_store": {
                        "storage": 1.0,
                        "narrative": 1.0 if i >= 3 else 0.0,
                        "reality": 0.0,
                        "belief": 0.0,
                        "self_model": 0.0,
                        "working_self": 0.0,
                        "cognitive": 0.0,
                    },
                    "top_store": "narrative" if i >= 3 else "storage",
                    "total": 2.0 if i >= 3 else 1.0,
                },
                "proposal_vs_reality": {
                    "key_jaccard": 0.8 if i < 3 else 0.5,
                    "proposal_reality_divergence": 0.2 if i < 3 else 0.5,
                    "cross_store_consistency": 0.9 if i < 3 else 0.6,
                    "unexpected_changes": ["narrative"] if i >= 3 else [],
                    "changed_stores": ["storage"] if i < 3 else ["storage", "narrative"],
                },
            }
        )
    return rows


class TestPhaseADivergenceAnalysis(unittest.TestCase):
    def test_prci_and_ranking(self):
        analyzer = DivergenceAnalyzer(".")
        report = analyzer.analyze(_sample_shadow_rows())
        self.assertEqual(report.observations, 5)
        self.assertGreater(report.prci, 0.0)
        self.assertLessEqual(report.prci, 1.0)
        self.assertIn("histogram", report.divergence_distribution)
        self.assertTrue(report.store_divergence_ranking[0]["divergence_total"] >= 0)

    def test_drift_trend_7d(self):
        report = DivergenceAnalyzer(".").analyze(_sample_shadow_rows())
        self.assertGreaterEqual(len(report.drift_trend_7d), 1)

    def test_gatekeeper_store_divergence(self):
        gk = RuntimeGatekeeper()
        out = gk.observe_runtime_event(
            {"memory": [], "narrative": []},
            {"memory": [{"id": "1"}], "narrative": [{"s": "x"}]},
            proposal={"target_stores": ["storage"], "proposed_keys": ["memory"]},
        )
        self.assertIn("store_divergence", out)
        self.assertIn("cross_store_consistency", out["proposal_vs_reality"])


class TestPhaseAShaping(unittest.TestCase):
    def test_attribution_sums_approx_one(self):
        report = ShapingAttributor().analyze(_sample_shadow_rows())
        total = sum(report.attribution.values())
        self.assertAlmostEqual(total, 1.0, places=2)
        self.assertIn(report.dominant_source, report.attribution)


class TestPhaseAReconstruction(unittest.TestCase):
    def test_rrs_and_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = _sample_shadow_rows()
            obs = tmp + "/observability"
            os.makedirs(obs, exist_ok=True)
            with open(os.path.join(obs, "gtbs_shadow.jsonl"), "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")

            drift = ReconstructionDriftAuditor(tmp).analyze()
            self.assertGreaterEqual(drift.retroactive_reshape_score, 0.0)
            self.assertTrue(drift.replay_immutable)

            registry = FrozenEpisodicAnchorRegistry(tmp)
            recorded = registry.scan_and_record(rows)
            self.assertGreater(len(recorded), 0)
            self.assertTrue(registry.path.exists())


class TestPhaseATrajectory(unittest.TestCase):
    def test_trajectory_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            with open(os.path.join(obs, "gtbs_shadow.jsonl"), "w", encoding="utf-8") as fh:
                for r in _sample_shadow_rows():
                    fh.write(json.dumps(r) + "\n")

            report = TrajectoryObservabilityEngine(tmp).build()
            self.assertGreaterEqual(report.reality_coupling_score, 0.0)
            self.assertTrue(report.top_active_attractors)
            self.assertTrue(report.instrumentation_only)


class TestPhaseALandscape(unittest.TestCase):
    def test_full_landscape_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            with open(os.path.join(obs, "gtbs_shadow.jsonl"), "w", encoding="utf-8") as fh:
                for r in _sample_shadow_rows():
                    fh.write(json.dumps(r) + "\n")

            bundle = PhaseALandscapeMapper(tmp).generate(record_anchors=True)
            payload = bundle.to_dict()
            self.assertTrue(payload["instrumentation_only"])
            self.assertTrue(payload["no_enforcement"])
            self.assertEqual(payload["north_star"], "Reality-Governed Continuity")
            self.assertIn("divergence_landscape", payload)
            self.assertIn("shaping_attribution", payload)


if __name__ == "__main__":
    unittest.main()

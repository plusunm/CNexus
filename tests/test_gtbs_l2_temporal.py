"""GTBS-L2 v0.2 temporal semantic continuity tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l2.loader import load_temporal_window
from core.governance.l2.render import GTBSL2Renderer
from core.governance.l2.temporal.trajectory_synthesizer import TrajectorySynthesizer
from core.governance.l2.temporal.window_builder import build_temporal_window


def _write_temporal_fixtures(tmp: str, days: int = 5):
    obs = os.path.join(tmp, "observability")
    os.makedirs(obs, exist_ok=True)
    now = datetime.now(timezone.utc)

    ecology_lines = []
    singularity_lines = []
    shadow_lines = []
    for i in range(days):
        ts = (now - timedelta(days=days - 1 - i)).isoformat()
        odc = 0.2 + i * 0.08
        ecology_lines.append(
            json.dumps(
                {
                    "ts": ts,
                    "acd": 0.3 + i * 0.05,
                    "odc": odc,
                    "rre": 0.6 - i * 0.03,
                    "cpx": 0.25 + i * 0.06,
                    "cpi": 0.2,
                }
            )
        )
        singularity_lines.append(
            json.dumps(
                {"ts": ts, "ncr": 0.15 + i * 0.07, "cea": 0.55, "rsci": 0.1 + i * 0.05}
            )
        )
        shadow_lines.append(
            json.dumps(
                {
                    "timestamp": ts,
                    "proposal_vs_reality": {
                        "proposal_reality_divergence": 0.2 + i * 0.05,
                        "key_jaccard": 0.8 - i * 0.06,
                        "cross_store_consistency": 0.85 - i * 0.05,
                    },
                    "context": {"phase": "interaction", "grounding_event_id": f"g{i}"},
                }
            )
        )

    with open(os.path.join(obs, "ecology_metrics.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(ecology_lines) + "\n")
    with open(os.path.join(obs, "singularity_metrics.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(singularity_lines) + "\n")
    with open(os.path.join(obs, "gtbs_shadow.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(shadow_lines) + "\n")


class TestGTBSL2Temporal(unittest.TestCase):
    def test_build_temporal_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_temporal_fixtures(tmp, days=5)
            window = build_temporal_window(tmp, window_days=7)
            self.assertGreaterEqual(window.snapshot_count, 1)
            self.assertIn("divergence_trend", window.aggregated)
            self.assertIn("ecology_shift", window.aggregated)

    def test_trajectory_synthesizer_three_tracks(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_temporal_fixtures(tmp, days=4)
            window = load_temporal_window(tmp, window_days=7)
            stories = TrajectorySynthesizer().synthesize(window)
            self.assertIn("drift_story", stories)
            self.assertIn("stability_story", stories)
            self.assertIn("pressure_story", stories)

    def test_render_temporal_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_temporal_fixtures(tmp, days=4)
            window = load_temporal_window(tmp, window_days=7)
            report = GTBSL2Renderer().render_temporal(window)
            payload = report.to_dict()
            self.assertEqual(payload["narrative_version"], "L2_v0.2")
            self.assertTrue(payload["metadata"]["no_temporal_governance"])
            self.assertIn("drift", payload["temporal_summaries"])
            self.assertIn("openness_delta", payload["trend_signals"])

    def test_interpret_temporal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_temporal_fixtures(tmp, days=3)
            window = load_temporal_window(tmp, window_days=7)
            narratives = GTBSL2Renderer().interpreter.interpret_temporal(window)
            self.assertEqual(len(narratives), 3)


if __name__ == "__main__":
    unittest.main()

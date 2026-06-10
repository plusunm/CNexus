"""GTBS-L2 v0.3 cross-stream fusion tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l2.fusion import build_fusion_report
from core.governance.l2.fusion.semantic_coupling_engine import SemanticCouplingEngine
from core.governance.l2.fusion.cross_stream_builder import build_cross_stream_field
from core.governance.l2.render import GTBSL2Renderer


def _write_fusion_fixtures(tmp: str, days: int = 5):
    obs = os.path.join(tmp, "observability")
    os.makedirs(obs, exist_ok=True)
    now = datetime.now(timezone.utc)
    ecology, singularity, shadow = [], [], []
    for i in range(days):
        ts = (now - timedelta(days=days - 1 - i)).isoformat()
        ecology.append(json.dumps({"ts": ts, "acd": 0.3 + i * 0.06, "odc": 0.2 + i * 0.07, "rre": 0.6, "cpx": 0.25 + i * 0.08, "cpi": 0.2}))
        singularity.append(json.dumps({"ts": ts, "ncr": 0.15 + i * 0.08, "cea": 0.55, "rsci": 0.1 + i * 0.06}))
        shadow.append(json.dumps({"timestamp": ts, "proposal_vs_reality": {"proposal_reality_divergence": 0.2 + i * 0.06, "key_jaccard": 0.75 - i * 0.05}}))
    for name, lines in [("ecology_metrics.jsonl", ecology), ("singularity_metrics.jsonl", singularity), ("gtbs_shadow.jsonl", shadow)]:
        with open(os.path.join(obs, name), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


class TestGTBSL2Fusion(unittest.TestCase):
    def test_coupling_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fusion_fixtures(tmp, days=5)
            field = build_cross_stream_field(tmp, window_days=7)
            analyzed = SemanticCouplingEngine().analyze(field)
            m = analyzed.coupling_matrix
            self.assertGreaterEqual(m.global_coupling_index, 0.0)
            self.assertLessEqual(m.global_coupling_index, 1.0)
            self.assertIn("divergence_x_ncr", analyzed.coupling_signals)

    def test_fusion_report_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fusion_fixtures(tmp, days=4)
            report = build_fusion_report(tmp, window_days=7)
            payload = report.to_dict()
            self.assertEqual(payload["narrative_version"], "L2_v0.3")
            self.assertIn("drift_convergence", payload["fusion_summaries"])
            self.assertIn("global_coupling_index", payload["coupling_matrix"])
            self.assertIn("reinforcement_loop_risk", payload["risk_surface"])
            self.assertTrue(payload["metadata"]["no_cross_stream_governance"])

    def test_render_fusion_cli_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fusion_fixtures(tmp, days=3)
            text = GTBSL2Renderer().render_fusion_text(tmp, window_days=7)
            self.assertIn("Cross-Stream Fusion Report", text)
            self.assertIn("S8/S9/S10", text)


if __name__ == "__main__":
    unittest.main()

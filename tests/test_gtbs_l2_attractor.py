"""GTBS-L2.5 latent attractor inference tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l2.attractor import build_attractor_field, build_attractor_inference_report
from core.governance.l2.attractor.stability_topology import compute_topology
from core.governance.l2.fusion import build_fusion_report
from core.governance.l2.render import GTBSL2Renderer


def _write_fusion_fixtures(tmp: str, days: int = 5):
    obs = os.path.join(tmp, "observability")
    os.makedirs(obs, exist_ok=True)
    now = datetime.now(timezone.utc)
    ecology, singularity, shadow = [], [], []
    for i in range(days):
        ts = (now - timedelta(days=days - 1 - i)).isoformat()
        ecology.append(
            json.dumps(
                {
                    "ts": ts,
                    "acd": 0.3 + i * 0.06,
                    "odc": 0.2 + i * 0.07,
                    "rre": 0.65,
                    "cpx": 0.25 + i * 0.08,
                    "cpi": 0.2,
                }
            )
        )
        singularity.append(
            json.dumps(
                {
                    "ts": ts,
                    "ncr": 0.15 + i * 0.08,
                    "cea": 0.55,
                    "rsci": 0.1 + i * 0.06,
                }
            )
        )
        shadow.append(
            json.dumps(
                {
                    "timestamp": ts,
                    "proposal_vs_reality": {
                        "proposal_reality_divergence": 0.2 + i * 0.06,
                        "key_jaccard": 0.75 - i * 0.05,
                    },
                }
            )
        )
    for name, lines in [
        ("ecology_metrics.jsonl", ecology),
        ("singularity_metrics.jsonl", singularity),
        ("gtbs_shadow.jsonl", shadow),
    ]:
        with open(os.path.join(obs, name), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


class TestGTBSL2Attractor(unittest.TestCase):
    def test_build_attractor_field_from_fusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fusion_fixtures(tmp, days=5)
            fusion = build_fusion_report(tmp, window_days=7)
            field = build_attractor_field(fusion)
            self.assertGreaterEqual(len(field.attractors), 1)
            self.assertIn(field.field_regime, ("diffuse", "clustered", "locked", "bifurcating"))
            att = field.attractors[0]
            self.assertIn(att.stability_class, ("stable", "metastable", "collapsing", "emerging"))

    def test_topology_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fusion_fixtures(tmp, days=4)
            fusion = build_fusion_report(tmp, window_days=7)
            field = build_attractor_field(fusion)
            topo = compute_topology(field)
            self.assertGreaterEqual(topo.cluster_count, 1)
            self.assertGreaterEqual(topo.lock_in_probability, 0.0)
            self.assertLessEqual(topo.lock_in_probability, 1.0)

    def test_attractor_report_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fusion_fixtures(tmp, days=5)
            report = build_attractor_inference_report(tmp, window_days=7)
            payload = report.to_dict()
            self.assertEqual(payload["narrative_version"], "L2_v0.5")
            self.assertIn("field_regime", payload)
            self.assertIn("lock_in_signal", payload["risk_surface"])
            self.assertIn("lock_in_risk", payload["risk_surface"])
            self.assertIn("interpretation", payload)
            self.assertTrue(payload["metadata"]["no_control_leakage"])
            self.assertTrue(payload["metadata"]["attractor_not_decision"])

    def test_render_attractor_cli_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fusion_fixtures(tmp, days=3)
            text = GTBSL2Renderer().render_attractor_text(tmp, window_days=7)
            self.assertIn("Latent Attractor Inference Report", text)
            self.assertIn("S11/S12", text)


if __name__ == "__main__":
    unittest.main()

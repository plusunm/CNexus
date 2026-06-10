"""GTBS-L2 Semantic Alignment Layer tests (core.governance.l2)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l2.language import classify_openness, classify_reality_coupling
from core.governance.l2.loader import generate_l2_narrative, load_snapshot_from_base_dir
from core.governance.l2.render import GTBSL2Renderer
from core.governance.l2.snapshot import GTBSSnapshot


class TestGTBSL2Module(unittest.TestCase):
    def test_classify_helpers(self):
        self.assertEqual(classify_openness(0.1), "low")
        self.assertEqual(classify_openness(0.5), "medium")
        self.assertEqual(classify_openness(0.9), "high")

    def test_renderer_metadata(self):
        snap = GTBSSnapshot.from_sources(
            divergence_data={"proposal_alignment": 0.85},
            shaping_data={"primary_source": "reality_driven", "self_reinforcing_risk": 0.2},
            continuity_data={"reality_coupling": 0.7, "openness": 0.6},
            ecology_data={"attractor_state": "distributed", "ecosystem_health": 0.75},
        )
        out = GTBSL2Renderer().render(snap)
        self.assertTrue(out["metadata"]["read_only"])
        self.assertTrue(out["metadata"]["instrumentation_only"])
        self.assertIn("divergence", out["summaries"])
        self.assertEqual(out["narrative_version"], "L2_v0.1")

    def test_generate_l2_narrative(self):
        out = generate_l2_narrative(
            divergence_data={"proposal_alignment": 0.6},
            shaping_data={"primary_source": "user_driven", "self_reinforcing_risk": 0.3},
            continuity_data={"reality_coupling": 0.55, "openness": 0.5},
            ecology_data={"attractor_state": "moderate", "ecosystem_health": 0.55},
        )
        self.assertIn("summaries", out)
        self.assertIn("raw_metrics", out)

    def test_empty_snapshot(self):
        snap = GTBSSnapshot()
        text = GTBSL2Renderer().render_narrative_text(snap)
        self.assertIn("暂无", text)

    def test_load_from_observability(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            with open(os.path.join(obs, "ecology_metrics.jsonl"), "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": "2026-01-01T00:00:00+00:00", "acd": 0.4, "odc": 0.3, "rre": 0.6, "cpx": 0.25}) + "\n")
            with open(os.path.join(obs, "gtbs_shadow.jsonl"), "w", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "timestamp": "2026-01-01T00:00:00+00:00",
                            "proposal_vs_reality": {"proposal_reality_divergence": 0.2, "key_jaccard": 0.8, "cross_store_consistency": 0.85},
                            "context": {"phase": "interaction", "grounding_event_id": "g1"},
                        }
                    )
                    + "\n"
                )
            snap = load_snapshot_from_base_dir(tmp)
            self.assertFalse(snap.is_empty)
            self.assertAlmostEqual(snap.divergence["proposal_alignment"], 0.8)

    def test_renderer_type_guard(self):
        with self.assertRaises(TypeError):
            GTBSL2Renderer().render({})  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

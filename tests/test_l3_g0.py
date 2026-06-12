"""L3-G0 governance boundary layer tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import (
    AuthorityRouter,
    Boundary,
    BoundaryRegistry,
    L3G0Report,
    LeakageProbe,
    build_l3_g0_report,
    default_registry,
    signals_from_l2_stack,
)


class TestL3G0(unittest.TestCase):
    def test_boundary_registry(self):
        reg = BoundaryRegistry()
        b = Boundary(name="test", scope="runtime", description="desc")
        reg.register(b)
        self.assertEqual(reg.get("test"), b)
        self.assertEqual(len(reg.all_boundaries()), 1)

    def test_default_registry_has_canonical_boundaries(self):
        reg = default_registry()
        names = {b.name for b in reg.all_boundaries()}
        self.assertIn("runtime", names)
        self.assertIn("l2_output", names)
        self.assertIn("attractor_state", names)

    def test_authority_router(self):
        router = AuthorityRouter()
        sig = {"type": "interpretation"}
        self.assertEqual(router.classify(sig).name, "INTERPRETATION")
        decision = router.route({"type": "governance_attempt"})
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, "reject")

    def test_leakage_probe(self):
        router = AuthorityRouter()
        probe = LeakageProbe(router)
        probe.record({"type": "interpretation", "source": "l2_fusion"})
        probe.record({"type": "observation", "source": "phase_c"})
        summary = probe.summary()
        self.assertEqual(summary["interpretation"], 1)
        self.assertEqual(summary["observation"], 1)
        self.assertGreaterEqual(summary["violations_detected"], 0)

    def test_l3_report_metadata(self):
        summary = {
            "total_signals": 3,
            "observation": 1,
            "interpretation": 1,
            "governance_attempt": 1,
            "violations_detected": 1,
        }
        report = L3G0Report(summary)
        payload = report.render()
        self.assertTrue(payload["metadata"]["no_control_directness"])
        self.assertIn("S13", payload["metadata"]["principles"])

    def test_build_l3_g0_synthetic(self):
        report = build_l3_g0_report(use_l2_coupling=False)
        payload = report.render()
        self.assertEqual(payload["summary"]["total_signals"], 3)
        self.assertTrue(payload["metadata"]["constraint_non_executability"])

    def test_l2_l3_coupling_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            now = datetime.now(timezone.utc)
            lines_eco, lines_sin, lines_sh = [], [], []
            for i in range(3):
                ts = (now - timedelta(days=2 - i)).isoformat()
                lines_eco.append(
                    json.dumps(
                        {"ts": ts, "acd": 0.3, "odc": 0.2, "rre": 0.6, "cpx": 0.3 + i * 0.1, "cpi": 0.2}
                    )
                )
                lines_sin.append(json.dumps({"ts": ts, "ncr": 0.2, "cea": 0.5, "rsci": 0.15 + i * 0.1}))
                lines_sh.append(
                    json.dumps(
                        {
                            "timestamp": ts,
                            "proposal_vs_reality": {"proposal_reality_divergence": 0.2, "key_jaccard": 0.7},
                        }
                    )
                )
            for name, lines in [
                ("ecology_metrics.jsonl", lines_eco),
                ("singularity_metrics.jsonl", lines_sin),
                ("gtbs_shadow.jsonl", lines_sh),
            ]:
                with open(os.path.join(obs, name), "w", encoding="utf-8") as fh:
                    fh.write("\n".join(lines) + "\n")

            signals = signals_from_l2_stack(tmp, window_days=7)
            self.assertGreater(len(signals), 0)
            report = build_l3_g0_report(tmp, window_days=7)
            payload = report.render()
            self.assertGreater(payload["summary"]["total_signals"], 0)
            self.assertIn("boundaries", payload)


if __name__ == "__main__":
    unittest.main()

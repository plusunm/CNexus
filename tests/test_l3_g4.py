"""L3-G4 meta-governance reflection tests."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l3 import build_l3_g4_report
from core.governance.l3.meta import (
    DriftAnalyzer,
    ObserverModel,
    ReflexivityEngine,
    SelfModelExtractor,
    StructuralModelExtractor,
)
from core.governance.l3.meta.l3g4_report import L3G4Reporter


class TestL3G4(unittest.TestCase):
    def test_self_vs_structural_model_gap(self):
        stack = {
            "g0": {"summary": {"governance_attempt": 1}, "violations": [{}], "metadata": {}},
            "g1": {"violation_score": 0.9, "arbitration_result": {"winner": "runtime_safety"}},
            "g2": {"shadow_states": [{}, {}]},
            "g3": {"stability": {"entropy": 0.6, "lock_in": 0.7}, "system_phase": "over-constrained field", "optimization": {}},
        }
        self_m = SelfModelExtractor().extract(stack)
        struct_m = StructuralModelExtractor().extract(stack)
        gap = StructuralModelExtractor().gap(self_m, struct_m)
        self.assertGreater(gap, 0.0)
        self.assertNotEqual(self_m["summary"], struct_m["summary"])

    def test_reflexivity_engine(self):
        self_m = {"summary": "self"}
        struct_m = {"summary": "struct", "violation_score": 0.5, "lock_in": 0.6, "governance_attempts": 1}
        observer = {"interpretation_stability_score": 0.4, "self_vs_structural_gap": True}
        profile = ReflexivityEngine().compute(self_m, struct_m, observer, 0.4)
        self.assertGreater(profile.reflexivity_score, 0.0)
        self.assertIn(profile.drift_signature.severity, ("low", "medium", "high"))

    def test_drift_analyzer_phases(self):
        from core.governance.l3.meta.types import DriftSignature, ReflexivityProfile

        reflex = ReflexivityProfile(0.7, 0.5, 0.7, 0.65, DriftSignature("recursive_self_alignment_pressure", "high"))
        meta = DriftAnalyzer().analyze(
            reflex,
            {"summary": "self"},
            {"summary": "struct", "lock_in": 0.8, "violation_score": 0.5},
            {"interpretation_stability_score": 0.3},
            0.4,
        )
        self.assertIn(meta.phase, ("stable", "drifting", "self_sealing", "expanding"))

    def test_l3g4_report_metadata(self):
        from core.governance.l3.meta.types import DriftSignature, MetaGovernanceState, ReflexivityProfile

        meta = MetaGovernanceState("stable", "self", "observed", 0.1)
        reflex = ReflexivityProfile(0.3, 0.1, 0.2, 0.25, DriftSignature("stable_reflexivity", "low"))
        report = L3G4Reporter().render(meta, reflex, {})
        payload = report.to_dict()
        self.assertTrue(payload["metadata"]["no_self_modification"])
        self.assertTrue(payload["metadata"]["observational_reflexivity_only"])

    def test_build_l3_g4_synthetic(self):
        report = build_l3_g4_report(
            {"type": "governance_attempt", "target": "runtime", "confidence": 0.9},
            use_l2_coupling=False,
        )
        payload = report.to_dict()
        self.assertIn(payload["meta_governance_state"], ("stable", "drifting", "self_sealing", "expanding"))
        self.assertIn("drift_signature", payload)
        self.assertIn("risk_signals", payload)

    def test_build_l3_g4_from_l2_coupling(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = os.path.join(tmp, "observability")
            os.makedirs(obs, exist_ok=True)
            now = datetime.now(timezone.utc)
            for i in range(3):
                ts = (now - timedelta(days=2 - i)).isoformat()
                with open(os.path.join(obs, "ecology_metrics.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": ts, "acd": 0.3, "odc": 0.2, "rre": 0.6, "cpx": 0.5, "cpi": 0.2}) + "\n")
                with open(os.path.join(obs, "singularity_metrics.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": ts, "ncr": 0.2, "cea": 0.5, "rsci": 0.6}) + "\n")
                with open(os.path.join(obs, "gtbs_shadow.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(
                        json.dumps(
                            {"timestamp": ts, "proposal_vs_reality": {"proposal_reality_divergence": 0.3, "key_jaccard": 0.6}}
                        )
                        + "\n"
                    )
            report = build_l3_g4_report(base_dir=tmp, window_days=7)
            self.assertGreater(report.reflexivity_score, 0.0)


if __name__ == "__main__":
    unittest.main()

"""Semantic Safety Stack v6 — cognitive dissolution tests."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.semantic_safety.v6 import (
    apply_cognitive_dissolution,
    build_semantic_safety_v6_report,
)
from core.governance.semantic_safety.v6.cognitive_continuity_breaker import CognitiveContinuityBreaker
from core.governance.semantic_safety.v6.coherence_decay_engine import CoherenceDecayEngine
from core.governance.semantic_safety.v6.narrative_disassembler import NarrativeDisassembler
from core.governance.semantic_safety.v6.temporal_semantic_scrambler import TemporalSemanticScrambler


class TestSemanticSafetyV6(unittest.TestCase):
    def test_continuity_breaker_breaks_chain(self):
        broken = CognitiveContinuityBreaker().break_continuity([{"a": 1}, {"b": 2}])
        self.assertEqual(len(broken), 2)
        self.assertEqual(broken[0]["temporal_link"], "broken")
        self.assertEqual(broken[0]["causal_continuity"], "undefined")

    def test_scrambler_deterministic(self):
        seq = ["alpha", "beta", "gamma", "delta"]
        a = TemporalSemanticScrambler().scramble(seq)
        b = TemporalSemanticScrambler().scramble(seq)
        self.assertEqual(a, b)
        self.assertNotEqual(a, seq)

    def test_narrative_disassembler_non_narrative(self):
        out = NarrativeDisassembler().disassemble("once upon a causal chain")
        self.assertEqual(out["structure"], "non-narrative")
        self.assertEqual(out["coherence_chain"], "broken")

    def test_coherence_decay_irreversible(self):
        decayed = CoherenceDecayEngine().decay({"tokens": ["a"]})
        self.assertLess(decayed["coherence"], 0.1)
        self.assertEqual(decayed["decay_state"], "irreversible")

    def test_apply_dissolution_v6_envelope(self):
        result = apply_cognitive_dissolution({"winner": "runtime_safety", "violation_score": 0.8})
        self.assertTrue(result["cognitive_dissolution_v6"])
        self.assertEqual(result["temporal_coherence"], "broken")
        self.assertEqual(result["narrative_state"]["status"], "non-constructible")
        self.assertEqual(result["event_continuity"]["causal_chain"], "undefined")
        self.assertIn("isolation_envelope", result)

    def test_build_v6_report_l3_stack(self):
        report = build_semantic_safety_v6_report()
        payload = report.to_dict()
        self.assertTrue(payload["cognitive_dissolution_v6"])
        self.assertIn("L3-G1", payload["dissolved_reports"])
        self.assertTrue(payload["metadata"]["non_narrative_cognitive_observation_kernel"])

    def test_v6_narrative_not_constructible(self):
        report = build_semantic_safety_v6_report()
        for dissolved in report.dissolved_reports.values():
            self.assertEqual(dissolved["narrative_state"]["status"], "non-constructible")
            self.assertEqual(dissolved["semantic_timefield"]["causal_embedding"], "collapsed")

    def test_v6_cli_script(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "semantic_safety_v6_dissolution.py"), "--text"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Cognitive Dissolution", proc.stdout)


if __name__ == "__main__":
    unittest.main()

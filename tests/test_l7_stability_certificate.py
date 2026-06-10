import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.l7.causal_transition import CausalTransitionValidator
from core.governance.l7.lyapunov_checker import LyapunovInequalityChecker
from core.governance.l7.stability_certificate import StabilityCertificateGenerator
from core.governance.l7.transition_reconstructor import TransitionReconstructor


def _graph_hash(nodes: int, edges: int) -> str:
    return hashlib.sha256(f"{nodes}:{edges}".encode()).hexdigest()


def _sample_records(n: int = 12) -> list:
    records = []
    v = 0.25
    for i in range(n):
        v = max(0.05, v - 0.01 + (0.002 if i % 3 == 0 else 0.0))
        nodes = 5 + i
        edges = 4 + i
        prev_tip = f"user_{999 + i}" if i > 0 else None
        tip = f"user_{1000 + i}"
        nd = 1 if i > 0 else 0
        ed = 1 if i > 0 else 0
        records.append(
            {
                "ts": f"2026-06-10T00:00:{i:02d}Z",
                "approved": True,
                "potential_v": round(v, 4),
                "entropy_rate": 0.001 if i % 4 else 0.003,
                "grounding_avg": 0.85 - i * 0.005,
                "reference_stable": True,
                "reality_tip": tip,
                "tip_parent_id": prev_tip,
                "prev_graph_hash": _graph_hash(nodes - 1, edges - 1) if i > 0 else None,
                "graph_hash": _graph_hash(nodes, edges),
                "graph_nodes": nodes,
                "graph_edges": edges,
                "node_delta": nd,
                "edge_delta": ed,
                "parent_edges_delta": ed,
                "entropy_dynamics": "piecewise",
                "interventions": [],
            }
        )
    return records


class TestL7StabilityCertificate(unittest.TestCase):
    def test_lyapunov_scalar_channel_for_verdict(self):
        checker = LyapunovInequalityChecker(alpha=0.01, eps=0.005)
        descending = [0.5, 0.45, 0.40, 0.36, 0.33]
        scalar = checker.check(descending, energy_channel="potential_v")
        self.assertEqual(scalar.energy_channel, "potential_v")
        self.assertGreater(scalar.lyapunov_descent_ratio, 0.5)

    def test_lyapunov_dual_channels_differ(self):
        checker = LyapunovInequalityChecker(alpha=0.01, eps=0.005)
        records = _sample_records(8)
        dual = checker.check_dual_from_records(records)
        self.assertEqual(dual.scalar.energy_channel, "potential_v")
        self.assertEqual(dual.composite.energy_channel, "composite")

    def test_behavioral_legality_grounding_diff(self):
        records = _sample_records(4)
        ok = CausalTransitionValidator.behavioral_legality(records)
        self.assertEqual(ok, 1.0)

        bad = dict(records[2])
        bad["grounding_avg"] = records[1]["grounding_avg"] - 0.25
        bad["interventions"] = []
        self.assertEqual(CausalTransitionValidator.behavioral_pair(records[1], bad), 0.0)

    def test_transition_reconstructor_hash_evolution(self):
        records = _sample_records(5)
        transitions = TransitionReconstructor().build(records)
        self.assertEqual(len(transitions), 4)
        for t in transitions:
            self.assertTrue(t.hash_evolution_valid)
            self.assertTrue(t.tip_chain_valid)

    def test_tip_chain_breaks_without_parent(self):
        prev = _sample_records(2)[0]
        bad = dict(_sample_records(2)[1])
        bad["tip_parent_id"] = None
        t = TransitionReconstructor()._pair(0, prev, bad)
        self.assertFalse(t.tip_chain_valid)
        self.assertIn("tip_chain_break", t.violations)

    def test_transition_legality_detects_violation(self):
        prev = _sample_records(2)[0]
        bad = dict(_sample_records(2)[1])
        bad["potential_v"] = prev["potential_v"] + 0.5
        bad["interventions"] = []
        self.assertFalse(CausalTransitionValidator.allows(prev, bad))

    def test_transition_legality_allows_controlled_spike(self):
        prev = _sample_records(2)[0]
        ok = dict(_sample_records(2)[1])
        ok["potential_v"] = prev["potential_v"] + 0.5
        ok["interventions"] = ["GRADIENT_DESCENT"]
        self.assertTrue(CausalTransitionValidator.allows(prev, ok))

    def test_dual_track_legality_fields(self):
        analysis = CausalTransitionValidator().analyze(_sample_records(10))
        self.assertIn("structural_legality", analysis)
        self.assertIn("behavioral_legality", analysis)
        expected = CausalTransitionValidator.combine_legality(
            analysis["structural_legality"],
            analysis["behavioral_legality"],
        )
        self.assertAlmostEqual(analysis["transition_legality"], expected, places=4)

    def test_certificate_generator_v231(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for rec in _sample_records(15):
                    f.write(json.dumps(rec) + "\n")
            cert = StabilityCertificateGenerator(path).generate(last_n=15)
            self.assertGreater(cert.total_cycles, 0)
            self.assertEqual(cert.certificate_version, "v2.3.1")
            self.assertGreater(cert.transition_count, 0)
            self.assertGreaterEqual(cert.structural_legality, 0.0)
            self.assertGreaterEqual(cert.behavioral_legality, 0.0)
            self.assertIn(cert.entropy_regime, ("stable", "shift", "oscillating", "rising"))
            d = cert.to_dict()
            self.assertIn("lyapunov_composite_margin", d)
            self.assertIn("structural_legality", d)
            self.assertTrue(d.get("axiom_compliance", {}).get("observer_only_l7"))

    def test_regime_aware_score_differs(self):
        gen = StabilityCertificateGenerator("/dev/null")
        stable = gen._regime_aware_score(
            v_std=0.05,
            grounding_std=0.03,
            entropy_std=0.005,
            entropy_trend_abs=0.001,
            lyapunov_margin=0.02,
            lyapunov_descent_ratio=0.7,
            causal_consistency=0.9,
            transition_legality=0.95,
            regime="stable",
        )
        osc = gen._regime_aware_score(
            v_std=0.05,
            grounding_std=0.03,
            entropy_std=0.08,
            entropy_trend_abs=0.001,
            lyapunov_margin=0.01,
            lyapunov_descent_ratio=0.5,
            causal_consistency=0.75,
            transition_legality=0.88,
            regime="oscillating",
        )
        self.assertNotAlmostEqual(stable, osc, places=1)


if __name__ == "__main__":
    unittest.main()

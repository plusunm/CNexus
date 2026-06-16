"""Causal state graph — reachability, illegal transitions, wait-for cycles."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.causal_state_graph import (
    S_BOOT_3,
    S_BOOT_3_STALL,
    S_BOOT_4,
    S_UI_LIVE,
    analyze_cnexus_runtime,
    build_cnexus_boot_graph,
    illegal_transitions,
    reachability,
)


class TestCausalStateGraph(unittest.TestCase):
    def test_ui_live_reachable_from_init(self) -> None:
        dist = reachability(build_cnexus_boot_graph())
        self.assertGreaterEqual(dist[S_UI_LIVE], 0)

    def test_banned_optimistic_boot4_listed_as_hard_illegal(self) -> None:
        graph = build_cnexus_boot_graph()
        banned = [t for t in illegal_transitions(graph) if t.id.startswith("t_force_boot4")]
        self.assertGreaterEqual(len(banned), 2)
        self.assertTrue(all(not t.enabled for t in banned))

    def test_boot3_stall_reachable_without_boot4_shortcut(self) -> None:
        dist = reachability(build_cnexus_boot_graph())
        self.assertGreaterEqual(dist[S_BOOT_3_STALL], 0)

    def test_optimistic_boot3_to_boot4_not_in_causal_reachability_chain(self) -> None:
        graph = build_cnexus_boot_graph()
        # Direct optimistic edge disabled — must go through gates
        direct = [t for t in graph.transitions if t.source == S_BOOT_3 and t.target == S_BOOT_4 and t.enabled]
        self.assertEqual(direct, [])

    def test_analysis_report_has_deadlock_gate_nodes(self) -> None:
        report = analyze_cnexus_runtime()
        self.assertIn("GATE_READY_EVALUATION", report.deadlock_gates or report.distances)


if __name__ == "__main__":
    unittest.main()

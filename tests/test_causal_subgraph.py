"""Causal index + subgraph builder tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.query.causal_index import CausalIndex
from core.spine.query.subgraph import build_subgraph, find_root_cause_summary


class TestCausalSubgraph(unittest.TestCase):
    def setUp(self):
        self.events = [
            {"event_id": "e1", "trace_id": "t1", "parent_event_id": None},
            {"event_id": "e2", "trace_id": "t1", "parent_event_id": "e1"},
            {"event_id": "e3", "trace_id": "t1", "parent_event_id": "e2"},
        ]

    def test_trace_up_and_roots(self):
        index = CausalIndex()
        index.build(self.events)
        self.assertEqual(index.trace_up("e3"), ["e2", "e1"])
        self.assertEqual(index.root_event_ids(self.events), ["e1"])

    def test_subgraph_nodes_edges(self):
        sg = build_subgraph(self.events)
        self.assertEqual(len(sg["nodes"]), 3)
        self.assertEqual(len(sg["edges"]), 2)
        self.assertEqual(sg["edges"][0]["kind"], "parent")

    def test_root_cause_summary(self):
        index = CausalIndex()
        index.build(self.events)
        summary = find_root_cause_summary(self.events, index)
        self.assertEqual(summary["roots"], ["e1"])
        self.assertEqual(summary["chains"][0]["root_cause"], "e1")


if __name__ == "__main__":
    unittest.main()

"""Semantic causal index v2 tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.query.causal_v2 import SemanticCausalIndex


class TestCausalV2(unittest.TestCase):
    def test_builds_temporal_and_triggered_by(self):
        events = [
            {
                "event_id": "e1",
                "trace_id": "t1",
                "event_type": "dispatch",
            },
            {
                "event_id": "e2",
                "trace_id": "t1",
                "event_type": "recall",
                "parent_event_id": "e1",
                "causal_edges": [
                    {"from": "e1", "to": "e2", "relation": "temporal"},
                    {"from": "e1", "to": "e2", "relation": "triggered_by"},
                ],
            },
        ]
        idx = SemanticCausalIndex()
        idx.build(events)
        self.assertEqual(len(idx.edges), 2)
        self.assertEqual(idx.trigger_chains("e2"), ["e1"])


if __name__ == "__main__":
    unittest.main()

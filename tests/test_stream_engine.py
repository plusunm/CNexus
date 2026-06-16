"""Spine explanation stream engine tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.stream.engine import SpineExplanationStreamEngine


class TestStreamEngine(unittest.TestCase):
    def test_ingest_deduplicates_and_builds_frame(self):
        engine = SpineExplanationStreamEngine(trace_id="t1")
        event = {
            "event_id": "e1",
            "trace_id": "t1",
            "event_type": "control",
            "parent_event_id": "root",
            "payload": {"decision": "allow", "policy": "gtbs"},
        }
        frame = engine.ingest_event(event)
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame["event_id"], "e1")
        self.assertTrue(frame["causal_delta"]["added_edges"])
        self.assertIn("feedback", frame)
        self.assertFalse(frame["feedback"]["applied_to_runtime"])

        again = engine.ingest_event(event)
        self.assertIsNone(again)

    def test_wrong_trace_skipped(self):
        engine = SpineExplanationStreamEngine(trace_id="t1")
        frame = engine.ingest_event({"event_id": "e2", "trace_id": "other"})
        self.assertIsNone(frame)

    def test_snapshot_streams(self):
        engine = SpineExplanationStreamEngine(trace_id="t1")
        engine.ingest_event(
            {
                "event_id": "e1",
                "trace_id": "t1",
                "parent_event_id": "root",
                "event_type": "recall",
            }
        )
        snap = engine.snapshot_streams()
        self.assertIn("causal_graph", snap)
        self.assertIn("control_state", snap)


if __name__ == "__main__":
    unittest.main()

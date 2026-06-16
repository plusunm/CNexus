"""CP-2 Spine Query Engine v1 tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.query import parse_query_text, run_query
from core.spine.storage import SpineEventLog


class TestSpineQueryEngine(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base = self._tmpdir.name
        self.log = SpineEventLog(self.base)
        rows = [
            {
                "event_id": "e1",
                "trace_id": "t1",
                "timestamp": "2026-06-14T00:00:01+00:00",
                "event_type": "recall",
                "subsystem": "gtbs",
                "action": "propose",
                "summary": "recall",
            },
            {
                "event_id": "e2",
                "trace_id": "t1",
                "timestamp": "2026-06-14T00:00:02+00:00",
                "event_type": "write_intent",
                "subsystem": "gtbs",
                "action": "propose",
                "summary": "write",
                "parent_event_id": "e1",
                "state_delta": {"stores": ["working_self"]},
            },
            {
                "event_id": "e3",
                "trace_id": "t1",
                "timestamp": "2026-06-14T00:00:03+00:00",
                "event_type": "control",
                "subsystem": "control_plane",
                "action": "read",
                "summary": "control warn",
                "parent_event_id": "e2",
                "decision": "WARN",
                "caller": "api",
                "entry": "chat_send",
            },
        ]
        for row in rows:
            self.log.append(__import__("core.spine.types", fromlist=["SpineEvent"]).SpineEvent.from_dict(row))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_parse_query_dsl(self):
        parsed = parse_query_text("TRACE t1 EXPLAIN causal")
        self.assertEqual(parsed.trace_id, "t1")
        self.assertEqual(parsed.mode, "causal")

    def test_run_query_by_trace_id(self):
        result = run_query(self.base, trace_id="t1")
        body = result.to_dict()
        self.assertEqual(body["schema_version"], "spine-query-1")
        self.assertEqual(body["trace_id"], "t1")
        self.assertEqual(len(body["events"]), 3)
        self.assertEqual(len(body["edges"]), 2)
        self.assertEqual(body["edges"][0]["from"], "e1")
        self.assertEqual(body["control"][0]["decision"], "WARN")
        self.assertEqual(len(body["state"]["deltas"]), 1)
        self.assertIn("subgraph", body)
        self.assertEqual(len(body["subgraph"]["nodes"]), 3)
        self.assertEqual(body["causal"]["index_version"], "v2")
        self.assertEqual(body["causal"]["roots"], ["e1"])
        self.assertIn("semantic", body["causal"])
        self.assertIn("state_timeline", body["meta"])
        self.assertIn("narrative", body["explanation"])
        self.assertIn("root_causes", body["explanation"])

    def test_run_query_by_dsl(self):
        result = run_query(self.base, query="TRACE t1 EXPLAIN linear")
        self.assertEqual(result.mode, "linear")
        self.assertEqual(len(result.events), 3)

    def test_empty_trace(self):
        result = run_query(self.base, trace_id="missing")
        self.assertEqual(result.events, [])
        self.assertIn("No spine events", result.explanation["narrative"])


if __name__ == "__main__":
    unittest.main()

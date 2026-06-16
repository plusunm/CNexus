"""Token Spine layer tests — binding, gravity field, observatory."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.cost.gravity_field import TokenCostGravityField
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEvent
from core.spine.token.binding import bind_tokens_to_execution
from core.spine.token.service import build_token_observatory, build_trace_token_report
from core.spine.token.token_emitter import emit_token_event
from core.spine.token.token_store import read_tokens


class TestTokenSpine(unittest.TestCase):
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
                "event_type": "llm",
                "subsystem": "llm",
                "action": "generate",
                "summary": "generate",
                "parent_event_id": "e1",
            },
            {
                "event_id": "e3",
                "trace_id": "t1",
                "timestamp": "2026-06-14T00:00:03+00:00",
                "event_type": "control",
                "subsystem": "control_plane",
                "action": "read",
                "summary": "control",
                "parent_event_id": "e2",
            },
        ]
        for row in rows:
            self.log.append(SpineEvent.from_dict(row))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_emit_and_read_tokens(self):
        emit_token_event(
            "t1",
            source="llm_generate",
            tokens_in=100,
            tokens_out=50,
            phase="EXEC",
            spine_event_id="e2",
            base_dir=self.base,
        )
        stored = read_tokens("t1", base_dir=self.base)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["total"], 150)
        self.assertEqual(stored[0]["spine_event_id"], "e2")

    def test_bind_tokens_to_execution(self):
        tokens = [
            {
                "trace_id": "t1",
                "event_id": "tok1",
                "total": 200,
                "tokens_in": 120,
                "tokens_out": 80,
            }
        ]
        bound = bind_tokens_to_execution("t1", tokens, base_dir=self.base)
        self.assertEqual(len(bound), 1)
        self.assertTrue(bound[0].get("spine_event_id"))

    def test_gravity_field(self):
        events = self.log.read_all()
        token_events = [
            {"spine_event_id": "e1", "total": 100, "phase": "RECALL"},
            {"spine_event_id": "e2", "total": 500, "phase": "EXEC"},
        ]
        field = TokenCostGravityField().build(events, token_events)
        self.assertGreater(field["total_cost"], 0)
        self.assertIn("e2", field["field"])
        self.assertIn("EXEC", field["by_phase"])

    def test_trace_token_report_synthesized(self):
        report = build_trace_token_report(self.base, "t1")
        self.assertEqual(report["trace_id"], "t1")
        self.assertGreater(report["total_tokens"], 0)
        self.assertTrue(report.get("field"))
        self.assertTrue(report.get("bindings"))

    def test_token_observatory(self):
        obs = build_token_observatory(self.base, limit=10)
        self.assertGreaterEqual(len(obs), 1)
        self.assertEqual(obs[0]["trace_id"], "t1")
        self.assertIn("cost_level", obs[0])


if __name__ == "__main__":
    unittest.main()

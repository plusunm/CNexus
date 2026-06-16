"""CP-2 Phase 0 — Spine canonical layer tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.decision_engine import Decision, DecisionType
from core.governance.gtbs.adapters.recall_adapter import emit_recall_side_effect_intent
from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.write_intent_bus import WriteIntentBus, write_intent_provenance_scope
from core.spine import rebuild_spine_from_gtbs
from core.spine.integration import register_spine_writer
from core.spine.storage import SpineEventLog
from core.spine.writer import SpineWriter


class TestSpineWriter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base = self._tmpdir.name
        self.gtbs = GTBSTransactionLog(self.base)
        self.spine_log = SpineEventLog(self.base)
        self.writer = SpineWriter(self.spine_log)
        register_spine_writer(self.writer)
        self.bus = WriteIntentBus(self.gtbs, spine_writer=self.writer)

    def tearDown(self):
        register_spine_writer(None)
        self._tmpdir.cleanup()

    def test_gtbs_emit_projects_spine_event(self):
        with write_intent_provenance_scope(trace_id="trace-test-1", entry_registry="memory_recall"):
            emit_recall_side_effect_intent(
                self.bus, query="hello", top_k=6, use_attention=True, activated_count=1, top_labels=["goal"]
            )
        spine_rows = self.spine_log.read_all()
        self.assertEqual(len(spine_rows), 1)
        self.assertEqual(spine_rows[0]["trace_id"], "trace-test-1")
        self.assertEqual(spine_rows[0]["event_type"], "recall")
        self.assertIn("write_intent", spine_rows[0])

    def test_causal_parent_linking_within_trace(self):
        with write_intent_provenance_scope(trace_id="trace-chain"):
            emit_recall_side_effect_intent(
                self.bus, query="a", top_k=3, use_attention=False, activated_count=0, top_labels=[]
            )
            intent_id = emit_recall_side_effect_intent(
                self.bus, query="b", top_k=3, use_attention=False, activated_count=0, top_labels=[]
            )
        self.bus.record_shadow_commit(intent_id, receipt={"ok": True})
        events = self.spine_log.read_events()
        self.assertEqual(len(events), 3)
        self.assertIsNone(events[0].parent_event_id)
        self.assertEqual(events[1].parent_event_id, events[0].event_id)
        self.assertEqual(events[2].parent_event_id, events[1].event_id)

    def test_rebuild_from_gtbs(self):
        with write_intent_provenance_scope(trace_id="trace-rebuild"):
            emit_recall_side_effect_intent(
                self.bus, query="x", top_k=2, use_attention=False, activated_count=0, top_labels=[]
            )
        self.spine_log.clear()
        count = rebuild_spine_from_gtbs(self.base, clear=True)
        self.assertEqual(count, 1)
        self.assertEqual(len(self.spine_log.read_all()), 1)

    def test_control_decision_projection(self):
        from core.spine.integration import maybe_project_control_decision

        decision = Decision(
            type=DecisionType.WARN,
            reason="LEGACY_CALLER",
            route_kind="memory_read",
            registry_entry="legacy_write",
            caller="legacy_api",
            channel="legacy",
        )
        maybe_project_control_decision(decision, trace_id="trace-ctrl")
        rows = self.spine_log.read_all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "control")
        self.assertEqual(rows[0]["decision"], "WARN")


if __name__ == "__main__":
    unittest.main()

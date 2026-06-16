"""CP-2 trace context binding tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.types import RouteKind
from core.governance.gtbs.adapters.recall_adapter import emit_recall_side_effect_intent
from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.write_intent_bus import WriteIntentBus, write_intent_provenance_scope
from core.runtime.trace_context import get_trace_id, trace_scope
from core.spine.integration import register_spine_writer
from core.spine.storage import SpineEventLog
from core.spine.writer import SpineWriter


class TestTraceContext(unittest.TestCase):
    def test_trace_scope_generates_id(self):
        with trace_scope() as tid:
            self.assertTrue(tid.startswith("trace-"))
            self.assertEqual(get_trace_id(), tid)

    def test_trace_scope_preserves_explicit(self):
        with trace_scope("trace-explicit") as tid:
            self.assertEqual(tid, "trace-explicit")
            self.assertEqual(get_trace_id(), "trace-explicit")

    def test_dispatch_injects_trace_id_on_dict_result(self):
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"ok": True, "reply": "hi"}
        disp = AuthorityDispatcher(runtime)
        result = disp.chat_send(message="hello")
        self.assertIsInstance(result, dict)
        self.assertIn("trace_id", result)
        self.assertTrue(str(result["trace_id"]).startswith("trace-"))

    def test_chat_dispatch_projects_control_to_spine(self):
        tmp = tempfile.TemporaryDirectory()
        base = tmp.name
        gtbs = GTBSTransactionLog(base)
        spine_log = SpineEventLog(base)
        writer = SpineWriter(spine_log)
        register_spine_writer(writer)
        bus = WriteIntentBus(gtbs, spine_writer=writer)

        runtime = MagicMock()
        runtime.process_interaction.return_value = {"ok": True, "reply": "hi"}
        runtime.config = {"gtbs": {"enable_write_intent_shadow": True}}
        disp = AuthorityDispatcher(runtime)

        with patch.object(
            disp,
            "_execute",
            side_effect=lambda ctx: (
                emit_recall_side_effect_intent(
                    bus,
                    query="q",
                    top_k=3,
                    use_attention=False,
                    activated_count=0,
                    top_labels=[],
                ),
                {"ok": True, "reply": "hi"},
            )[-1],
        ):
            result = disp.chat_send(message="hello")

        self.assertIn("trace_id", result)
        rows = spine_log.read_all()
        trace_ids = {r["trace_id"] for r in rows}
        self.assertIn(result["trace_id"], trace_ids)
        register_spine_writer(None)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

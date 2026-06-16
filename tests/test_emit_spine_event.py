"""CP-2.5 Execution Spine Hook tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.trace_context import trace_scope
from core.spine.emit import emit_spine_event
from core.spine.integration import register_spine_writer
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEventType
from core.spine.writer import SpineWriter


class TestEmitSpineEvent(unittest.TestCase):
    def test_emit_writes_execution_event_with_semantic_edge(self):
        tmp = tempfile.TemporaryDirectory()
        writer = SpineWriter(SpineEventLog(tmp.name))
        register_spine_writer(writer)

        with trace_scope("trace-exec-1"):
            first = emit_spine_event(
                event_type=SpineEventType.DISPATCH.value,
                summary="dispatch · chat_send",
                subsystem="control_plane",
            )
            second = emit_spine_event(
                event_type=SpineEventType.RECALL.value,
                summary="recall · hello",
                payload={"query": "hello", "top_k": 5, "result_count": 3},
                triggered_by=first.event_id if first else None,
            )

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        assert second is not None
        rows = writer._log.read_all()
        self.assertEqual(len(rows), 2)
        edges = second.to_dict().get("causal_edges") or []
        relations = {e["relation"] for e in edges}
        self.assertIn("temporal", relations)
        self.assertIn("triggered_by", relations)

        register_spine_writer(None)
        tmp.cleanup()

    def test_no_trace_no_emit(self):
        from core.runtime import trace_context

        trace_context._current_trace_id.set(None)
        tmp = tempfile.TemporaryDirectory()
        writer = SpineWriter(SpineEventLog(tmp.name))
        register_spine_writer(writer)
        result = emit_spine_event(event_type="recall", summary="x")
        self.assertIsNone(result)
        self.assertEqual(len(writer._log.read_all()), 0)
        register_spine_writer(None)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

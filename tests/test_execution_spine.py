"""Execution Spine Layer v1 tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.execution.bind import bind_explanation_to_execution
from core.spine.execution.builder import build_execution_graph
from core.spine.execution.semantics import classify_event_phase
from core.spine.query.builder import run_query
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEvent


class TestExecutionSemantics(unittest.TestCase):
    def test_classify_phases(self):
        self.assertEqual(classify_event_phase({"event_type": "dispatch"}), "trigger")
        self.assertEqual(classify_event_phase({"event_type": "control"}), "control")
        self.assertEqual(classify_event_phase({"event_type": "llm_call"}), "execution")
        self.assertEqual(classify_event_phase({"event_type": "memory_mutation"}), "mutation")
        self.assertEqual(classify_event_phase({"event_type": "state"}), "state")


class TestExecutionGraph(unittest.TestCase):
    def test_semantic_edges_preferred(self):
        events = [
            {
                "event_id": "e1",
                "trace_id": "t1",
                "timestamp": "2026-01-01T00:00:00Z",
                "event_type": "dispatch",
            },
            {
                "event_id": "e2",
                "trace_id": "t1",
                "timestamp": "2026-01-01T00:00:01Z",
                "event_type": "recall",
                "causal_edges": [
                    {"from": "e1", "to": "e2", "relation": "triggered_by"},
                ],
            },
            {
                "event_id": "e3",
                "trace_id": "t1",
                "timestamp": "2026-01-01T00:00:02Z",
                "event_type": "state",
                "causal_edges": [
                    {"from": "e2", "to": "e3", "relation": "triggered_by"},
                ],
            },
        ]
        graph = build_execution_graph("t1", events)
        self.assertEqual(len(graph.nodes), 3)
        kinds = {e.kind for e in graph.edges}
        self.assertIn("triggers", kinds)
        bound = bind_explanation_to_execution({"narrative": "x"}, graph)
        self.assertIn("execution_path", bound)
        self.assertTrue(bound["execution_path_labels"])


class TestQueryExecutionLayer(unittest.TestCase):
    def test_run_query_includes_execution(self):
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        log = SpineEventLog(tmp.name)
        rows = [
            {
                "event_id": "e1",
                "trace_id": "t-ex",
                "timestamp": "2026-06-14T00:00:01+00:00",
                "event_type": "dispatch",
                "subsystem": "control_plane",
                "action": "read",
                "summary": "dispatch",
            },
            {
                "event_id": "e2",
                "trace_id": "t-ex",
                "timestamp": "2026-06-14T00:00:02+00:00",
                "event_type": "recall",
                "subsystem": "runtime",
                "action": "read",
                "summary": "recall",
                "causal_edges": [{"from": "e1", "to": "e2", "relation": "triggered_by"}],
            },
        ]
        for row in rows:
            log.append(SpineEvent.from_dict(row))

        result = run_query(tmp.name, trace_id="t-ex")
        body = result.to_dict()
        self.assertIn("execution", body)
        self.assertEqual(body["execution"]["trace_id"], "t-ex")
        self.assertIn("execution_path", body["explanation"])
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

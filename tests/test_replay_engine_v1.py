"""Execution Replay Engine v1 + ExecutionRecord consolidation."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.graph.builder import GraphBuilder
from core.kernel.identity.index_v1 import reset_identity_graph_index
from core.kernel.intent import ExecutionIntent
from core.kernel.kernel import ExecutionKernel
from core.kernel.record import ExecutionRecord, RECORD_VERSION
from core.runtime.execution_tap import reset_execution_tap


class TestExecutionRecord(unittest.TestCase):
    def test_materialize_single_node(self):
        from core.kernel.context import ExecutionContext

        intent = ExecutionIntent(type="recall", payload={"query": "q"})
        ctx = ExecutionContext(trace_id="t1")
        record = ExecutionRecord.materialize(intent=intent, ctx=ctx, result="hit")
        self.assertEqual(record.version, RECORD_VERSION)
        self.assertEqual(record.to_legacy_response(), "hit")

    def test_to_dict_contains_truth_fields(self):
        from core.kernel.context import ExecutionContext

        graph = GraphBuilder().build(intent := ExecutionIntent(type="recall", payload={"query": "q"}), "t")
        ctx = ExecutionContext(trace_id="t")
        record = ExecutionRecord.materialize(
            intent=intent,
            ctx=ctx,
            result={"ok": True},
            graph=graph,
            identity_info={"identity": "I-test", "equivalence": {"count": 0}},
        )
        data = record.to_dict()
        self.assertEqual(data["identity"], "I-test")
        self.assertTrue(data["nodes"])


class TestReplayEngineV1(unittest.TestCase):
    def setUp(self):
        reset_execution_tap()
        reset_identity_graph_index()

    def test_replay_consistent_identity(self):
        runtime = MagicMock()
        runtime.recall.return_value = "ctx"
        kernel = ExecutionKernel(runtime)

        with patch("core.kernel.hooks.enqueue_spine_event"):
            record = kernel.execute(
                ExecutionIntent(type="recall", payload={"query": "alpha"}, trace_id="trace-r1")
            )

        with patch("core.kernel.hooks.enqueue_spine_event"):
            replay = kernel.replay(trace_id="trace-r1")

        self.assertEqual(replay["replay_status"], "consistent")
        self.assertTrue(replay["identity_match"])
        self.assertEqual(replay["identity"], record.identity)
        self.assertTrue(replay["replay_signature"].startswith("R-"))

    def test_replay_from_graph_without_stored_trace(self):
        runtime = MagicMock()
        runtime.recall.return_value = "x"
        kernel = ExecutionKernel(runtime)
        graph = GraphBuilder().build(
            ExecutionIntent(type="recall", payload={"query": "z"}),
            "trace-x",
        )

        with patch("core.kernel.hooks.enqueue_spine_event"):
            replay = kernel.replay(graph, verify_identity=False)

        self.assertEqual(replay["replay_status"], "replayed")
        self.assertIn("replay_result", replay)


if __name__ == "__main__":
    unittest.main()

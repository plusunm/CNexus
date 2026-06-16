"""Scheduler v2 — wave parallelism, join barriers, failure propagation."""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.context import ExecutionContext
from core.kernel.graph.execution_graph import (
    KernelExecutionGraph,
    KernelGraphEdge,
    KernelGraphNode,
    new_node_id,
)
from core.kernel.graph.scheduler_v2 import SchedulerV2
from core.kernel.intent import ExecutionIntent


def _fanout_graph() -> KernelExecutionGraph:
    """A fans out to B and C, then D joins B+C."""
    a, b, c, d = new_node_id("a"), new_node_id("b"), new_node_id("c"), new_node_id("d")
    nodes = [
        KernelGraphNode(
            node_id=a,
            intent=ExecutionIntent(type="recall", payload={"query": "seed"}),
            label="seed",
        ),
        KernelGraphNode(
            node_id=b,
            intent=ExecutionIntent(type="recall", payload={"query": "b"}),
            label="branch_b",
            depends_on=[a],
        ),
        KernelGraphNode(
            node_id=c,
            intent=ExecutionIntent(type="recall", payload={"query": "c"}),
            label="branch_c",
            depends_on=[a],
        ),
        KernelGraphNode(
            node_id=d,
            intent=ExecutionIntent(type="chat", payload={"message": "join", "use_memory": False}),
            label="join_chat",
            depends_on=[b, c],
        ),
    ]
    edges = [
        KernelGraphEdge(from_id=a, to_id=b, kind="fork"),
        KernelGraphEdge(from_id=a, to_id=c, kind="fork"),
        KernelGraphEdge(from_id=b, to_id=d, kind="join"),
        KernelGraphEdge(from_id=c, to_id=d, kind="join"),
    ]
    return KernelExecutionGraph(
        trace_id="trace-fan",
        nodes=nodes,
        edges=edges,
        root_node_ids=[a],
        join_node_id=d,
    )


class TestSchedulerV2Parallel(unittest.TestCase):
    def test_fanout_wave_executes_branches(self):
        runtime = MagicMock()
        runtime.recall.return_value = "ok"
        runtime.process_interaction.return_value = {"reply": "done"}

        graph = _fanout_graph()
        ctx = ExecutionContext(trace_id="trace-fan")

        with patch.dict(os.environ, {"USE_SCHEDULER_V2": "1"}):
            result = SchedulerV2().run(graph, ctx, runtime)

        self.assertEqual(runtime.recall.call_count, 3)
        self.assertEqual(runtime.process_interaction.call_count, 1)
        self.assertEqual(result.get("scheduler"), "v2")
        self.assertIn("graph_invariant", result)

    def test_parallel_wave_timing(self):
        runtime = MagicMock()
        delays: dict[str, float] = {}

        def slow_recall(query, **kwargs):
            time.sleep(0.05)
            delays[query] = time.time()
            return query

        runtime.recall.side_effect = slow_recall
        runtime.process_interaction.return_value = {"reply": "x"}

        graph = _fanout_graph()
        ctx = ExecutionContext(trace_id="trace-fan")

        SchedulerV2(max_parallelism=4).run(graph, ctx, runtime)

        # b and c should start close together (same wave)
        if "b" in delays and "c" in delays:
            self.assertLess(abs(delays["b"] - delays["c"]), 0.04)


class TestSchedulerV2Failure(unittest.TestCase):
    def test_fail_fast_halts_graph(self):
        runtime = MagicMock()

        def recall_side_effect(query, **kwargs):
            if query == "b":
                raise RuntimeError("boom")
            return query

        runtime.recall.side_effect = recall_side_effect
        graph = _fanout_graph()
        ctx = ExecutionContext(trace_id="trace-fan")

        result = SchedulerV2(failure_policy="fail_fast").run(graph, ctx, runtime)

        self.assertTrue(result.get("halted"))
        self.assertIn("node_errors", result)
        runtime.process_interaction.assert_not_called()

    def test_skip_dependents_skips_join(self):
        runtime = MagicMock()

        def recall_side_effect(query, **kwargs):
            if query == "c":
                raise RuntimeError("branch failed")
            return query

        runtime.recall.side_effect = recall_side_effect
        graph = _fanout_graph()
        ctx = ExecutionContext(trace_id="trace-fan")

        result = SchedulerV2(failure_policy="skip_dependents").run(graph, ctx, runtime)

        self.assertTrue(any("branch failed" in str(v) for v in result.get("node_errors", {}).values()))
        self.assertIn(graph.join_node_id, result.get("skipped_nodes", []))
        runtime.process_interaction.assert_not_called()


class TestGraphTopologicalGenerations(unittest.TestCase):
    def test_generations_on_graph_object(self):
        graph = _fanout_graph()
        gens = graph.topological_generations()
        self.assertEqual(len(gens), 3)
        self.assertEqual(len(gens[1]), 2)


if __name__ == "__main__":
    unittest.main()

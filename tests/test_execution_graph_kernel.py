"""Execution Graph Kernel v1 — DAG builder, resolver, scheduler."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.graph.builder import GraphBuilder
from core.kernel.graph.execution_graph import KernelExecutionGraph, KernelGraphEdge, KernelGraphNode, new_node_id
from core.kernel.graph.resolver import GraphResolutionError, topological_generations, topological_order, validate_acyclic
from core.kernel.graph.scheduler import GraphScheduler
from core.kernel.intent import ExecutionIntent
from core.kernel.kernel import ExecutionKernel, graph_enabled
from core.runtime.execution_tap import reset_execution_tap


class TestGraphBuilder(unittest.TestCase):
    def test_single_intent_graph(self):
        intent = ExecutionIntent(type="recall", payload={"query": "x"})
        graph = GraphBuilder().build(intent, "trace-1")
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(graph.nodes[0].intent.type, "recall")

    def test_chat_expands_to_dag(self):
        intent = ExecutionIntent(
            type="chat",
            payload={"message": "hello", "use_memory": True},
        )
        graph = GraphBuilder().build(intent, "trace-2", tier="T3")
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.edges[0].kind, "join")
        self.assertEqual(graph.join_node_id, graph.nodes[1].node_id)

    def test_invariant_hash_stable(self):
        intent = ExecutionIntent(type="capture", payload={"role": "user", "content": "c"})
        g1 = GraphBuilder().build(intent, "t")
        g2 = GraphBuilder().build(intent, "t")
        self.assertEqual(g1.invariant_hash(), g2.invariant_hash())


class TestGraphResolver(unittest.TestCase):
    def _sample_graph(self) -> KernelExecutionGraph:
        a, b, c = new_node_id("a"), new_node_id("b"), new_node_id("c")
        nodes = [
            KernelGraphNode(node_id=a, intent=ExecutionIntent(type="recall", payload={"query": "1"}), label="a"),
            KernelGraphNode(
                node_id=b,
                intent=ExecutionIntent(type="recall", payload={"query": "2"}),
                label="b",
                depends_on=[a],
            ),
            KernelGraphNode(
                node_id=c,
                intent=ExecutionIntent(type="chat", payload={"message": "hi"}),
                label="c",
                depends_on=[b],
            ),
        ]
        edges = [
            KernelGraphEdge(from_id=a, to_id=b, kind="depends"),
            KernelGraphEdge(from_id=b, to_id=c, kind="join"),
        ]
        return KernelExecutionGraph(trace_id="t", nodes=nodes, edges=edges, root_node_ids=[a], join_node_id=c)

    def test_topological_order(self):
        graph = self._sample_graph()
        order = [n.node_id for n in topological_order(graph)]
        self.assertEqual(order[0], graph.root_node_ids[0])
        self.assertEqual(order[-1], graph.join_node_id)

    def test_generations_show_parallel_potential(self):
        graph = self._sample_graph()
        gens = topological_generations(graph)
        self.assertEqual(len(gens), 3)

    def test_cycle_raises(self):
        a, b = new_node_id(), new_node_id()
        nodes = [
            KernelGraphNode(node_id=a, intent=ExecutionIntent(type="recall", payload={"query": "1"}), depends_on=[b]),
            KernelGraphNode(node_id=b, intent=ExecutionIntent(type="chat", payload={"message": "x"}), depends_on=[a]),
        ]
        graph = KernelExecutionGraph(trace_id="t", nodes=nodes, edges=[])
        with self.assertRaises(GraphResolutionError):
            validate_acyclic(graph)


class TestGraphScheduler(unittest.TestCase):
    def test_runs_nodes_in_order(self):
        runtime = MagicMock()
        runtime.recall.return_value = "ctx"
        runtime.process_interaction.return_value = {"reply": "ok"}

        intent = ExecutionIntent(type="chat", payload={"message": "hi", "use_memory": True})
        graph = GraphBuilder().build(intent, "trace-s", tier="T3")
        from core.kernel.context import ExecutionContext

        ctx = ExecutionContext(trace_id="trace-s")
        result = GraphScheduler().run(graph, ctx, runtime)

        self.assertEqual(runtime.recall.call_count, 1)
        self.assertEqual(runtime.process_interaction.call_count, 1)
        self.assertIn("execution_graph", result)
        self.assertIn("graph_invariant", result)


class TestKernelGraphIntegration(unittest.TestCase):
    def setUp(self):
        reset_execution_tap()

    def test_kernel_uses_graph_by_default(self):
        runtime = MagicMock()
        runtime.recall.return_value = "mem"
        runtime.process_interaction.return_value = {"reply": "yes"}
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "1"}):
            with patch("core.kernel.hooks.enqueue_spine_event"):
                record = kernel.execute(
                    ExecutionIntent(type="chat", payload={"message": "test", "use_memory": True})
                )

        self.assertTrue(graph_enabled())
        self.assertIsNotNone(record.graph_invariant)
        self.assertEqual(len(record.nodes), 1)
        runtime.recall.assert_not_called()
        runtime.process_interaction.assert_called_once()


if __name__ == "__main__":
    unittest.main()

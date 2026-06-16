"""Graph Identity Kernel v1 + Identity Graph Index v1."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.graph.builder import GraphBuilder
from core.kernel.graph.execution_graph import KernelExecutionGraph, KernelGraphEdge, KernelGraphNode, new_node_id
from core.kernel.identity.graph_identity_v1 import GraphIdentityV1
from core.kernel.identity.index_v1 import IdentityGraphIndexV1, reset_identity_graph_index
from core.kernel.intent import ExecutionIntent


class TestGraphIdentityV1(unittest.TestCase):
    def setUp(self):
        self.kernel = GraphIdentityV1()

    def test_same_structure_different_node_ids_equivalent(self):
        g1 = GraphBuilder().build(
            ExecutionIntent(type="chat", payload={"message": "hi", "use_memory": True}),
            "t1",
        )
        g2 = GraphBuilder().build(
            ExecutionIntent(type="chat", payload={"message": "hi", "use_memory": True}),
            "t2",
        )
        self.assertTrue(self.kernel.equivalent(g1, g2))
        self.assertEqual(self.kernel.compute_identity(g1), self.kernel.compute_identity(g2))

    def test_trace_id_noise_does_not_affect_identity(self):
        intent_a = ExecutionIntent(type="recall", payload={"query": "x", "trace_id": "noise-a"})
        intent_b = ExecutionIntent(type="recall", payload={"query": "x", "trace_id": "noise-b"})
        g1 = GraphBuilder().build(intent_a, "t1")
        g2 = GraphBuilder().build(intent_b, "t2")
        self.assertEqual(self.kernel.compute_identity(g1), self.kernel.compute_identity(g2))

    def test_different_intent_not_equivalent(self):
        g1 = GraphBuilder().build(ExecutionIntent(type="recall", payload={"query": "a"}), "t1")
        g2 = GraphBuilder().build(ExecutionIntent(type="capture", payload={"role": "u", "content": "c"}), "t2")
        self.assertFalse(self.kernel.equivalent(g1, g2))

    def test_identity_prefix(self):
        g = GraphBuilder().build(ExecutionIntent(type="recall", payload={"query": "z"}), "t")
        self.assertTrue(self.kernel.compute_identity(g).startswith("I-"))


class TestIdentityGraphIndexV1(unittest.TestCase):
    def setUp(self):
        reset_identity_graph_index()
        self.index = IdentityGraphIndexV1()

    def test_register_and_lookup(self):
        graph = GraphBuilder().build(ExecutionIntent(type="recall", payload={"query": "q"}), "trace-1")
        identity = self.index.register("trace-1", graph)
        self.assertEqual(self.index.get_identity("trace-1"), identity)

    def test_equivalent_traces_cross_retrieval(self):
        graph = GraphBuilder().build(ExecutionIntent(type="recall", payload={"query": "q"}), "t")
        id1 = self.index.register("trace-a", graph)
        graph2 = GraphBuilder().build(ExecutionIntent(type="recall", payload={"query": "q"}), "t2")
        id2 = self.index.register("trace-b", graph2)
        self.assertEqual(id1, id2)

        eq = self.index.find_equivalent_traces(graph2, exclude_trace="trace-b")
        self.assertEqual(eq["count"], 1)
        self.assertIn("trace-a", eq["equivalent_traces"])

    def test_stats(self):
        graph = GraphBuilder().build(ExecutionIntent(type="recall", payload={"query": "q"}), "t")
        self.index.register("trace-a", graph)
        stats = self.index.stats()
        self.assertEqual(stats["unique_identities"], 1)
        self.assertEqual(stats["total_traces"], 1)


if __name__ == "__main__":
    unittest.main()

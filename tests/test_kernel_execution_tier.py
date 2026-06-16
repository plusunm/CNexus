"""Execution tier routing — kernel performance split v1."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.graph.builder import GraphBuilder
from core.kernel.intent import ExecutionIntent
from core.kernel.kernel import ExecutionKernel
from core.kernel.record import LazyExecutionRecord
from core.kernel.tier.resolver import resolve_execution_tier
from core.runtime.execution_tap import get_execution_tap, reset_execution_tap
from core.kernel.hooks import flush_observability_queues, reset_observability_workers


class TestTierResolver(unittest.TestCase):
    def test_chat_default_t2(self):
        intent = ExecutionIntent(type="chat", payload={"message": "hi", "use_memory": True})
        self.assertEqual(resolve_execution_tier(intent), "T2")

    def test_fast_t0(self):
        intent = ExecutionIntent(type="chat", payload={"message": "hi", "fast": True})
        self.assertEqual(resolve_execution_tier(intent), "T0")

    def test_no_memory_t1(self):
        intent = ExecutionIntent(type="chat", payload={"message": "hi", "use_memory": False})
        self.assertEqual(resolve_execution_tier(intent), "T1")

    def test_deep_reasoning_t3(self):
        intent = ExecutionIntent(
            type="chat",
            payload={"message": "hi", "use_memory": True, "deep_reasoning": True},
        )
        self.assertEqual(resolve_execution_tier(intent), "T3")

    def test_non_chat_t3(self):
        intent = ExecutionIntent(type="recall", payload={"query": "x"})
        self.assertEqual(resolve_execution_tier(intent), "T3")


class TestGraphBuilderTier(unittest.TestCase):
    def test_t2_single_node_chat(self):
        intent = ExecutionIntent(type="chat", payload={"message": "hello", "use_memory": True})
        graph = GraphBuilder().build(intent, "trace-t2", tier="T2")
        self.assertEqual(len(graph.nodes), 1)

    def test_t3_recall_chat_dag(self):
        intent = ExecutionIntent(type="chat", payload={"message": "hello", "use_memory": True})
        graph = GraphBuilder().build(intent, "trace-t3", tier="T3")
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)


class TestKernelExecutionTier(unittest.TestCase):
    def setUp(self):
        reset_execution_tap()
        reset_observability_workers()
        os.environ["KERNEL_TAP_SYNC"] = "1"

    def tearDown(self):
        os.environ.pop("KERNEL_TAP_SYNC", None)
        flush_observability_queues()

    def test_t0_no_graph(self):
        runtime = MagicMock()
        runtime.recall.return_value = "prefetched"
        runtime.process_interaction.return_value = {"reply": "fast"}
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "1", "KERNEL_ENFORCE_MODE": "0"}):
            record = kernel.execute(
                ExecutionIntent(type="chat", payload={"message": "ping", "fast": True})
            )

        self.assertIsNone(record.graph)
        self.assertEqual(record.derivation.get("execution_tier"), "T0")
        self.assertIsInstance(record, LazyExecutionRecord)
        runtime.recall.assert_called_once()
        runtime.process_interaction.assert_called_once()

    def test_t1_no_graph_no_recall(self):
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"reply": "light"}
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "1", "KERNEL_ENFORCE_MODE": "0"}):
            record = kernel.execute(
                ExecutionIntent(
                    type="chat",
                    payload={"message": "ping", "use_memory": False},
                )
            )

        self.assertIsNone(record.graph)
        self.assertEqual(record.derivation.get("execution_tier"), "T1")
        runtime.recall.assert_not_called()

    def test_t2_single_recall(self):
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"reply": "ok"}
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "1", "KERNEL_ENFORCE_MODE": "0"}):
            record = kernel.execute(
                ExecutionIntent(type="chat", payload={"message": "test", "use_memory": True})
            )

        self.assertIsNotNone(record.graph_invariant)
        self.assertEqual(len(record.nodes), 1)
        runtime.recall.assert_not_called()
        runtime.process_interaction.assert_called_once()

    def test_recall_prefetch_single_call_t3(self):
        runtime = MagicMock()
        runtime.recall.return_value = "mem hits"
        runtime.process_interaction.return_value = {"reply": "yes"}

        def capture_interaction(*args, **kwargs):
            meta = kwargs.get("metadata") or {}
            self.assertEqual(meta.get("recall_prefetch"), "mem hits")
            return {"reply": "yes"}

        runtime.process_interaction.side_effect = capture_interaction
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "1", "KERNEL_ENFORCE_MODE": "0"}):
            kernel.execute(
                ExecutionIntent(
                    type="chat",
                    payload={"message": "test", "use_memory": True, "deep_reasoning": True},
                )
            )

        runtime.recall.assert_called_once()
        runtime.process_interaction.assert_called_once()

    def test_lazy_record_materialization(self):
        runtime = MagicMock()
        runtime.recall.return_value = "ctx"
        runtime.process_interaction.return_value = {"reply": "lazy"}
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "1", "KERNEL_ENFORCE_MODE": "0"}):
            record = kernel.execute(
                ExecutionIntent(type="chat", payload={"message": "x", "fast": True})
            )

        self.assertFalse(record._expanded)
        data = record.to_dict()
        self.assertTrue(record._expanded)
        self.assertIn("causal_projection", data)
        self.assertEqual(data["derivation"]["execution_tier"], "T0")

    def test_tap_records_with_sync_mode(self):
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"reply": "tap"}
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "1", "KERNEL_ENFORCE_MODE": "0"}):
            record = kernel.execute(
                ExecutionIntent(type="chat", payload={"message": "tap", "fast": True})
            )

        events = get_execution_tap().events_for_trace(record.trace_id)
        phases = {e["payload"].get("phase") for e in events}
        self.assertIn("enter_kernel", phases)
        self.assertIn("after_execute", phases)


if __name__ == "__main__":
    unittest.main()

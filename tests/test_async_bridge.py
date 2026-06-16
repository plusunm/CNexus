"""async_bridge — safe coroutine execution from sync/async mixed stacks."""

import asyncio
import unittest

from core.runtime.async_bridge import run_coro_sync


class TestAsyncBridge(unittest.TestCase):
    def test_run_coro_sync_without_loop(self):
        async def _add() -> int:
            return 40 + 2

        self.assertEqual(run_coro_sync(_add()), 42)

    def test_run_coro_sync_from_running_loop(self):
        async def _inner() -> int:
            return run_coro_sync(_worker())

        async def _worker() -> int:
            await asyncio.sleep(0)
            return 7

        self.assertEqual(asyncio.run(_inner()), 7)


class TestSchedulerV2FromLoop(unittest.TestCase):
    def test_scheduler_run_inside_asyncio_loop(self):
        from unittest.mock import MagicMock

        from core.kernel.context import ExecutionContext
        from core.kernel.graph.execution_graph import KernelExecutionGraph, KernelGraphNode
        from core.kernel.graph.scheduler_v2 import SchedulerV2
        from core.kernel.intent import ExecutionIntent

        intent = ExecutionIntent(type="chat", payload={"message": "hi", "_action": "prepare"})
        node = KernelGraphNode(node_id="n1", intent=intent, label="chat")
        graph = KernelExecutionGraph(trace_id="t-1", nodes=[node], root_node_ids=["n1"], join_node_id="n1")
        ctx = ExecutionContext(trace_id="t-1")
        runtime = MagicMock()
        runtime.prepare_chat_turn.return_value = {"prepare_id": "p1"}

        async def _run() -> None:
            result = SchedulerV2().run(graph, ctx, runtime)
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("prepare_id"), "p1")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()

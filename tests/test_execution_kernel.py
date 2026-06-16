"""CP-3 Execution Kernel — routing, tap, and dispatcher bridge."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.types import DispatchContext, RouteKind, build_dispatch_context
from core.kernel.context import ExecutionContext
from core.kernel.intent import ExecutionIntent, dispatch_context_to_intent
from core.kernel.kernel import ExecutionKernel, kernel_enabled
from core.kernel.registry import all_capabilities, resolve_handler
from core.kernel.router import route_intent
from core.runtime.execution_tap import reset_execution_tap


class TestIntentBridge(unittest.TestCase):
    def test_dispatch_chat_to_intent(self):
        ctx = build_dispatch_context(
            RouteKind.CHAT_SEND,
            {"message": "hello"},
            trace_id="trace-abc",
        )
        intent = dispatch_context_to_intent(ctx)
        self.assertEqual(intent.type, "chat")
        self.assertEqual(intent.payload["message"], "hello")
        self.assertEqual(intent.trace_id, "trace-abc")

    def test_dispatch_recall_to_intent(self):
        ctx = build_dispatch_context(RouteKind.MEMORY_READ, {"query": "test"})
        intent = dispatch_context_to_intent(ctx)
        self.assertEqual(intent.type, "recall")

    def test_prepare_action_tagged(self):
        ctx = build_dispatch_context(RouteKind.CHAT_PREPARE, {"message": "hi"})
        intent = dispatch_context_to_intent(ctx)
        self.assertEqual(intent.payload["_action"], "prepare")


class TestRouter(unittest.TestCase):
    def test_route_recall(self):
        runtime = MagicMock()
        runtime.recall.return_value = "mem"
        ctx = ExecutionContext(trace_id="t1")
        intent = ExecutionIntent(type="recall", payload={"query": "q"})
        out = route_intent(intent, ctx, runtime)
        self.assertEqual(out, "mem")
        runtime.recall.assert_called_once()

    def test_route_chat_send(self):
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"reply": "ok"}
        ctx = ExecutionContext(trace_id="t2")
        intent = ExecutionIntent(type="chat", payload={"message": "hello"})
        out = route_intent(intent, ctx, runtime)
        self.assertEqual(out["reply"], "ok")


class TestKernelExecute(unittest.TestCase):
    def setUp(self):
        reset_execution_tap()
        os.environ["KERNEL_TAP_SYNC"] = "1"

    def tearDown(self):
        os.environ.pop("KERNEL_TAP_SYNC", None)

    def test_kernel_records_tap(self):
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"reply": "x"}
        kernel = ExecutionKernel(runtime)
        record = kernel.execute(
            ExecutionIntent(type="chat", payload={"message": "ping"}, source="test")
        )
        self.assertEqual(record.trace_id, record.to_dict()["trace_id"])
        from core.runtime.execution_tap import get_execution_tap

        events = get_execution_tap().events_for_trace(record.trace_id)
        phases = {e["payload"].get("phase") for e in events}
        self.assertIn("enter_kernel", phases)
        self.assertIn("exit_kernel", phases)

    def test_kernel_enabled_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("USE_EXECUTION_KERNEL", None)
            self.assertTrue(kernel_enabled())


class TestRegistry(unittest.TestCase):
    def test_capabilities_cover_core_intents(self):
        caps = all_capabilities()
        for name in ("chat", "recall", "capture", "ir_exec"):
            self.assertIn(name, caps)
            self.assertTrue(resolve_handler(name))


class TestDispatcherKernelBridge(unittest.TestCase):
    def test_dispatcher_execute_delegates_to_kernel(self):
        from core.control_plane.dispatch import AuthorityDispatcher

        runtime = MagicMock()
        runtime.recall.return_value = "found"
        dispatcher = AuthorityDispatcher(runtime)
        ctx = DispatchContext(
            kind=RouteKind.MEMORY_READ,
            payload={"query": "alpha"},
            trace_id="trace-k1",
        )

        with patch.dict(os.environ, {"USE_EXECUTION_KERNEL": "1", "KERNEL_ENFORCE_MODE": "0"}):
            with patch("core.kernel.hooks.enqueue_spine_event"):
                out = dispatcher._execute(ctx)

        self.assertEqual(out, "found")
        runtime.recall.assert_called_once()


if __name__ == "__main__":
    unittest.main()

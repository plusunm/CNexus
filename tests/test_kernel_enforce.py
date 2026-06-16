"""Kernel Enforce Mode v1 — reality gate contract tests."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.types import DispatchContext, RouteKind
from core.kernel.enforce.exceptions import KernelViolation
from core.kernel.enforce.gate import get_enforce_gate
from core.kernel.enforce.mode import enforce_mode, execution_via_kernel_required
from core.kernel.hooks import record_execution_tap
from core.kernel.intent import ExecutionIntent
from core.kernel.kernel import ExecutionKernel
from core.kernel.migration.runtime_proxy import RuntimeProxy
from core.runtime.execution_tap import reset_execution_tap


class TestEnforceModeFlags(unittest.TestCase):
    def test_enforce_default_on(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KERNEL_ENFORCE_MODE", None)
            self.assertTrue(enforce_mode())

    def test_execution_via_kernel_when_enforce(self):
        with patch.dict(os.environ, {"KERNEL_ENFORCE_MODE": "1", "USE_EXECUTION_KERNEL": "0"}):
            self.assertTrue(execution_via_kernel_required())


class TestEnforceGate(unittest.TestCase):
    def test_legacy_route_blocked(self):
        with patch.dict(os.environ, {"KERNEL_ENFORCE_MODE": "1"}):
            with self.assertRaises(KernelViolation):
                get_enforce_gate().block_legacy_route("memory_read")

    def test_bypass_blocked_on_proxy(self):
        runtime = MagicMock()
        runtime.recall.return_value = "x"
        kernel = MagicMock()
        proxy = RuntimeProxy(runtime, kernel)

        with patch.dict(os.environ, {"KERNEL_ENFORCE_MODE": "1"}):
            with self.assertRaises(KernelViolation):
                proxy.recall("q", _bypass_kernel=True)

    def test_tap_outside_kernel_dropped(self):
        reset_execution_tap()
        with patch.dict(os.environ, {"KERNEL_ENFORCE_MODE": "1"}):
            record_execution_tap({"trace_id": "t", "phase": "outside"})
        from core.runtime.execution_tap import get_execution_tap

        self.assertEqual(len(get_execution_tap().events_for_trace("t")), 0)


class TestDispatcherEnforce(unittest.TestCase):
    def test_legacy_blocked_when_enforce(self):
        from core.control_plane.dispatch import AuthorityDispatcher

        runtime = MagicMock()
        dispatcher = AuthorityDispatcher(runtime)
        ctx = DispatchContext(kind=RouteKind.MEMORY_READ, payload={"query": "x"})

        with patch.dict(os.environ, {"KERNEL_ENFORCE_MODE": "1", "USE_EXECUTION_KERNEL": "0"}):
            runtime.recall.return_value = "ok"
            with patch("core.kernel.hooks.enqueue_spine_event"):
                out = dispatcher._execute(ctx)
        self.assertEqual(out, "ok")


class TestKernelRecordValidation(unittest.TestCase):
    def test_record_validated_on_execute(self):
        runtime = MagicMock()
        runtime.recall.return_value = "hit"
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"KERNEL_ENFORCE_MODE": "1", "USE_EXECUTION_GRAPH": "1"}):
            with patch("core.kernel.hooks.enqueue_spine_event"):
                record = kernel.execute(ExecutionIntent(type="recall", payload={"query": "a"}))

        self.assertTrue(record.identity or record.graph_invariant)
        self.assertEqual(record.to_legacy_response(), "hit")

    def test_t2_chat_prepare_lazy_record_allowed(self):
        runtime = MagicMock()
        runtime.prepare_chat_turn.return_value = {"prepare_id": "p1", "user_message": "hi"}
        kernel = ExecutionKernel(runtime)

        with patch.dict(os.environ, {"KERNEL_ENFORCE_MODE": "1", "USE_EXECUTION_GRAPH": "1"}):
            with patch("core.kernel.hooks.enqueue_spine_event"):
                record = kernel.execute(
                    ExecutionIntent(
                        type="chat",
                        payload={"_action": "prepare", "message": "hi", "use_memory": True},
                    )
                )

        self.assertEqual(record.to_legacy_response()["prepare_id"], "p1")
        self.assertEqual((record.derivation or {}).get("execution_tier"), "T2")


if __name__ == "__main__":
    unittest.main()

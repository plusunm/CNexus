"""Execution Interceptor — RuntimeProxy migration layer."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.migration.auto_wrap import should_intercept
from core.kernel.migration.intent_mapper import map_runtime_call
from core.kernel.migration.patch_runtime import migration_enabled, patch_runtime
from core.kernel.migration.runtime_proxy import RuntimeProxy
from core.runtime.execution_tap import reset_execution_tap


class TestIntentMapper(unittest.TestCase):
    def test_maps_process_interaction(self):
        intent = map_runtime_call("process_interaction", ("hello",), {"use_memory": False})
        self.assertEqual(intent.type, "chat")
        self.assertEqual(intent.payload["message"], "hello")

    def test_maps_recall(self):
        intent = map_runtime_call("recall", ("query",), {"top_k": 3})
        self.assertEqual(intent.type, "recall")
        self.assertEqual(intent.payload["query"], "query")

    def test_maps_governance(self):
        intent = map_runtime_call("run_governance_cycle", (), {})
        self.assertEqual(intent.type, "cdg_apply")


class TestRuntimeProxy(unittest.TestCase):
    def setUp(self):
        reset_execution_tap()

    def test_intercepts_recall(self):
        runtime = MagicMock()
        runtime.recall.return_value = "hit"
        kernel = MagicMock()
        kernel.execute.return_value = "hit"
        proxy = RuntimeProxy(runtime, kernel)

        out = proxy.recall("alpha", top_k=2)

        self.assertEqual(out, "hit")
        kernel.execute.assert_called_once()
        runtime.recall.assert_not_called()

    def test_passthrough_read(self):
        runtime = MagicMock()
        runtime.get_current_state.return_value = {"ok": True}
        kernel = MagicMock()
        proxy = RuntimeProxy(runtime, kernel)

        out = proxy.get_current_state()

        self.assertEqual(out, {"ok": True})
        kernel.execute.assert_not_called()
        runtime.get_current_state.assert_called_once()

    def test_bypass_kernel(self):
        runtime = MagicMock()
        runtime.recall.return_value = "direct"
        kernel = MagicMock()
        proxy = RuntimeProxy(runtime, kernel)

        with patch.dict(os.environ, {"KERNEL_ENFORCE_MODE": "0"}):
            out = proxy.recall("q", _bypass_kernel=True)

        self.assertEqual(out, "direct")
        kernel.execute.assert_not_called()
        runtime.recall.assert_called_once()

    def test_no_recursion_via_kernel_internal(self):
        runtime = MagicMock()
        runtime.recall.return_value = "internal"
        kernel = MagicMock()
        proxy = RuntimeProxy(runtime, kernel)

        out = proxy.recall("q", _kernel_internal=True)

        self.assertEqual(out, "internal")
        kernel.execute.assert_not_called()


class TestPatchRuntime(unittest.TestCase):
    def test_patch_returns_proxy_when_enabled(self):
        runtime = MagicMock()
        with patch.dict(os.environ, {"KERNEL_MIGRATION_ENABLED": "1"}):
            facade = patch_runtime(runtime)
        self.assertIsInstance(facade, RuntimeProxy)
        self.assertIs(facade.unwrap(), runtime)

    def test_patch_passthrough_when_disabled(self):
        runtime = MagicMock()
        with patch.dict(os.environ, {"KERNEL_MIGRATION_ENABLED": "0"}):
            facade = patch_runtime(runtime)
        self.assertIs(facade, runtime)


class TestAutoWrapPolicy(unittest.TestCase):
    def test_intercepted_vs_read(self):
        self.assertTrue(should_intercept("recall"))
        self.assertTrue(should_intercept("process_interaction"))
        self.assertFalse(should_intercept("get_current_state"))
        self.assertFalse(should_intercept("memory_stats"))


if __name__ == "__main__":
    unittest.main()

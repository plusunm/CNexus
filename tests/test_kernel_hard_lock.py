"""Kernel Hard Lock — CP-3 final bypass elimination contract tests."""

from __future__ import annotations

import os
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.types import DispatchContext, RouteKind
from core.kernel.enforce.exceptions import KernelViolation
from core.kernel.enforce.mode import hard_lock_mode, legacy_allowed
from core.kernel.migration.runtime_proxy import RuntimeProxy


class TestHardLockFlags(unittest.TestCase):
    def test_hard_lock_default_on(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KERNEL_HARD_LOCK_MODE", None)
            self.assertTrue(hard_lock_mode())

    def test_legacy_disallowed_under_hard_lock(self):
        with patch.dict(os.environ, {"KERNEL_HARD_LOCK_MODE": "1"}):
            self.assertFalse(legacy_allowed())


class TestHardLockDispatcher(unittest.TestCase):
    def test_legacy_execute_raises_under_hard_lock(self):
        runtime = MagicMock()
        dispatcher = AuthorityDispatcher(runtime)
        ctx = DispatchContext(kind=RouteKind.MEMORY_READ, payload={"query": "x"})

        with patch.dict(
            os.environ,
            {
                "KERNEL_HARD_LOCK_MODE": "1",
                "KERNEL_ENFORCE_MODE": "0",
                "USE_EXECUTION_KERNEL": "0",
            },
        ):
            with self.assertRaises(KernelViolation):
                dispatcher._execute_legacy(ctx)

    def test_execute_routes_kernel_when_hard_lock(self):
        runtime = MagicMock()
        dispatcher = AuthorityDispatcher(runtime)
        record = MagicMock()
        record.to_legacy_response.return_value = {"ok": True}
        dispatcher._kernel.execute = MagicMock(return_value=record)
        ctx = DispatchContext(kind=RouteKind.MEMORY_READ, payload={"query": "x"})

        with patch.dict(
            os.environ,
            {"KERNEL_HARD_LOCK_MODE": "1", "USE_EXECUTION_KERNEL": "1"},
        ):
            out = dispatcher._execute(ctx)

        self.assertEqual(out, {"ok": True})
        dispatcher._kernel.execute.assert_called_once()


class TestHardLockRuntimeProxy(unittest.TestCase):
    def test_bypass_raises_under_hard_lock(self):
        runtime = MagicMock()
        kernel = MagicMock()
        proxy = RuntimeProxy(runtime, kernel)

        with patch.dict(os.environ, {"KERNEL_HARD_LOCK_MODE": "1", "KERNEL_ENFORCE_MODE": "0"}):
            with self.assertRaises(KernelViolation):
                proxy.recall("q", _bypass_kernel=True)


class TestHardLockApiContract(unittest.TestCase):
    def test_brain_memory_ui_openai_uses_legacy_adapter(self):
        path = os.path.join(ROOT, "brain-memory-ui", "api", "routes", "openai_compatible.py")
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("get_legacy_adapter", source)
        self.assertIn("legacy_adapter=legacy_adapter", source)
        self.assertNotRegex(source, r"Depends\(get_runtime\)")

    def test_ws_routes_support_legacy_adapter(self):
        path = os.path.join(ROOT, "api", "ws_routes.py")
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("get_legacy_adapter", source)
        self.assertIn("_legacy_adapter_provider", source)

    def test_chat_cancel_uses_dispatcher(self):
        path = os.path.join(ROOT, "brain-memory-ui", "api", "routes", "chat.py")
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("get_dispatcher().chat_cancel", source)
        self.assertNotRegex(source, r"runtime\.cancel_prepared_chat_turn")


class TestHardLockForbiddenPatterns(unittest.TestCase):
    FORBIDDEN = [
        (r"RuntimeProxy\._bypass_kernel", "core"),
        (r"def _bypass_kernel", "core"),
    ]

    def test_no_explicit_bypass_helpers_in_core(self):
        core_root = os.path.join(ROOT, "core")
        for dirpath, _, filenames in os.walk(core_root):
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    source = fh.read()
                for pattern, _ in self.FORBIDDEN:
                    if re.search(pattern, source):
                        self.fail(f"forbidden pattern {pattern!r} in {path}")


if __name__ == "__main__":
    unittest.main()

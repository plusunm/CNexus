"""Fix Contract L1/L2 — runtime must never construct on caller thread."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFixContractRuntimeIsolation(unittest.TestCase):
    def setUp(self):
        from api.runtime_warm_status import reset_runtime_warm_status

        reset_runtime_warm_status()

    def test_get_runtime_never_inline_creates(self):
        import api.deps as deps

        with patch.object(deps, "_runtime", None), patch.object(deps, "_runtime_warming", False):
            with patch.object(deps, "_create_runtime", side_effect=AssertionError("must not inline create")):
                with self.assertRaises(deps.RuntimeNotReady):
                    deps.get_runtime()

    def test_warm_thread_is_only_create_path(self):
        import api.deps as deps

        created = []

        def fake_create():
            created.append(True)
            return MagicMock()

        with patch.object(deps, "_runtime", None), patch.object(deps, "_runtime_warming", False):
            with patch.object(deps, "_create_runtime", side_effect=fake_create):
                deps.warm_runtime_background()
                import time

                deadline = time.time() + 2.0
                while not created and time.time() < deadline:
                    time.sleep(0.05)
        self.assertTrue(created, "warm_runtime_background must invoke _create_runtime on worker thread")

    def test_hydrate_sync_impl_exists_off_loop(self):
        from core.runtime.tap_bootstrap import hydrate_execution_stores_sync

        self.assertTrue(callable(hydrate_execution_stores_sync))

    def test_get_runtime_uses_peek_when_core_loaded(self):
        import api.deps as deps

        core = MagicMock(name="runtime_core")
        with patch.object(deps, "_runtime", None), patch.object(deps, "_runtime_core", core):
            self.assertIs(deps.get_runtime(), core)

    def test_get_runtime_raises_when_peek_empty(self):
        import api.deps as deps

        with patch.object(deps, "_runtime", None), patch.object(deps, "_runtime_core", None):
            with self.assertRaises(deps.RuntimeNotReady):
                deps.get_runtime()

    def test_warm_init_failure_records_error_and_cooldown(self):
        import api.deps as deps
        from api.runtime_warm_status import reset_runtime_warm_status, runtime_warm_meta

        reset_runtime_warm_status()
        with patch.object(deps, "_runtime", None), patch.object(deps, "_runtime_core", None):
            with patch.object(deps, "_runtime_warming", False):
                with patch.object(
                    deps,
                    "_create_runtime",
                    side_effect=ValueError("EmbeddingService requires plane or scheduler"),
                ):
                    deps.warm_runtime_background()
                    import time

                    deadline = time.time() + 2.0
                    while deps._runtime_warming and time.time() < deadline:
                        time.sleep(0.05)
        from api.runtime_warm_status import runtime_warm_meta

        self.assertIn("EmbeddingService", runtime_warm_meta().get("init_error") or "")
        self.assertFalse(deps.can_retry_runtime_warm())
        self.assertTrue(deps.can_retry_runtime_warm(force=True))


if __name__ == "__main__":
    unittest.main()

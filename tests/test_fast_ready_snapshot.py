"""Fast-Path v1 — snapshot ready without cluster / CRDT gates."""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.system_ready import mark_app_started, system_ready_payload
from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, set_boot_phase
from core.runtime.fast_ready_snapshot import fast_boot_mode_enabled, fast_ready_snapshot, should_use_fast_ready


class TestFastReadySnapshot(unittest.TestCase):
    def test_fast_snapshot_shape(self):
        snap = fast_ready_snapshot(
            MagicMock(),
            boot_id="test",
            app_started=True,
            mono_start=time.monotonic(),
        )
        self.assertEqual(snap["status"], "ready_fast")
        self.assertEqual(snap["ui"], "ok")
        self.assertEqual(snap["render_mode"], "fast_path_v1")
        self.assertEqual(snap["checks"]["cluster"], "deferred")
        self.assertEqual(snap["checks"]["cognitive"], "unknown")

    def test_should_use_fast_query_param(self):
        self.assertTrue(should_use_fast_ready(mode="fast", runtime=None))
        self.assertFalse(should_use_fast_ready(mode="full", runtime=None))

    def test_system_ready_payload_fast_mode(self):
        mark_app_started()
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        runtime = MagicMock()
        start = time.perf_counter()
        payload = system_ready_payload(runtime, mode="fast")
        elapsed = time.perf_counter() - start
        self.assertEqual(payload["status"], "ready_fast")
        self.assertLess(elapsed, 0.05)
        self.assertNotIn("cluster_ok", payload)

    def test_system_ready_payload_full_mode(self):
        mark_app_started()
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        runtime = MagicMock()
        with patch.dict(os.environ, {"CNEXUS_FAST_PATH_V1": "0"}, clear=False):
            payload = system_ready_payload(runtime, mode="full")
        self.assertIn(payload["status"], ("ready", "warming", "not_ready"))

    def test_fast_boot_mode_default_on(self):
        with patch.dict(os.environ, {"CNEXUS_FAST_PATH_V1": "1"}, clear=False):
            self.assertTrue(fast_boot_mode_enabled())


if __name__ == "__main__":
    unittest.main()

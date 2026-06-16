"""Boot Protocol v2 — non-blocking ready/health contract tests."""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.system_ready import mark_app_started, system_ready_payload, system_ready_warming_payload
from core.runtime.boot_protocol import (
    BootPhase,
    cognitive_disabled,
    fast_health_payload,
    get_boot_phase,
    mark_cognitive_warmup_done,
    mark_hydrate_complete,
    mark_runtime_spawned,
    set_boot_phase,
)


class TestBootProtocolFastPath(unittest.TestCase):
    def test_warming_payload_is_instant(self):
        mark_app_started()
        start = time.perf_counter()
        payload = system_ready_warming_payload()
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.05)
        self.assertEqual(payload["status"], "warming")
        self.assertIn("boot_phase", payload)

    def test_ready_payload_never_calls_get_current_state(self):
        mark_app_started()
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        runtime = MagicMock()
        runtime.get_current_state = MagicMock(side_effect=AssertionError("must not call get_current_state"))

        payload = system_ready_payload(runtime, mode="full")
        runtime.get_current_state.assert_not_called()
        self.assertEqual(payload["status"], "ready")

    def test_fast_health_no_table_scan(self):
        runtime = MagicMock()
        runtime.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        runtime.base_dir = os.path.join(runtime.project_root, "memory")
        runtime.storage = MagicMock()
        runtime.storage.vector.table.count_rows = MagicMock(
            side_effect=AssertionError("must not scan lance in fast health")
        )

        with patch.dict(os.environ, {"CNEXUS_DEPLOY_LEVEL": "dev"}):
            payload = fast_health_payload(runtime)

        runtime.storage.vector.table.count_rows.assert_not_called()
        self.assertEqual(payload.get("mode"), "fast")


class TestBootProtocolLockSafety(unittest.TestCase):
    def test_minimal_boot_mark_hydrate_does_not_deadlock(self):
        with patch.dict(os.environ, {"CNEXUS_MINIMAL_BOOT": "1"}, clear=False):
            mark_hydrate_complete()
        self.assertEqual(get_boot_phase(), BootPhase.BOOT_4_READY)

    def test_mark_cognitive_warmup_done_is_reentrant_safe(self):
        start = time.perf_counter()
        mark_cognitive_warmup_done()
        self.assertLess(time.perf_counter() - start, 0.05)
        self.assertEqual(get_boot_phase(), BootPhase.BOOT_4_READY)

    def test_mark_runtime_spawned_minimal_boot_stays_boot_4(self):
        with patch.dict(os.environ, {"CNEXUS_MINIMAL_BOOT": "1"}, clear=False):
            mark_hydrate_complete()
            mark_runtime_spawned()
        self.assertEqual(get_boot_phase(), BootPhase.BOOT_4_READY)


class TestSystemReadyEndpointContract(unittest.TestCase):
    def test_v1_ready_returns_200_while_warming(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.v1_endpoints import configure_v1_dependencies, router as v1_router

        mark_app_started()
        app = FastAPI()
        app.include_router(v1_router, prefix="/v1")
        configure_v1_dependencies(get_runtime=MagicMock())

        with patch("api.deps.peek_runtime", return_value=None):
            client = TestClient(app)
            resp = client.get("/v1/system/ready")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "warming")


if __name__ == "__main__":
    unittest.main()

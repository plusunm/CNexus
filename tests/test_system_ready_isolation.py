"""system_ready must use isolation path when CNEXUS_CONTROL_PLANE_ISOLATION=1."""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.system_ready import mark_app_started, system_ready_payload
from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, set_boot_phase
from core.runtime.control_plane_isolation import isolation_enabled


class TestSystemReadyIsolation(unittest.TestCase):
    def test_repo_root_system_ready_uses_isolation_fast_path(self):
        mark_app_started()
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        runtime = MagicMock()
        start = time.perf_counter()
        payload = system_ready_payload(runtime, mode="full")
        elapsed = time.perf_counter() - start
        self.assertTrue(isolation_enabled())
        self.assertIn(payload.get("isolation"), (
            "full_predictive_ui_runtime",
            "fast_path_v1",
            "cross_machine_cluster_v5",
            "deterministic_cluster_v4",
            "process_event_bus_v3",
            "non_hang_v2",
        ))
        self.assertIn("l3_ok", payload)
        self.assertIn("cognitive_ok", payload)
        self.assertLess(elapsed, 0.05)
        self.assertIn(payload["status"], ("ready", "warming", "not_ready"))


if __name__ == "__main__":
    unittest.main()

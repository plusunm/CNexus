"""Control Plane Isolation Kernel v1 tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.control_plane_isolation import (
    isolation_enabled,
    probe_event_loop,
    zero_dep_ready_payload,
)


class TestControlPlaneIsolation(unittest.TestCase):
    def test_isolation_enabled_by_default(self):
        self.assertTrue(isolation_enabled())

    def test_zero_dep_ready_is_fast_shape(self):
        payload = zero_dep_ready_payload(app_started=True, runtime_present=False)
        self.assertIn(payload["status"], ("warming", "not_ready", "ready"))
        self.assertTrue(payload.get("isolation"))
        self.assertIn("boot_phase", payload)

    def test_event_loop_probe(self):
        probe = probe_event_loop()
        self.assertIn("loop_running", probe)
        self.assertIn("probe_elapsed_ms", probe)
        self.assertLess(probe["probe_elapsed_ms"], 100)


if __name__ == "__main__":
    unittest.main()

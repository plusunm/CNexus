"""Non-Hang Kernel v2 tests."""

from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.non_hang_kernel_v2 import NonHangKernelV2
from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, ready_gate_snapshot, set_boot_phase
from core.runtime.event_loop_offload import offload_sync
from core.runtime.governance_signal_queue import drain_governance_signals, enqueue_governance_signal


class TestNonHangKernelV2(unittest.IsolatedAsyncioTestCase):
    async def test_run_bounded_async_timeout(self):
        kernel = NonHangKernelV2(max_workers=2)

        def slow() -> str:
            time.sleep(0.2)
            return "done"

        result = await kernel.run_bounded_async(slow, timeout_s=0.05)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "killed_timeout")
        kernel.shutdown()

    async def test_offload_sync_runs_off_loop(self):
        seen = {}

        def work() -> int:
            seen["ok"] = True
            return 7

        value = await offload_sync(work, timeout_s=2.0)
        self.assertEqual(value, 7)
        self.assertTrue(seen.get("ok"))


class TestGovernanceSignalQueue(unittest.TestCase):
    def test_enqueue_and_drain(self):
        while drain_governance_signals(limit=32):
            pass
        enqueue_governance_signal({"type": "GOVERNANCE_INIT"})
        drained = drain_governance_signals()
        self.assertEqual(len(drained), 1)
        self.assertEqual(drained[0]["type"], "GOVERNANCE_INIT")


class TestReadyGateSnapshot(unittest.TestCase):
    def test_ready_gate_fields(self):
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        snap = ready_gate_snapshot()
        self.assertIn("l3_ok", snap)
        self.assertIn("cognitive_ok", snap)
        self.assertIn("ready_gate_ok", snap)


if __name__ == "__main__":
    unittest.main()

"""Non-Hang Kernel v1 tests."""

from __future__ import annotations

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.non_hang_kernel import NonHangKernel
from core.runtime.boot_protocol import (
    BootPhase,
    evaluate_system_ready,
    mark_cognitive_warmup_done,
    set_boot_phase,
    set_l3_scheduler_status,
)
from core.runtime.l3_scheduler import L3GovernanceScheduler, L3TaskKind
from core.runtime.system_guard import governance_inline_on_l3_allowed, non_hang_kernel_enabled


class TestNonHangKernel(unittest.TestCase):
    def test_timeout_returns_killed_status(self):
        kernel = NonHangKernel(max_workers=2)

        def slow() -> str:
            time.sleep(0.2)
            return "done"

        result = kernel.run_bounded(slow, timeout_s=0.05)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "killed_timeout")
        kernel.shutdown()

    def test_fast_fn_completes(self):
        kernel = NonHangKernel(max_workers=2)
        result = kernel.run_bounded(lambda: 42, timeout_s=1.0)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, 42)
        kernel.shutdown()


class TestL3NonHangIsolation(unittest.TestCase):
    def test_slow_task_times_out_without_blocking_tick_forever(self):
        sched = L3GovernanceScheduler(time_slice_ms=50)
        sched.enqueue_batch([("slow", lambda: time.sleep(0.25), L3TaskKind.WARMUP, 5)])
        start = time.monotonic()
        result = sched.run_tick()
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.2)
        self.assertTrue(any(x.startswith("timeout:") for x in result.executed))


class TestAntiFalseReady(unittest.TestCase):
    def setUp(self):
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()

    def test_ready_blocked_when_l3_queue_nonempty(self):
        set_l3_scheduler_status({"queue_length": 2, "ticks": 1})
        self.assertEqual(
            evaluate_system_ready(
                app_started=True,
                runtime_present=True,
                runtime_warming=False,
                memory_ok=True,
            ),
            "warming",
        )

    def test_ready_when_l3_drained(self):
        set_l3_scheduler_status({"queue_length": 0, "ticks": 3})
        self.assertEqual(
            evaluate_system_ready(
                app_started=True,
                runtime_present=True,
                runtime_warming=False,
                memory_ok=True,
            ),
            "ready",
        )


class TestSystemGuard(unittest.TestCase):
    def test_governance_not_inline_by_default(self):
        self.assertTrue(non_hang_kernel_enabled())
        self.assertFalse(governance_inline_on_l3_allowed())

    def test_non_hang_v2_enabled_by_default(self):
        from core.runtime.system_guard import non_hang_v2_enabled

        self.assertTrue(non_hang_v2_enabled())


if __name__ == "__main__":
    unittest.main()

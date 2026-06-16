"""L3 scheduler tests."""

from __future__ import annotations

import unittest

from core.runtime.l3_scheduler import L3GovernanceScheduler, L3Task, L3TaskKind


class TestL3Scheduler(unittest.TestCase):
    def test_tick_returns_result_with_queue_empty(self):
        sched = L3GovernanceScheduler(time_slice_ms=30)
        sched.enqueue(L3Task(kind=L3TaskKind.WARMUP, fn=lambda: None, label="once"))
        result = sched.run_tick()
        self.assertTrue(result.queue_empty)
        self.assertEqual(result.remaining, 0)

    def test_enqueue_batch(self):
        sched = L3GovernanceScheduler(time_slice_ms=50)
        sched.enqueue_batch(
            [
                ("a", lambda: None, L3TaskKind.WARMUP, 5),
                ("b", lambda: None, L3TaskKind.WARMUP, 5),
            ]
        )
        self.assertEqual(sched.queue_length(), 2)
        result = sched.run_tick()
        self.assertTrue(result.queue_empty)


if __name__ == "__main__":
    unittest.main()

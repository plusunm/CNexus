"""Non-Hang Kernel v3 tests."""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.v3.event_bus import TOPIC_L3_DONE, TOPIC_L3_TASK, EventBus
from core.kernel.v3.l3_scheduler_v3 import L3SchedulerV3
from core.kernel.v3.process_isolated_executor import ProcessIsolatedExecutor
from core.kernel.v3.system_guard_v3 import enforce_v3_guards, non_hang_v3_enabled
from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, ready_gate_snapshot, set_boot_phase


class TestEventBus(unittest.TestCase):
    def test_publish_consume(self):
        bus = EventBus()
        bus.publish(TOPIC_L3_TASK, {"label": "a", "handler": "noop_ping"})
        event = bus.try_get(TOPIC_L3_TASK)
        self.assertIsNotNone(event)
        self.assertEqual(event["label"], "a")

    def test_idle_after_consume(self):
        bus = EventBus()
        bus.publish(TOPIC_L3_TASK, {"label": "a"})
        bus.try_get(TOPIC_L3_TASK)
        self.assertTrue(bus.is_idle())


class TestL3SchedulerV3(unittest.TestCase):
    def test_signal_only_tick_drains_done(self):
        from core.runtime.l3_scheduler import L3TaskKind

        bus = EventBus()
        sched = L3SchedulerV3(bus=bus)
        sched.enqueue_signal(label="a", handler="cdg_init", kind=L3TaskKind.WARMUP)
        self.assertEqual(sched.queue_length(), 1)
        bus.publish(TOPIC_L3_DONE, {"label": "a", "status": "ok"})
        result = sched.run_tick()
        self.assertTrue(result.queue_empty)


class TestV3Guards(unittest.TestCase):
    def test_v3_enabled_default(self):
        self.assertTrue(non_hang_v3_enabled())

    def test_ready_gate_v3_fields(self):
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        with patch.dict(os.environ, {"CNEXUS_NON_HANG_V4": "0", "CNEXUS_NON_HANG_V5": "0"}, clear=False):
            snap = ready_gate_snapshot()
        if non_hang_v3_enabled():
            self.assertIn("bus_idle", snap)
            self.assertEqual(snap.get("layer"), "v3")

    def test_enforce_v3_guards_shape(self):
        report = enforce_v3_guards()
        self.assertEqual(report.get("isolation"), "process_event_bus_v3")


class TestProcessExecutor(unittest.TestCase):
    def test_noop_ping(self):
        executor = ProcessIsolatedExecutor(processes=1)
        try:
            result = executor.run_named("noop_ping", timeout_s=5.0)
            self.assertTrue(result.ok)
        finally:
            executor.shutdown()


if __name__ == "__main__":
    unittest.main()

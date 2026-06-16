"""Non-Hang Kernel v4 tests."""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.v4.cluster_runtime import get_cluster_runtime
from core.kernel.v4.deterministic_log import DeterministicLog
from core.kernel.v4.l3_scheduler_v4 import L3SchedulerV4
from core.kernel.v4.replay_engine import ReplayEngine
from core.kernel.v4.system_guard_v4 import enforce_v4, non_hang_v4_enabled
from core.kernel.v3.event_bus import TOPIC_L3_DONE, TOPIC_L3_TASK, EventBus
from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, ready_gate_snapshot, set_boot_phase
from core.runtime.l3_scheduler import L3TaskKind


def _wait_cluster_idle(timeout_s: float = 3.0) -> None:
    cluster = get_cluster_runtime()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if cluster.cluster_healthy() and cluster.queue_length() == 0:
            return
        time.sleep(0.02)
    raise AssertionError(f"cluster not idle: {cluster.stats()}")


def _drain_bus_topics(*topics: str) -> None:
    from core.kernel.v3 import event_bus as bus_mod

    bus = bus_mod.get_event_bus()
    for topic in topics:
        while bus.try_get(topic) is not None:
            pass


class TestDeterministicLog(unittest.TestCase):
    def test_append_and_replay(self):
        log = DeterministicLog()
        log.append({"type": "l3.task", "id": "1", "handler": "cdg_init"})
        results = log.replay({"l3.task": lambda e: {"ok": e["id"]}})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ok"], "1")


class TestReplayEngine(unittest.TestCase):
    def test_verify_consistent(self):
        log = DeterministicLog()
        log.append({"type": "l3.task", "id": "a"})
        engine = ReplayEngine(log)
        ok = engine.verify_consistent({"l3.task": lambda e: {"status": "replay_ok"}})
        self.assertTrue(ok)


class TestL3SchedulerV4(unittest.TestCase):
    def test_signal_tick_with_done(self):
        bus = EventBus()
        from core.kernel.v3 import event_bus as bus_mod

        original = bus_mod.get_event_bus
        bus_mod.get_event_bus = lambda: bus
        runtime = MagicMock()
        runtime.base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory")
        try:
            with patch("api.deps.peek_runtime", return_value=runtime):
                sched = L3SchedulerV4()
                sched.enqueue_signal(label="x", handler="noop_ping", kind=L3TaskKind.WARMUP)
                _wait_cluster_idle()
                bus.publish(TOPIC_L3_DONE, {"label": "x", "status": "ok"})
                result = sched.run_tick()
                self.assertTrue(result.queue_empty)
        finally:
            bus_mod.get_event_bus = original
            _drain_bus_topics(TOPIC_L3_TASK, TOPIC_L3_DONE)
            _wait_cluster_idle()


class TestV4Guards(unittest.TestCase):
    def test_v4_enabled_default(self):
        self.assertTrue(non_hang_v4_enabled())

    def test_ready_gate_v4_layer(self):
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        with patch.dict(os.environ, {"CNEXUS_NON_HANG_V5": "0"}, clear=False):
            snap = ready_gate_snapshot()
        if non_hang_v4_enabled():
            self.assertEqual(snap.get("layer"), "v4")
            self.assertIn("cluster_ok", snap)
            self.assertIn("replay_ok", snap)

    def test_enforce_v4_shape(self):
        report = enforce_v4()
        self.assertEqual(report.get("isolation"), "deterministic_cluster_v4")


if __name__ == "__main__":
    unittest.main()

"""Non-Hang Kernel v5 tests."""



from __future__ import annotations



import os

import sys

import time

import unittest

from unittest.mock import MagicMock, patch



sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



from core.kernel.v4.cluster_runtime import get_cluster_runtime

from core.kernel.v5.boot_protocol_v5 import system_ready as v5_system_ready

from core.kernel.v5.cluster_consensus import ClusterConsensus

from core.kernel.v5.crdt_memory import CRDTMemory

from core.kernel.v5.global_cluster_runtime import get_global_cluster_runtime

from core.kernel.v5.l3_scheduler_v5 import L3SchedulerV5

from core.kernel.v5.system_guard_v5 import enforce_v5, non_hang_v5_enabled

from core.kernel.v3.event_bus import TOPIC_L3_DONE, TOPIC_L3_TASK, EventBus

from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, ready_gate_snapshot, set_boot_phase

from core.runtime.l3_scheduler import L3TaskKind





def _wait_global_cluster_idle(timeout_s: float = 3.0) -> None:

    cluster = get_global_cluster_runtime()

    backend = get_cluster_runtime()

    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:

        if cluster.cluster_health() and backend.queue_length() == 0:

            return

        time.sleep(0.02)

    raise AssertionError(f"global cluster not idle: {cluster.stats()}")





def _drain_bus_topics(*topics: str) -> None:

    from core.kernel.v3 import event_bus as bus_mod



    bus = bus_mod.get_event_bus()

    for topic in topics:

        while bus.try_get(topic) is not None:

            pass





class TestCRDTMemory(unittest.TestCase):

    def test_merge_and_read(self):

        crdt = CRDTMemory()

        crdt.merge("a", {"id": "a", "type": "l3.task"}, node_id=0)

        self.assertEqual(crdt.read("a")["id"], "a")

        self.assertTrue(crdt.is_consistent())





class TestClusterConsensus(unittest.TestCase):

    def test_elect_leader(self):

        nodes = [MagicMock(node_id=i) for i in range(3)]

        consensus = ClusterConsensus(nodes)

        leader = consensus.elect_leader()

        self.assertIsNotNone(leader)

        self.assertTrue(consensus.is_stable())





class TestL3SchedulerV5(unittest.TestCase):

    def test_signal_tick_with_done(self):

        bus = EventBus()

        from core.kernel.v3 import event_bus as bus_mod



        original = bus_mod.get_event_bus

        bus_mod.get_event_bus = lambda: bus

        runtime = MagicMock()

        runtime.base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory")

        try:

            with patch("api.deps.peek_runtime", return_value=runtime):

                sched = L3SchedulerV5()

                sched.enqueue_signal(label="x", handler="noop_ping", kind=L3TaskKind.WARMUP)

                _wait_global_cluster_idle()

                bus.publish(TOPIC_L3_DONE, {"label": "x", "status": "ok"})

                result = sched.run_tick()

                self.assertTrue(result.queue_empty)

                self.assertEqual(result.executed, ["signal_only_v5"])

        finally:

            bus_mod.get_event_bus = original

            _drain_bus_topics(TOPIC_L3_TASK, TOPIC_L3_DONE)

            _wait_global_cluster_idle()





class TestV5Guards(unittest.TestCase):

    def test_v5_enabled_default(self):

        self.assertTrue(non_hang_v5_enabled())



    def test_ready_gate_v5_layer(self):

        set_boot_phase(BootPhase.BOOT_4_READY)

        mark_cognitive_warmup_done()

        snap = ready_gate_snapshot()

        if non_hang_v5_enabled():

            self.assertEqual(snap.get("layer"), "v5")

            self.assertIn("cluster_ok", snap)

            self.assertIn("consensus_ok", snap)

            self.assertIn("crdt_ok", snap)



    def test_enforce_v5_shape(self):

        report = enforce_v5()

        self.assertEqual(report.get("isolation"), "cross_machine_cluster_v5")



    def test_boot_protocol_v5_ready_shape(self):

        snap = v5_system_ready(runtime=MagicMock())

        self.assertIn(snap.get("status"), ("ready", "warming"))

        self.assertEqual(snap.get("layer"), "v5")





if __name__ == "__main__":

    unittest.main()


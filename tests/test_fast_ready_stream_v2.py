"""Fast-Path v2 — streaming progressive ready tests."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.system_ready import mark_app_started, system_ready_payload
from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, set_boot_phase
from core.runtime.l3_scheduler import L3GovernanceScheduler
from core.runtime.streaming_ready import StreamingReady, fast_path_v2_enabled, should_use_stream_ready


class TestStreamingReady(unittest.TestCase):
    def test_fast_path_v2_default_on(self):
        with patch.dict(os.environ, {"CNEXUS_FAST_PATH_V2": "1"}, clear=False):
            self.assertTrue(fast_path_v2_enabled())

    def test_should_use_stream_modes(self):
        self.assertTrue(should_use_stream_ready(mode="stream", runtime=None))
        self.assertFalse(should_use_stream_ready(mode="fast", runtime=None))
        self.assertFalse(should_use_stream_ready(mode="full", runtime=None))

    def test_stream_phases_order(self):
        async def _run():
            streamer = StreamingReady(MagicMock())
            phases = []
            async for event in streamer.iter_events():
                phases.append(event["phase"])
            return phases

        phases = asyncio.run(_run())
        self.assertEqual(phases, ["shell", "local", "cluster", "final"])

    def test_system_ready_default_returns_streaming_ack(self):
        mark_app_started()
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        with patch.dict(
            os.environ,
            {"CNEXUS_FAST_PATH_V2": "1", "CNEXUS_FAST_PATH_V1": "1", "CNEXUS_FAST_PATH_V3": "0"},
            clear=False,
        ):
            payload = system_ready_payload(MagicMock(), mode="default")
        self.assertEqual(payload["status"], "streaming")
        self.assertEqual(payload["mode"], "fast-path-v2")

    def test_l3_ready_affecting_ops_isolated(self):
        sched = L3GovernanceScheduler()
        self.assertFalse(sched.ready_affecting_ops())


if __name__ == "__main__":
    unittest.main()

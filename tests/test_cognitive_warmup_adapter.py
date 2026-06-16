"""Cognitive warmup L3 adapter tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from core.runtime.boot_protocol import BootPhase, get_boot_phase, set_boot_phase
from core.runtime.cognitive_warmup_adapter import CognitiveWarmupAdapter, run_cognitive_warmup_ticks
from core.runtime.l3_scheduler import L3GovernanceScheduler


class TestCognitiveWarmupAdapter(unittest.TestCase):
    def setUp(self):
        set_boot_phase(BootPhase.BOOT_2_HYDRATING)

    def test_tick_advances_to_boot_4_when_queue_drains(self):
        runtime = MagicMock()
        runtime.base_dir = "/tmp/cnexus-test"
        runtime.config = {"governance_background_enabled": False}
        runtime.cdg.trajectory_report.return_value = {}
        runtime.memory_manager.block_stats.return_value = {}
        runtime.reflection_pipeline.count_due_reviews.return_value = 0

        adapter = CognitiveWarmupAdapter(runtime, L3GovernanceScheduler(time_slice_ms=50))
        phase = BootPhase.BOOT_3_COGNITIVE_WARMING
        for _ in range(20):
            phase = adapter.tick()
            if phase == BootPhase.BOOT_4_READY:
                break

        self.assertEqual(phase, BootPhase.BOOT_4_READY)
        self.assertEqual(get_boot_phase(), BootPhase.BOOT_4_READY)

    def test_run_ticks_yields_between_iterations(self):
        runtime = MagicMock()
        runtime.base_dir = "/tmp/cnexus-test"
        runtime.config = {"governance_background_enabled": False}
        runtime.cdg.trajectory_report.return_value = {}
        runtime.memory_manager.block_stats.return_value = {}
        runtime.reflection_pipeline.count_due_reviews.return_value = 0

        with patch("core.runtime.cognitive_warmup_adapter.time.sleep") as mock_sleep:
            final = run_cognitive_warmup_ticks(runtime, max_ticks=5, yield_sec=0.01)
        self.assertEqual(final, BootPhase.BOOT_4_READY)
        self.assertGreater(mock_sleep.call_count, 0)


if __name__ == "__main__":
    unittest.main()

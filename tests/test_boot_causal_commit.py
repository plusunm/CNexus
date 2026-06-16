"""BOOT_4 causal commit — no optimistic state advance."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.boot_protocol import (
    BootPhase,
    evaluate_system_ready,
    get_boot_phase,
    mark_cognitive_warmup_done,
    set_boot_phase,
    set_l3_scheduler_status,
)
from core.runtime.cognitive_warmup_adapter import CognitiveWarmupAdapter, reset_warmup_adapter


class _StubScheduler:
    def __init__(self) -> None:
        self._queue_len = 2

    def run_tick(self):
        from types import SimpleNamespace

        return SimpleNamespace(queue_empty=False)

    def status_payload(self) -> dict:
        return {"queue_length": self._queue_len, "ticks": 1}


class _StubRuntime:
    base_dir = "/tmp/test"


class TestBootCausalCommit(unittest.TestCase):
    def tearDown(self) -> None:
        reset_warmup_adapter()
        set_boot_phase(BootPhase.BOOT_0_API)
        set_l3_scheduler_status({})

    def test_rejects_optimistic_boot_4_when_l3_queue_nonempty(self) -> None:
        set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)
        set_l3_scheduler_status({"queue_length": 3, "ticks": 10})
        adapter = CognitiveWarmupAdapter(_StubRuntime(), scheduler=_StubScheduler())
        import core.runtime.cognitive_warmup_adapter as mod

        mod._active_adapter = adapter

        self.assertFalse(mark_cognitive_warmup_done())
        self.assertEqual(get_boot_phase(), BootPhase.BOOT_3_COGNITIVE_WARMING)
        self.assertEqual(
            evaluate_system_ready(
                app_started=True,
                runtime_present=True,
                runtime_warming=False,
                memory_ok=True,
            ),
            "warming",
        )

    def test_allows_boot_4_when_adapter_drained(self) -> None:
        set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)
        set_l3_scheduler_status({"queue_length": 0, "ticks": 10})
        adapter = CognitiveWarmupAdapter(_StubRuntime(), scheduler=_StubScheduler())
        adapter.done = True
        import core.runtime.cognitive_warmup_adapter as mod

        mod._active_adapter = adapter

        self.assertTrue(mark_cognitive_warmup_done())
        self.assertEqual(get_boot_phase(), BootPhase.BOOT_4_READY)


if __name__ == "__main__":
    unittest.main()

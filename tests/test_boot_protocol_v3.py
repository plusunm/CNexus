"""Boot Protocol v3 — scheduler semantics and ready gate tests."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.boot_protocol import (
    BootPhase,
    evaluate_system_ready,
    mark_cognitive_warmup_done,
    mark_hydrate_complete,
    mark_runtime_spawned,
    normalize_boot_phase,
    set_boot_phase,
)


class TestBootProtocolV3(unittest.TestCase):
    def setUp(self):
        set_boot_phase(BootPhase.BOOT_0_API)

    def test_legacy_phase_normalization(self):
        self.assertEqual(
            normalize_boot_phase("boot_1_state"),
            BootPhase.BOOT_1_RUNTIME_SPAWNED,
        )
        self.assertEqual(
            normalize_boot_phase("boot_3_optimized"),
            BootPhase.BOOT_4_READY,
        )

    def test_ready_only_at_boot_4(self):
        mark_runtime_spawned()
        self.assertEqual(
            evaluate_system_ready(
                app_started=True,
                runtime_present=True,
                runtime_warming=False,
                memory_ok=True,
            ),
            "warming",
        )

        mark_hydrate_complete()
        self.assertEqual(
            evaluate_system_ready(
                app_started=True,
                runtime_present=True,
                runtime_warming=False,
                memory_ok=True,
            ),
            "warming",
        )

        mark_cognitive_warmup_done(bypass_causal=True)
        with patch.dict(os.environ, {"CNEXUS_NON_HANG_V4": "0", "CNEXUS_NON_HANG_V5": "0"}, clear=False):
            self.assertEqual(
                evaluate_system_ready(
                    app_started=True,
                    runtime_present=True,
                    runtime_warming=False,
                    memory_ok=True,
                ),
                "ready",
            )

    def test_warming_while_runtime_warming(self):
        set_boot_phase(BootPhase.BOOT_4_READY)
        self.assertEqual(
            evaluate_system_ready(
                app_started=True,
                runtime_present=True,
                runtime_warming=True,
                memory_ok=True,
            ),
            "warming",
        )


if __name__ == "__main__":
    unittest.main()

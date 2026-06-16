"""Operational vs full readiness — BDE-1 capability model tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from core.runtime.boot_protocol import (
    BootPhase,
    evaluate_operational_ready,
    evaluate_system_ready,
    mark_cognitive_warmup_done,
    set_boot_phase,
)
from core.runtime.system_capability import build_system_capabilities


class OperationalReadyTests(unittest.TestCase):
    def test_operational_without_boot_4(self):
        set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)
        op = evaluate_operational_ready(
            app_started=True,
            runtime_present=True,
            runtime_warming=False,
            memory_ok=True,
        )
        full = evaluate_system_ready(
            app_started=True,
            runtime_present=True,
            runtime_warming=False,
            memory_ok=True,
        )
        self.assertEqual(op, "operational")
        self.assertEqual(full, "warming")

    def test_capability_vector_chat_before_full(self):
        set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)
        cap = build_system_capabilities(
            app_started=True,
            runtime_present=True,
            runtime_warming=False,
            memory_ok=True,
        )
        self.assertTrue(cap["operational_ready"])
        self.assertFalse(cap["full_ready"])
        self.assertTrue(cap["capabilities"]["chat"])
        self.assertFalse(cap["capabilities"]["upload"])
        self.assertEqual(cap["cognitive_status"], "warming")

    def test_cognitive_status_ready_only_when_full(self):
        set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)
        mark_cognitive_warmup_done(bypass_causal=True)
        cap = build_system_capabilities(
            app_started=True,
            runtime_present=True,
            runtime_warming=False,
            memory_ok=True,
        )
        if cap["full_ready"]:
            self.assertEqual(cap["cognitive_status"], "ready")
        else:
            self.assertNotEqual(cap["cognitive_status"], "ready")

    def test_skip_cognitive_full_ready(self):
        with patch.dict(os.environ, {"CNEXUS_BOOT_SKIP_COGNITIVE": "1"}, clear=False):
            set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)
            mark_cognitive_warmup_done(bypass_causal=True)
            cap = build_system_capabilities(
                app_started=True,
                runtime_present=True,
                runtime_warming=False,
                memory_ok=True,
            )
            self.assertTrue(cap["full_ready"])
            self.assertTrue(cap["capabilities"]["upload"])


if __name__ == "__main__":
    unittest.main()

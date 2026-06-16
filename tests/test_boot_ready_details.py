"""Boot ready details + skip-cognitive isolation flag."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from core.runtime.boot_protocol import (
    BootPhase,
    boot_ready_details,
    cognitive_disabled,
    mark_cognitive_warmup_done,
    set_boot_phase,
)
from storage.graph import _resolve_kuzu_db_path


class BootReadyDetailsTests(unittest.TestCase):
    def test_skip_cognitive_env(self):
        with patch.dict(os.environ, {"CNEXUS_BOOT_SKIP_COGNITIVE": "1"}, clear=False):
            self.assertTrue(cognitive_disabled())

    def test_ready_details_when_boot_4(self):
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done(bypass_causal=True)
        details = boot_ready_details(
            status="ready",
            app_started=True,
            runtime_present=True,
            runtime_warming=False,
            memory_ok=True,
        )
        self.assertTrue(details["ready"])
        self.assertEqual(details["progress"], 100)
        self.assertIsNone(details["reason"])

    def test_ready_details_cognitive_warming(self):
        set_boot_phase(BootPhase.BOOT_3_COGNITIVE_WARMING)
        details = boot_ready_details(
            status="warming",
            app_started=True,
            runtime_present=True,
            runtime_warming=False,
            memory_ok=True,
        )
        self.assertFalse(details["ready"])
        self.assertEqual(details["reason"], "COGNITIVE_WARMUP")
        self.assertGreaterEqual(details["progress"], 40)


class KuzuPathTests(unittest.TestCase):
    def test_empty_kuzu_dir_removed_before_init(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            kuzu = Path(tmp) / "kuzu_db"
            kuzu.mkdir()
            resolved = _resolve_kuzu_db_path(str(kuzu))
            self.assertFalse(resolved.is_dir())


if __name__ == "__main__":
    unittest.main()

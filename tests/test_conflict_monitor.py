"""Runtime conflict monitor log file tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.runtime.conflict_monitor import (
    conflict_log_path,
    log_capability_transition,
    log_conflict_event,
    tail_conflict_log,
)


class ConflictMonitorTests(unittest.TestCase):
    def test_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime-conflict-monitor.log"
            with patch("core.runtime.conflict_monitor.conflict_log_path", return_value=path):
                log_conflict_event("TEST_EVENT", force=True, foo="bar")
                self.assertTrue(path.is_file())
                line = json.loads(path.read_text(encoding="utf-8").strip())
                self.assertEqual(line["event"], "TEST_EVENT")
                self.assertEqual(line["foo"], "bar")

    def test_capability_dual_reality_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime-conflict-monitor.log"
            with patch("core.runtime.conflict_monitor.conflict_log_path", return_value=path):
                log_capability_transition(
                    operational_ready=False,
                    full_ready=False,
                    cognitive_status="warming",
                    boot_phase="boot_3_cognitive_warming",
                    reason="COGNITIVE_WARMUP",
                    progress=55,
                    status="warming",
                    legacy_status="ready_fast",
                )
                entries = tail_conflict_log(10)
                self.assertTrue(entries)
                self.assertIn("DUAL_REALITY_FAST_NOT_OPERATIONAL", entries[-1].get("conflicts", []))


if __name__ == "__main__":
    unittest.main()

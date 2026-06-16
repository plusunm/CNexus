"""Runtime state track (P1) tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.gtbs.state_snapshot import TierASnapshot, snapshot_tier_a
from core.runtime.trace_context import trace_scope
from core.spine.integration import register_spine_writer
from core.spine.state.track import commit_runtime_state_diff, snapshot_runtime_tier_a
from core.spine.storage import SpineEventLog
from core.spine.writer import SpineWriter


class TestStateTrack(unittest.TestCase):
    def test_commit_runtime_state_diff_writes_spine(self):
        tmp = tempfile.TemporaryDirectory()
        writer = SpineWriter(SpineEventLog(tmp.name))
        register_spine_writer(writer)

        runtime = MagicMock()
        runtime.working_self = MagicMock()
        runtime.state = MagicMock()
        runtime.dna_engine = MagicMock()

        before = TierASnapshot(working_self={"goal": "a"}, legacy_state={"cognitive_load": 0.1})
        after = TierASnapshot(working_self={"goal": "b"}, legacy_state={"cognitive_load": 0.2})

        def _snap(_rt):
            return after

        with unittest.mock.patch("core.spine.state.track.snapshot_tier_a", side_effect=_snap):
            with trace_scope("trace-p1"):
                event = commit_runtime_state_diff(runtime, before, label="test_mutation")

        self.assertIsNotNone(event)
        rows = writer._log.read_all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "state")
        self.assertEqual(rows[0]["state_delta"]["mutation_label"], "test_mutation")

        register_spine_writer(None)
        tmp.cleanup()

    def test_no_trace_skips_commit(self):
        runtime = MagicMock()
        before = TierASnapshot(working_self={"a": 1}, legacy_state={})
        result = commit_runtime_state_diff(runtime, before, label="x")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

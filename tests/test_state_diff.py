"""Tier-A state diff + spine state event tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.gtbs.state_snapshot import TierASnapshot
from core.runtime.trace_context import trace_scope
from core.spine.integration import register_spine_writer
from core.spine.state.diff import diff_tier_a
from core.spine.state.emit import maybe_record_tier_a_diff
from core.spine.storage import SpineEventLog
from core.spine.writer import SpineWriter


class TestStateDiff(unittest.TestCase):
    def test_diff_tier_a_fields(self):
        before = TierASnapshot(
            working_self={"goal": "a", "focus": 1},
            legacy_state={"cognitive_load": 0.2},
        )
        after = TierASnapshot(
            working_self={"goal": "b", "focus": 1},
            legacy_state={"cognitive_load": 0.5},
        )
        patch = diff_tier_a(before, after)
        self.assertEqual(patch["change_count"], 2)
        fields = {c["field"] for c in patch["changes"]}
        self.assertIn("working_self.goal", fields)
        self.assertIn("legacy_state.cognitive_load", fields)

    def test_emit_state_spine_event(self):
        tmp = tempfile.TemporaryDirectory()
        base = tmp.name
        writer = SpineWriter(SpineEventLog(base))
        register_spine_writer(writer)

        before = TierASnapshot(working_self={"x": 1}, legacy_state={})
        after = TierASnapshot(working_self={"x": 2}, legacy_state={})

        with trace_scope("trace-state-1"):
            event = maybe_record_tier_a_diff(before, after, intent_id="intent-1")

        self.assertIsNotNone(event)
        rows = writer._log.read_all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "state")
        self.assertEqual(rows[0]["state_delta"]["change_count"], 1)

        register_spine_writer(None)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

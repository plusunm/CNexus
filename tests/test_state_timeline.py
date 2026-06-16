"""State timeline engine tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.state.timeline import StateTimelineEngine


class TestStateTimeline(unittest.TestCase):
    def test_builds_projection_chain(self):
        events = [
            {
                "event_id": "s1",
                "timestamp": "2026-01-01T00:00:00Z",
                "event_type": "state",
                "state_delta": {
                    "change_count": 1,
                    "changes": [{"field": "working_self.goal", "before": "a", "after": "b"}],
                },
            },
            {
                "event_id": "s2",
                "timestamp": "2026-01-01T00:00:01Z",
                "event_type": "state",
                "state_delta": {
                    "change_count": 1,
                    "changes": [{"field": "working_self.goal", "before": "b", "after": "c"}],
                },
            },
        ]
        engine = StateTimelineEngine()
        timeline = engine.build(events)
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]["after"]["working_self.goal"], "b")
        self.assertEqual(timeline[1]["after"]["working_self.goal"], "c")
        self.assertEqual(engine.to_dict()["latest_projection"]["working_self.goal"], "c")


if __name__ == "__main__":
    unittest.main()

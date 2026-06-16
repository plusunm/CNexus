"""Explanation Engine v2 fusion tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.explain_v2 import build_fusion_explanation
from core.spine.query import run_query
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEvent


class TestExplainV2(unittest.TestCase):
    def test_fusion_from_mixed_trace(self):
        events = [
            {
                "event_id": "e1",
                "trace_id": "t1",
                "event_type": "recall",
                "summary": "recall",
                "parent_event_id": None,
            },
            {
                "event_id": "e2",
                "trace_id": "t1",
                "event_type": "state",
                "summary": "state patch",
                "parent_event_id": "e1",
                "state_delta": {
                    "source": "tier_a",
                    "change_count": 1,
                    "changes": [
                        {
                            "field": "working_self.focus",
                            "before": 0.4,
                            "after": 0.7,
                        }
                    ],
                },
            },
            {
                "event_id": "e3",
                "trace_id": "t1",
                "event_type": "control",
                "summary": "control warn",
                "parent_event_id": "e2",
                "decision": "WARN",
                "entry": "legacy_api",
                "caller": "http",
            },
        ]
        fusion = build_fusion_explanation("t1", events)
        self.assertEqual(fusion["version"], "explain-v2")
        self.assertEqual(len(fusion["causal_chain"]), 3)
        self.assertEqual(fusion["causal_chain"][0]["caused"], ["e2"])
        self.assertEqual(len(fusion["state_transitions"]), 1)
        self.assertAlmostEqual(fusion["state_transitions"][0]["delta"]["working_self.focus"], 0.3)
        self.assertEqual(fusion["control_flow"][0]["decision"], "WARN")
        self.assertIn("summary", fusion["explanation"])
        self.assertTrue(fusion["explanation"]["state_story"])

    def test_query_includes_fusion_v2(self):
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        base = tmp.name
        log = SpineEventLog(base)
        log.append(
            SpineEvent.from_dict(
                {
                    "event_id": "e1",
                    "trace_id": "t-fusion",
                    "timestamp": "2026-06-14T00:00:00+00:00",
                    "event_type": "recall",
                    "subsystem": "gtbs",
                    "action": "propose",
                    "summary": "recall",
                }
            )
        )
        result = run_query(base, trace_id="t-fusion").to_dict()
        self.assertIn("fusion_v2", result)
        self.assertEqual(result["fusion_v2"]["version"], "explain-v2")
        self.assertIn("v2_summary", result["explanation"])
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

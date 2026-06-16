"""Feedback loop observation-only tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.feedback.loop import SpineFeedbackLoopEngine


class TestFeedbackLoop(unittest.TestCase):
    def test_high_quality_frame(self):
        engine = SpineFeedbackLoopEngine()
        frame = {
            "causal_delta": {"added_edges": [["a", "b"]]},
            "state_delta": {"delta": {"x": 1}},
            "control_delta": {"decision": "allow"},
        }
        fb = engine.process({"event_type": "control"}, frame)
        self.assertGreaterEqual(fb["evaluation"]["score"], 0.7)
        self.assertEqual(fb["evaluation"]["quality"], "HIGH")
        self.assertFalse(fb["applied_to_runtime"])

    def test_drift_triggers_control_state(self):
        engine = SpineFeedbackLoopEngine()
        frame = {"causal_delta": {}, "state_delta": {}, "control_delta": None}
        fb = engine.process({"event_type": "recall"}, frame)
        self.assertTrue(fb["drift"].get("missing_causal"))
        self.assertTrue(engine.control_state.get("trace_enforcement"))


if __name__ == "__main__":
    unittest.main()

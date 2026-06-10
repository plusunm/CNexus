"""GTBS v1.1 Shadow Mode — divergence sensor invariants."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.gtbs.gatekeeper import (
    GTBS_SHADOW_MODE,
    GTBS_SHADOW_VERSION,
    RuntimeGatekeeper,
)


class TestGTBSShadowMode(unittest.TestCase):
    def test_shadow_constants(self):
        gk = RuntimeGatekeeper()
        self.assertTrue(gk.is_shadow_mode)
        self.assertEqual(gk.GTBS_VERSION, GTBS_SHADOW_VERSION)
        self.assertEqual(gk.GTBS_MODE, GTBS_SHADOW_MODE)

    def test_observe_no_side_effects(self):
        gk = RuntimeGatekeeper()
        pre = {"a": 1, "b": 2}
        post = {"b": 2, "c": 3}
        out = gk.observe_runtime_event(
            pre,
            post,
            context={"phase": "test"},
            proposal={"target_stores": ["storage"], "operation_type": "INGEST"},
        )
        self.assertEqual(pre, {"a": 1, "b": 2})
        self.assertEqual(post, {"b": 2, "c": 3})
        self.assertEqual(out["type"], "gtbs_shadow_observation")
        self.assertTrue(out["non_actionable"])
        self.assertEqual(out["state_diff"]["added_keys"], ["c"])
        self.assertEqual(out["state_diff"]["removed_keys"], ["a"])
        self.assertEqual(out["state_diff"]["divergence_score"], 2)

    def test_observe_empty_states(self):
        gk = RuntimeGatekeeper()
        out = gk.observe_runtime_event(None, None)
        self.assertFalse(out["has_proposal"])
        self.assertEqual(out["state_diff"]["divergence_score"], 0)

    def test_no_control_surface(self):
        """P1 invariant: gatekeeper must not expose commit/approve/block."""
        gk = RuntimeGatekeeper()
        forbidden = ("commit", "approve", "block", "reject", "adjust_params", "record")
        for name in forbidden:
            self.assertFalse(hasattr(gk, name), f"forbidden surface: {name}")


if __name__ == "__main__":
    unittest.main()

"""CP-2 write funnel — Tier-A rollback tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.gtbs.adapters.capture_adapter import build_capture_write_intent
from core.governance.gtbs.state_snapshot import restore_tier_a, snapshot_tier_a
from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.write_funnel import execute_write_intent, tx_rollback_enabled
from core.governance.gtbs.write_intent_bus import WriteIntentBus
from memory.runtime_guard import runtime_write_context
from runtime.cognitive_state import PersistentCognitiveState


class TestStateSnapshot(unittest.TestCase):
    def test_tier_a_roundtrip(self):
        rt = MagicMock()
        rt.working_self = PersistentCognitiveState(goal_focus="identity", turn_count=3)
        rt.state.cognitive_load = 0.42
        rt.state.current_goal_focus = "identity"
        rt.state.current_identity_mode = "reflective"
        rt.state.current_relationship_focus = None
        snap = snapshot_tier_a(rt)
        rt.working_self.goal_focus = "general"
        rt.working_self.turn_count = 99
        rt.state.cognitive_load = 0.1
        restore_tier_a(rt, snap)
        self.assertEqual(rt.working_self.goal_focus, "identity")
        self.assertEqual(rt.working_self.turn_count, 3)
        self.assertEqual(rt.state.cognitive_load, 0.42)


class TestWriteFunnel(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base_dir = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    def _runtime(self):
        rt = MagicMock()
        rt.base_dir = self.base_dir
        rt.config = {
            "gtbs": {
                "enable_write_intent_shadow": True,
                "enable_write_intent_soft_gate": True,
                "enable_write_intent_tx_rollback": True,
            }
        }
        rt.working_self = PersistentCognitiveState(turn_count=1)
        rt.state.cognitive_load = 0.5
        rt.state.current_goal_focus = None
        rt.state.current_identity_mode = "stable"
        rt.state.current_relationship_focus = None
        bus = WriteIntentBus(GTBSTransactionLog(self.base_dir))
        rt._get_write_intent_bus = MagicMock(return_value=bus)
        return rt, bus

    def test_tx_rollback_enabled_flag(self):
        self.assertFalse(tx_rollback_enabled(config={"gtbs": {}}))
        self.assertTrue(
            tx_rollback_enabled(config={"gtbs": {"enable_write_intent_tx_rollback": True}})
        )

    def test_execute_rollback_on_failure(self):
        rt, bus = self._runtime()
        log = GTBSTransactionLog(self.base_dir)
        intent = build_capture_write_intent(
            role="user",
            content="x",
            layer="episodic",
            importance=0.5,
        )
        rt.working_self.turn_count = 5

        def fail():
            rt.working_self.turn_count = 99
            raise RuntimeError("commit failed")

        with runtime_write_context(token="tok-1"):
            with self.assertRaises(RuntimeError):
                execute_write_intent(rt, intent, fail)

        self.assertEqual(rt.working_self.turn_count, 5)
        rows = log.read_all()
        self.assertEqual(rows[-1]["payload"].get("rollback"), True)

    def test_execute_commit_on_success(self):
        rt, bus = self._runtime()
        log = GTBSTransactionLog(self.base_dir)
        intent = build_capture_write_intent(
            role="user",
            content="x",
            layer="episodic",
            importance=0.5,
        )

        with runtime_write_context(token="tok-1"):
            out = execute_write_intent(rt, intent, lambda: "mem-ok")

        self.assertEqual(out, "mem-ok")
        types = [r["event_type"] for r in log.read_all()]
        self.assertEqual(types, ["proposal", "commit"])


if __name__ == "__main__":
    unittest.main()

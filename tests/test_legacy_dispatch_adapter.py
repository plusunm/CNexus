"""Legacy api/server.py → AuthorityDispatcher adapter tests."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.legacy_adapter import LEGACY_CALLER, LEGACY_CHANNEL, LegacyDispatchAdapter


class TestLegacyDispatchAdapter(unittest.TestCase):
    def setUp(self):
        self._env = patch.dict(
            os.environ,
            {
                "USE_EXECUTION_GRAPH": "0",
                "USE_EXECUTION_KERNEL": "1",
                "KERNEL_ENFORCE_MODE": "1",
                "KERNEL_HARD_LOCK_MODE": "1",
            },
        )
        self._env.start()
        self.runtime = MagicMock()
        self.runtime.process_interaction.return_value = {
            "ok": True,
            "reply": "hello",
            "response": "hello",
        }
        self.runtime.run_governance_cycle.return_value = {"status": "ok"}
        self.runtime.recall.return_value = "recalled ctx"
        self.dispatcher = AuthorityDispatcher(self.runtime)
        self.adapter = LegacyDispatchAdapter(self.dispatcher)

    def tearDown(self):
        self._env.stop()

    def test_chat_routes_through_dispatcher(self):
        llm = MagicMock()
        profile = MagicMock()
        result = self.adapter.chat(
            message="hi",
            use_memory=True,
            temperature=0.5,
            llm_client=llm,
            llm_profile=profile,
        )
        self.assertEqual(result["reply"], "hello")
        self.runtime.process_interaction.assert_called_once()
        args, kwargs = self.runtime.process_interaction.call_args
        self.assertEqual(args[0], "hi")
        self.assertEqual(kwargs.get("temperature"), 0.5)

    @patch("core.control_plane.dispatch.audit_decision")
    def test_chat_marks_legacy_caller_in_audit(self, mock_audit):
        self.adapter.chat(
            message="hi",
            llm_client=MagicMock(),
            llm_profile=MagicMock(),
            trace_id="legacy-trace-1",
        )
        decision = mock_audit.call_args[0][0]
        self.assertEqual(decision.caller, LEGACY_CALLER)
        self.assertEqual(decision.channel, LEGACY_CHANNEL)

    def test_governance_cycle_routes_through_dispatcher(self):
        out = self.adapter.governance_cycle()
        self.assertEqual(out["status"], "ok")
        self.runtime.run_governance_cycle.assert_called_once()

    def test_recall_preview_uses_projection_mode(self):
        ctx = self.adapter.recall_preview("query text")
        self.assertEqual(ctx, "recalled ctx")
        self.runtime.recall.assert_called_once()
        kwargs = self.runtime.recall.call_args.kwargs
        self.assertFalse(kwargs.get("mutate_state", True))

    def test_from_runtime_factory(self):
        adapter = LegacyDispatchAdapter.from_runtime(self.runtime)
        self.assertIsInstance(adapter, LegacyDispatchAdapter)
        self.assertIs(adapter.runtime, self.runtime)

    def test_capture_routes_through_dispatcher(self):
        self.runtime.capture.return_value = "mem-1"
        result = self.adapter.capture(
            role="user",
            content="note",
            return_detail=True,
        )
        self.assertEqual(result, "mem-1")
        self.runtime.capture.assert_called_once()

    def test_interact_routes_with_user_id(self):
        self.adapter.interact(
            message="hello",
            user_id="u1",
            metadata={"session_id": "s1"},
            llm_client=MagicMock(),
            llm_profile=MagicMock(),
        )
        kwargs = self.runtime.process_interaction.call_args.kwargs
        self.assertEqual(kwargs["user_id"], "u1")
        self.assertEqual(kwargs["metadata"]["session_id"], "s1")


if __name__ == "__main__":
    unittest.main()

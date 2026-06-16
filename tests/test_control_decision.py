"""Phase 1 — DecisionEngine overlay and dispatch integration."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.decision_engine import DecisionEngine, DecisionType
from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.exceptions import ControlDecisionRejected
from core.control_plane.registry import EntryNotRegisteredError
from core.control_plane.types import RouteKind, build_dispatch_context


class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()

    def test_allow_primary_http_path(self):
        ctx = build_dispatch_context(RouteKind.MEMORY_READ, {"query": "q"})
        decision = self.engine.decide(
            ctx,
            registry_entry="memory_recall",
            spec={"mutate_state": False},
        )
        self.assertEqual(decision.type, DecisionType.ALLOW)
        self.assertEqual(decision.reason, "OK")

    def test_warn_legacy_caller(self):
        ctx = build_dispatch_context(
            RouteKind.CHAT_SEND,
            {"message": "hi"},
            caller="legacy_api",
            channel="api/server.py",
        )
        decision = self.engine.decide(
            ctx,
            registry_entry="process_interaction",
            spec={},
        )
        self.assertEqual(decision.type, DecisionType.WARN)
        self.assertEqual(decision.reason, "LEGACY_CALLER")

    def test_warn_deprecated_entry(self):
        ctx = build_dispatch_context(RouteKind.MEMORY_WRITE, {"role": "user", "content": "x"})
        decision = self.engine.decide(
            ctx,
            registry_entry="memory_capture",
            spec={"deprecated_for_external": True},
        )
        self.assertEqual(decision.type, DecisionType.WARN)
        self.assertEqual(decision.reason, "DEPRECATED_ENTRY")

    def test_normal_capture_not_warn_spam(self):
        ctx = build_dispatch_context(RouteKind.MEMORY_WRITE, {"role": "user", "content": "x"})
        decision = self.engine.decide(
            ctx,
            registry_entry="memory_capture",
            spec={"deprecated_for_external": True},
        )
        self.assertEqual(decision.type, DecisionType.WARN)
        self.assertNotEqual(decision.reason, "EXTERNAL_MEMORY_WRITE")

    def test_unknown_entry_signal(self):
        ctx = build_dispatch_context(RouteKind.MEMORY_READ, {"query": "q"})
        decision = DecisionEngine.unknown_entry(ctx)
        self.assertEqual(decision.type, DecisionType.SIGNAL_REJECT)
        self.assertTrue(decision.blocks_when_hard_gate())


class TestDispatchDecisionOverlay(unittest.TestCase):
    def test_dispatch_still_executes_on_warn(self):
        runtime = MagicMock()
        runtime.recall.return_value = "ctx"
        disp = AuthorityDispatcher(runtime)

        ctx = build_dispatch_context(
            RouteKind.MEMORY_WRITE,
            {"role": "user", "content": "hello", "layer": "episodic", "importance": 0.5, "meta": {}},
        )
        out = disp.dispatch(ctx)

        runtime.capture.assert_called_once()
        self.assertIsNotNone(out)

    def test_legacy_caller_warns_but_executes(self):
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"reply": "ok"}
        disp = AuthorityDispatcher(runtime)

        ctx = build_dispatch_context(
            RouteKind.CHAT_SEND,
            {"message": "hello"},
            caller="legacy_api",
        )
        out = disp.dispatch(ctx)

        self.assertEqual(out["reply"], "ok")
        runtime.process_interaction.assert_called_once()

    def test_unknown_entry_raises_without_hard_gate(self):
        runtime = MagicMock()
        disp = AuthorityDispatcher(runtime)
        ctx = build_dispatch_context(RouteKind.MEMORY_READ, {"query": "q"})

        with patch.dict(os.environ, {"CONTROL_PLANE_HARD_GATE": ""}, clear=False):
            with patch(
                "core.control_plane.dispatch.resolve_registry_entry",
                side_effect=EntryNotRegisteredError("unmapped"),
            ):
                with self.assertRaises(EntryNotRegisteredError):
                    disp.dispatch(ctx)

        runtime.recall.assert_not_called()

    def test_unknown_entry_hard_gate_raises_control_rejected(self):
        runtime = MagicMock()
        disp = AuthorityDispatcher(runtime)
        ctx = build_dispatch_context(RouteKind.MEMORY_READ, {"query": "q"})

        with patch.dict(os.environ, {"CONTROL_PLANE_HARD_GATE": "1"}, clear=False):
            with patch(
                "core.control_plane.dispatch.resolve_registry_entry",
                side_effect=EntryNotRegisteredError("unmapped"),
            ):
                with self.assertRaises(ControlDecisionRejected) as cm:
                    disp.dispatch(ctx)
                self.assertEqual(cm.exception.decision.reason, "UNKNOWN_ENTRY")

    def test_ws_chat_sets_websocket_caller(self):
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"reply": "ok"}
        disp = AuthorityDispatcher(runtime)

        with patch.object(disp, "dispatch", wraps=disp.dispatch) as mock_dispatch:
            disp.ws_chat(message="hello")
            ctx = mock_dispatch.call_args[0][0]
            self.assertEqual(ctx.caller, "websocket")

    @patch("core.control_plane.dispatch.audit_decision")
    def test_memory_read_audit_includes_mutate_state_false(self, mock_audit):
        runtime = MagicMock()
        runtime.recall.return_value = "ctx"
        disp = AuthorityDispatcher(runtime)
        disp.memory_recall("hello")

        _, kwargs = mock_audit.call_args
        self.assertFalse(kwargs["extra"]["mutate_state"])


if __name__ == "__main__":
    unittest.main()

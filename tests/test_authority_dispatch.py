"""Phase 0 — AuthorityDispatcher and recall projection mode."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.guards import dispatch_context, is_dispatch_active
from core.control_plane.registry import ROUTE_ENTRY_MAP, enforce_route_entry, resolve_registry_entry
from core.control_plane.types import DispatchContext, RouteKind


class TestAuthorityRegistry(unittest.TestCase):
    def test_route_map_covers_write_paths(self):
        for kind in (
            "chat_send",
            "memory_read",
            "memory_write",
            "ir_execute",
            "governance_cycle",
            "ws_chat",
        ):
            self.assertIn(kind, ROUTE_ENTRY_MAP)

    def test_enforce_memory_recall(self):
        spec = enforce_route_entry("memory_read")
        self.assertFalse(spec.get("mutate_state", True))

    def test_unmapped_route_raises(self):
        with self.assertRaises(KeyError):
            resolve_registry_entry("not_a_route")


class TestDispatchContext(unittest.TestCase):
    def test_dispatch_context_flag(self):
        self.assertFalse(is_dispatch_active())
        with dispatch_context():
            self.assertTrue(is_dispatch_active())
        self.assertFalse(is_dispatch_active())


class TestRecallProjectionMode(unittest.TestCase):
    def test_recall_default_does_not_sync_state(self):
        from runtime.recall_pipeline import RecallPipeline

        rt = MagicMock()
        rt.recall_top_k = 3
        rt.runtime_mode = "legacy"
        rt.router.hybrid_recall.return_value = [{"_label": "a", "_final_score": 1.0}]
        rt.goal_manager.motivation_boost.return_value = 0
        rt.goal_manager.active_goals.return_value = []
        rt.context_engine.assemble.return_value = "ctx"
        rt.emotion_engine.format_context_block.return_value = ""
        rt.intent_engine.format_context_block.return_value = ""
        rt.reflective_engine.format_context_block.return_value = ""
        rt.values_governance.format_context_block.return_value = ""
        rt.narrative.generate_identity_anchor.return_value = ""
        rt.narrative.get_current_narrative_summary.return_value = ""
        rt.self_model.to_prompt_block.return_value = ""
        rt.working_self.goal_focus = "x"
        rt.working_self.cumulative_coherence = 0.5
        rt.working_self.prediction_error = 0.1

        pipe = RecallPipeline(rt)
        pipe.recall("hello", mutate_state=False)

        rt.state.sync_from_attention.assert_not_called()
        rt.working_self.sync_to_legacy.assert_not_called()

    def test_recall_stateful_syncs(self):
        from runtime.recall_pipeline import RecallPipeline

        rt = MagicMock()
        rt.recall_top_k = 3
        rt.runtime_mode = "legacy"
        rt.router.hybrid_recall.return_value = [{"_label": "a", "_final_score": 1.0}]
        rt.goal_manager.motivation_boost.return_value = 0
        rt.goal_manager.active_goals.return_value = []
        rt.attention.attention_competition.return_value = [{"_label": "a"}]
        rt.context_engine.assemble.return_value = "ctx"
        rt.emotion_engine.format_context_block.return_value = ""
        rt.intent_engine.format_context_block.return_value = ""
        rt.reflective_engine.format_context_block.return_value = ""
        rt.values_governance.format_context_block.return_value = ""
        rt.narrative.generate_identity_anchor.return_value = ""
        rt.narrative.get_current_narrative_summary.return_value = ""
        rt.self_model.to_prompt_block.return_value = ""
        rt.working_self.goal_focus = "x"
        rt.working_self.cumulative_coherence = 0.5
        rt.working_self.prediction_error = 0.1

        pipe = RecallPipeline(rt)
        pipe.recall("hello", mutate_state=True, use_attention=True)

        rt.state.sync_from_attention.assert_called_once()
        rt.working_self.sync_to_legacy.assert_called_once()


class TestAuthorityDispatcher(unittest.TestCase):
    def test_memory_read_uses_projection(self):
        runtime = MagicMock()
        runtime.recall.return_value = "ctx"
        disp = AuthorityDispatcher(runtime)

        out = disp.memory_recall("query")

        self.assertEqual(out, "ctx")
        runtime.recall.assert_called_once()
        _, kwargs = runtime.recall.call_args
        self.assertFalse(kwargs.get("mutate_state", True))

    def test_dispatch_sets_context(self):
        runtime = MagicMock()
        runtime.run_governance_cycle.return_value = {"ok": True}
        disp = AuthorityDispatcher(runtime)

        with patch("core.control_plane.dispatch.dispatch_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            disp.governance_cycle()
            mock_ctx.assert_called_once()

    def test_chat_confirm_accepts_prepare_id_positional(self):
        runtime = MagicMock()
        runtime.confirm_prepared_chat_turn.return_value = {"reply": "hi"}
        disp = AuthorityDispatcher(runtime)

        out = disp.chat_confirm("prep-abc", send_mode="user_only", temperature=0.2)

        self.assertEqual(out["reply"], "hi")
        runtime.confirm_prepared_chat_turn.assert_called_once_with(
            "prep-abc",
            temperature=0.2,
            llm_client=None,
            llm_profile=None,
            allow_proactive=True,
            send_mode="user_only",
        )


if __name__ == "__main__":
    unittest.main()

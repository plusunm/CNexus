"""CP-1.5 — WriteIntentBus and RecallAdapter shadow emit tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.types import DispatchContext, RouteKind
from core.governance.gtbs.adapters.capture_adapter import (
    build_capture_write_intent,
    emit_capture_write_intent,
    maybe_emit_capture_direct_shadow,
)
from core.governance.gtbs.adapters.cdg_adapter import (
    build_cdg_apply_write_intent,
    emit_cdg_apply_write_intent,
    maybe_emit_cdg_apply_shadow,
)
from core.governance.gtbs.adapters.recall_adapter import (
    emit_recall_side_effect_intent,
    maybe_emit_recall_side_effect,
)
from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.capture_boundary import CaptureMutationBoundary
from core.governance.gtbs.write_intent import (
    MutabilityLevel,
    WriteIntentKind,
)
from core.governance.gtbs.write_intent_bus import (
    WriteIntentBus,
    shadow_emit_enabled,
    write_intent_provenance_scope,
)
from memory.runtime_guard import runtime_write_context
from runtime.recall_pipeline import RecallPipeline


class TestWriteIntentBus(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.log = GTBSTransactionLog(self._tmpdir.name)
        self.bus = WriteIntentBus(self.log)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_emit_shadow_writes_proposal_event(self):
        intent_id = emit_recall_side_effect_intent(
            self.bus,
            query="hello world",
            top_k=6,
            use_attention=True,
            activated_count=2,
            top_labels=["goal", "intent"],
        )
        self.assertTrue(intent_id.startswith("prop-"))
        rows = self.log.read_all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "proposal")
        payload = rows[0]["payload"]
        self.assertTrue(payload.get("shadow"))
        self.assertEqual(payload["write_intent_kind"], WriteIntentKind.RECALL_SIDE_EFFECT.value)
        self.assertEqual(payload["mutability"], MutabilityLevel.IMPLICIT.value)
        self.assertEqual(payload["gtbs_mode"], "SHADOW_EMIT")

    def test_provenance_scope_merged_into_intent(self):
        with write_intent_provenance_scope(
            trace_id="trace-abc",
            dispatch_kind="memory_read",
            caller="http",
            channel="test-channel",
            entry_registry="memory_recall",
        ):
            with runtime_write_context(token="rt-tok-1"):
                intent_id = emit_recall_side_effect_intent(
                    self.bus,
                    query="q",
                    top_k=3,
                    use_attention=False,
                    activated_count=1,
                    top_labels=["a"],
                )
        rows = self.log.read_all()
        prov = rows[0]["payload"]["provenance"]
        self.assertEqual(prov["trace_id"], "trace-abc")
        self.assertEqual(prov["dispatch_kind"], "memory_read")
        self.assertEqual(prov["entry_registry"], "memory_recall")
        self.assertEqual(prov["runtime_token"], "rt-tok-1")
        self.assertEqual(rows[0]["transaction_id"], intent_id)

    def test_shadow_emit_disabled_by_env(self):
        with patch.dict(os.environ, {"GTBS_WRITE_INTENT_SHADOW": "0"}):
            self.assertFalse(shadow_emit_enabled())
        with patch.dict(os.environ, {"GTBS_WRITE_INTENT_SHADOW": "1"}):
            self.assertTrue(shadow_emit_enabled())


class TestRecallAdapterIntegration(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base_dir = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    def _build_runtime_mock(self):
        rt = MagicMock()
        rt.recall_top_k = 3
        rt.runtime_mode = "legacy"
        rt.base_dir = self.base_dir
        rt.config = {"gtbs": {"enable_write_intent_shadow": True}}
        rt.router.hybrid_recall.return_value = [
            {"_label": "goal", "_final_score": 1.0},
            {"_label": "intent", "_final_score": 0.8},
        ]
        rt.goal_manager.motivation_boost.return_value = 0
        rt.goal_manager.active_goals.return_value = []
        rt.attention.attention_competition.return_value = [{"_label": "goal"}]
        rt.attention.focus_scores_by_label.return_value = {"goal": 0.9}
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

        from core.governance.gtbs.transaction_log import GTBSTransactionLog
        from core.governance.gtbs.write_intent_bus import WriteIntentBus

        rt._get_write_intent_bus = MagicMock(
            return_value=WriteIntentBus(GTBSTransactionLog(self.base_dir))
        )
        return rt

    def test_mutate_state_emits_shadow_intent(self):
        rt = self._build_runtime_mock()
        pipe = RecallPipeline(rt)
        with runtime_write_context(token="internal-tok"):
            pipe.recall("hello", mutate_state=True, use_attention=True)

        rt.state.sync_from_attention.assert_called_once()
        rt._get_write_intent_bus.assert_called()
        log_path = os.path.join(self.base_dir, "observability", "gtbs_transactions.jsonl")
        self.assertTrue(os.path.isfile(log_path))
        with open(log_path, encoding="utf-8") as fh:
            row = json.loads(fh.readline())
        self.assertEqual(row["payload"]["write_intent_kind"], "recall_side_effect")

    def test_mutate_state_false_does_not_emit(self):
        rt = self._build_runtime_mock()
        pipe = RecallPipeline(rt)
        pipe.recall("hello", mutate_state=False)
        rt._get_write_intent_bus.assert_not_called()

    def test_shadow_disabled_skips_emit(self):
        rt = self._build_runtime_mock()
        rt.config = {"gtbs": {"enable_write_intent_shadow": False}}
        pipe = RecallPipeline(rt)
        pipe.recall("hello", mutate_state=True)
        rt._get_write_intent_bus.assert_not_called()

    def test_maybe_emit_returns_none_without_bus_hook(self):
        rt = MagicMock(spec=[])
        rt.config = {"gtbs": {"enable_write_intent_shadow": True}}
        self.assertIsNone(
            maybe_emit_recall_side_effect(
                rt,
                query="q",
                top_k=3,
                use_attention=True,
                activated=[],
                recall_results=[],
            )
        )


class TestDispatchProvenanceBinding(unittest.TestCase):
    def test_dispatch_wraps_execute_with_write_intent_provenance(self):
        runtime = MagicMock()
        captured: dict = {}

        def fake_execute(ctx):
            from core.governance.gtbs.write_intent_bus import build_current_provenance

            captured["prov"] = build_current_provenance().to_dict()
            return "ok"

        disp = AuthorityDispatcher(runtime)
        disp._execute = fake_execute  # type: ignore[method-assign]

        result = disp.dispatch(
            DispatchContext(
                kind=RouteKind.MEMORY_READ,
                payload={"query": "test"},
                caller="http",
                channel="test-ui",
                trace_id="dispatch-trace-1",
            )
        )

        self.assertEqual(result, "ok")
        self.assertEqual(captured["prov"]["trace_id"], "dispatch-trace-1")
        self.assertEqual(captured["prov"]["dispatch_kind"], "memory_read")
        self.assertEqual(captured["prov"]["caller"], "http")
        self.assertEqual(captured["prov"]["entry_registry"], "memory_recall")


class TestCaptureAdapter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.log = GTBSTransactionLog(self._tmpdir.name)
        self.bus = WriteIntentBus(self.log)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_emit_capture_write_intent(self):
        intent = emit_capture_write_intent(
            self.bus,
            role="user",
            content="hello capture",
            layer="episodic",
            importance=0.7,
        )
        self.assertEqual(intent.kind.value, WriteIntentKind.CAPTURE.value)
        rows = self.log.read_all()
        self.assertEqual(rows[0]["payload"]["write_intent_kind"], "capture")
        self.assertEqual(rows[0]["payload"]["mutability"], MutabilityLevel.EXPLICIT.value)

    def test_capture_boundary_uses_write_intent_bus(self):
        boundary = CaptureMutationBoundary(self.log, write_intent_bus=self.bus)
        result = boundary.propose_and_commit(
            role="user",
            content="test content",
            layer="episodic",
            importance=0.6,
            emotional_weight=0.5,
            meta={},
            validate=lambda: (True, "ok", 0.1),
            commit=lambda: "mem-123",
        )
        self.assertEqual(result, "mem-123")
        types = [e["event_type"] for e in self.log.read_all()]
        self.assertEqual(types, ["proposal", "approval", "commit"])
        self.assertEqual(self.log.read_all()[0]["payload"]["write_intent_kind"], "capture")


class TestCdgAdapter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.log = GTBSTransactionLog(self._tmpdir.name)
        self.bus = WriteIntentBus(self.log)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_emit_cdg_apply_write_intent(self):
        modified = {
            "working_self": {"goal_focus": "x"},
            "self_model": {"coherence_score": 0.8},
            "flags": ["REALITY_OVERRIDE_APPLIED"],
        }
        intent = emit_cdg_apply_write_intent(
            self.bus,
            phase="interaction",
            pre_state={"beliefs": []},
            proposed_state={"beliefs": [{"id": "1"}]},
            modified_state=modified,
            decision_summary={"approved": True},
        )
        self.assertEqual(intent.kind.value, WriteIntentKind.CDG_APPLY.value)
        payload = self.log.read_all()[0]["payload"]
        self.assertEqual(payload["write_intent_kind"], "cdg_apply")
        self.assertEqual(payload["mutability"], MutabilityLevel.ADVISORY.value)

    def test_run_cdg_cycle_emits_shadow_intent(self):
        from dataclasses import dataclass, field
        from typing import Any, Dict, List

        @dataclass
        class FakeDecision:
            approved: bool = True
            modified_state: Dict[str, Any] = field(
                default_factory=lambda: {"working_self": {"goal_focus": "a"}}
            )
            rcs: float = 0.9
            interventions: List[str] = field(default_factory=list)
            alerts: List[str] = field(default_factory=list)
            metrics: Dict[str, Any] = field(default_factory=dict)

            def to_dict(self):
                return {"approved": self.approved}

        rt = MagicMock()
        rt.config = {"gtbs": {"enable_write_intent_shadow": True}}
        rt.base_dir = self._tmpdir.name
        rt._get_write_intent_bus = MagicMock(return_value=self.bus)
        rt.cdg.run.return_value = FakeDecision()

        from brain_memory.runtime import BrainMemoryRuntime

        BrainMemoryRuntime._run_cdg_cycle(
            rt,
            {"beliefs": []},
            {"beliefs": [{"id": "1"}]},
            phase="interaction",
        )

        rows = self.log.read_all()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["payload"]["write_intent_kind"], "cdg_apply")
        self.assertEqual(rows[1]["event_type"], "commit")


class TestStep2dAdapters(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.log = GTBSTransactionLog(self._tmpdir.name)
        self.bus = WriteIntentBus(self.log)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_ir_commit_intent(self):
        from core.governance.gtbs.adapters.ir_adapter import emit_ir_commit_intent
        from ir_kernel.schema.sigma_exec import CommitEvent

        events = [CommitEvent(kind="capture", role="user", content="hi")]
        intent = emit_ir_commit_intent(self.bus, events=events)
        self.assertEqual(intent.kind.value, WriteIntentKind.IR_COMMIT.value)

    def test_chat_deferred_intent(self):
        from core.governance.gtbs.adapters.chat_deferred_adapter import emit_chat_deferred_intent

        intent = emit_chat_deferred_intent(
            self.bus,
            text="hello",
            capture_id="cap-1",
            grounding_event_id="g-1",
        )
        self.assertEqual(intent.kind.value, WriteIntentKind.CHAT_DEFERRED.value)

    def test_working_self_intent(self):
        from core.governance.gtbs.adapters.working_self_adapter import emit_working_self_intent

        intent = emit_working_self_intent(
            self.bus,
            text_preview="hello",
            importance=0.65,
        )
        self.assertEqual(intent.kind.value, WriteIntentKind.WORKING_SELF.value)


if __name__ == "__main__":
    unittest.main()

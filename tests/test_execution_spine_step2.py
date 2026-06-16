"""CP-2.5 Step 2 — execution context + mutation hook tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.guards import warn_direct_runtime_access
from core.governance.gtbs.state_snapshot import TierASnapshot, snapshot_tier_a
from core.governance.gtbs.write_funnel import execute_write_intent
from core.governance.gtbs.write_intent import (
    MutabilityLevel,
    WriteIntent,
    WriteIntentKind,
    WriteProvenance,
)
from core.governance.gtbs.types import GovernanceProposal, JustificationSource, OperationType, StateDelta
from core.runtime.trace_context import get_trace_id, trace_scope
from core.spine.execution_context import note_execution_event, resolve_recall_trigger
from core.spine.hooks.mutation import emit_capture_mutation
from core.spine.integration import register_spine_writer
from core.spine.storage import SpineEventLog
from core.spine.writer import SpineWriter


class TestExecutionContext(unittest.TestCase):
    def test_recall_trigger_resolution(self):
        note_execution_event("recall", "recall-1")
        self.assertEqual(resolve_recall_trigger(), "recall-1")


class TestAutoTrace(unittest.TestCase):
    def test_direct_access_starts_trace(self):
        from core.runtime import trace_context

        trace_context._current_trace_id.set(None)
        warn_direct_runtime_access("recall")
        self.assertTrue(get_trace_id() and get_trace_id().startswith("trace-direct-recall-"))


class TestWriteFunnelTriggeredBy(unittest.TestCase):
    def test_state_diff_links_to_intent_spine_event(self):
        tmp = tempfile.TemporaryDirectory()
        writer = SpineWriter(SpineEventLog(tmp.name))
        register_spine_writer(writer)

        runtime = MagicMock()
        runtime.config = {"gtbs": {"enable_write_intent_shadow": True}}
        bus = MagicMock()
        bus.emit.return_value = "intent-1"

        def _emit_side_effect(intent, config=None):
            with trace_scope("trace-funnel"):
                writer.emit(
                    trace_id="trace-funnel",
                    event_type="write_intent",
                    summary="intent",
                    action="propose",
                )
            return "intent-1"

        bus.emit.side_effect = _emit_side_effect
        runtime._get_write_intent_bus.return_value = bus

        proposal = GovernanceProposal(
            operation_type=OperationType.INGEST,
            deltas=[
                StateDelta(
                    target_store="storage",
                    payload={"x": 1},
                    description="test",
                )
            ],
            justification={"source": JustificationSource.INTERACTION.value},
            source="test",
        )
        intent = WriteIntent(
            kind=WriteIntentKind.CAPTURE,
            mutability=MutabilityLevel.EXPLICIT,
            proposal=proposal,
            provenance=WriteProvenance(trace_id="trace-funnel"),
        )

        before = TierASnapshot(working_self={"a": 1}, legacy_state={})
        after = TierASnapshot(working_self={"a": 2}, legacy_state={})

        call_count = {"n": 0}

        def _snap(_rt):
            call_count["n"] += 1
            return before if call_count["n"] == 1 else after

        with trace_scope("trace-funnel"):
            with unittest.mock.patch(
                "core.governance.gtbs.write_funnel.snapshot_tier_a", side_effect=_snap
            ):
                with unittest.mock.patch(
                    "core.governance.gtbs.write_funnel.tx_rollback_enabled", return_value=False
                ):
                    execute_write_intent(runtime, intent, lambda: "ok")

        rows = writer._log.read_all()
        state_rows = [r for r in rows if r.get("event_type") == "state"]
        self.assertEqual(len(state_rows), 1)
        edges = state_rows[0].get("causal_edges") or []
        relations = {e["relation"] for e in edges}
        self.assertIn("triggered_by", relations)

        register_spine_writer(None)
        tmp.cleanup()


class TestCaptureMutationHook(unittest.TestCase):
    def test_emit_capture_mutation_uses_recall_trigger(self):
        tmp = tempfile.TemporaryDirectory()
        writer = SpineWriter(SpineEventLog(tmp.name))
        register_spine_writer(writer)

        with trace_scope("trace-cap"):
            note_execution_event("recall", "recall-x")
            emit_capture_mutation(
                memory_id="m1",
                role="user",
                layer="episodic",
                importance=0.5,
            )

        rows = writer._log.read_all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "memory_mutation")
        edges = rows[0].get("causal_edges") or []
        self.assertTrue(any(e.get("relation") == "triggered_by" for e in edges))

        register_spine_writer(None)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

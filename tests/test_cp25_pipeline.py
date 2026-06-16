"""Execution Tap standardization, Explain Bind v2, Self-Healing Spine tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.execution_tap import get_execution_tap, reset_execution_tap
from core.spine.execution.bind_v2 import bind_explanation_to_execution_v2, build_frame_execution_bind
from core.spine.execution.builder import build_execution_graph
from core.spine.healing.repair import SpineHealer
from core.spine.integration import register_spine_writer
from core.spine.query.builder import run_query
from core.spine.query.builder_v2 import enrich_with_drift
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEvent
from core.spine.writer import SpineWriter


class TestExecutionTapStandardization(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base = self._tmpdir.name
        reset_execution_tap()
        self.writer = SpineWriter(SpineEventLog(self.base))
        register_spine_writer(self.writer)

    def tearDown(self):
        register_spine_writer(None)
        self._tmpdir.cleanup()
        reset_execution_tap()

    def test_spine_writer_mirrors_tap(self):
        self.writer.emit(
            trace_id="t-tap",
            event_type="control",
            summary="control warn",
            subsystem="control_plane",
            decision="WARN",
        )
        tap = get_execution_tap().events_for_trace("t-tap")
        self.assertEqual(len(tap), 1)
        self.assertTrue(tap[0]["spine_written"])
        self.assertEqual(tap[0]["type"], "control")

    def test_state_patch_mirrors_tap(self):
        self.writer.project_state_patch(
            trace_id="t-tap",
            patch={"change_count": 1, "changes": [{"field": "goal_focus"}]},
        )
        tap = get_execution_tap().events_for_trace("t-tap")
        self.assertEqual(len(tap), 1)
        self.assertEqual(tap[0]["type"], "state")


class TestExplainBindV2(unittest.TestCase):
    def test_bind_v2_path_frames(self):
        events = [
            {"event_id": "e1", "event_type": "dispatch", "trace_id": "t1", "timestamp": "1"},
            {"event_id": "e2", "event_type": "recall", "trace_id": "t1", "timestamp": "2"},
        ]
        graph = build_execution_graph("t1", events)
        bound = bind_explanation_to_execution_v2({"narrative": "test"}, graph, events)
        self.assertIn("execution_v2", bound)
        self.assertEqual(bound["execution_v2"]["version"], "execution-bind-v2")
        self.assertTrue(bound["execution_v2"]["path_frames"])

    def test_stream_frame_bind(self):
        events = [
            {"event_id": "e1", "event_type": "chat", "trace_id": "t1"},
            {"event_id": "e2", "event_type": "llm_call", "trace_id": "t1"},
        ]
        bind = build_frame_execution_bind("t1", events, "e2")
        self.assertIn("execution_path", bind)
        self.assertEqual(bind["path_frames"][-1]["event_id"], "e2")


class TestSelfHealingSpine(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base = self._tmpdir.name
        reset_execution_tap()
        self.writer = SpineWriter(SpineEventLog(self.base))
        register_spine_writer(self.writer)
        self.log = SpineEventLog(self.base)
        row = {
            "event_id": "e1",
            "trace_id": "t-heal",
            "timestamp": "2026-06-14T00:00:01+00:00",
            "event_type": "recall",
            "subsystem": "runtime",
            "action": "read",
            "summary": "recall",
        }
        self.log.append(SpineEvent.from_dict(row))
        get_execution_tap().record(
            event_type="chat",
            summary="chat missing",
            trace_id="t-heal",
            spine_written=False,
        )

    def tearDown(self):
        register_spine_writer(None)
        self._tmpdir.cleanup()
        reset_execution_tap()

    def test_healer_suggests_backfill(self):
        from core.spine.drift.detector import RuntimeSpineDriftDetector

        tap = get_execution_tap().events_for_trace("t-heal")
        spine = [{"event_id": "e1", "event_type": "recall", "trace_id": "t-heal"}]
        drift = RuntimeSpineDriftDetector().compare("t-heal", tap, spine)
        healer = SpineHealer()
        suggestions = healer.suggest(drift, tap)
        self.assertTrue(any(s["action"] == "backfill_spine" for s in suggestions))

    def test_healer_dry_run_backfill(self):
        from core.spine.drift.detector import RuntimeSpineDriftDetector

        tap = get_execution_tap().events_for_trace("t-heal")
        spine = [{"event_id": "e1", "event_type": "recall", "trace_id": "t-heal"}]
        drift = RuntimeSpineDriftDetector().compare("t-heal", tap, spine)
        healer = SpineHealer()
        result = healer.apply_backfill("t-heal", drift.missing, tap, apply=False)
        self.assertTrue(result["dry_run"])
        self.assertGreaterEqual(result["would_backfill"], 1)

    def test_query_v2_includes_heal_meta(self):
        v1 = run_query(self.base, trace_id="t-heal")
        v2 = enrich_with_drift(v1, self.base)
        meta = v2.to_dict()["meta"]
        self.assertIn("heal_suggestions", meta)
        self.assertIn("execution_v2", v2.to_dict()["explanation"])


if __name__ == "__main__":
    unittest.main()

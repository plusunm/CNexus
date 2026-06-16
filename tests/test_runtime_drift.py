"""Runtime ↔ Spine drift detector v1 tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.execution_tap import reset_execution_tap, get_execution_tap
from core.spine.drift.annotator import DriftAnnotator
from core.spine.drift.detector import RuntimeSpineDriftDetector
from core.spine.query.builder_v2 import enrich_with_drift, get_drift_report
from core.spine.query.builder import run_query
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEvent


class TestRuntimeDrift(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base = self._tmpdir.name
        self.log = SpineEventLog(self.base)
        reset_execution_tap()
        self.tap = get_execution_tap()

        rows = [
            {
                "event_id": "e1",
                "trace_id": "t-drift",
                "timestamp": "2026-06-14T00:00:01+00:00",
                "event_type": "recall",
                "subsystem": "runtime",
                "action": "read",
                "summary": "recall",
            },
            {
                "event_id": "e2",
                "trace_id": "t-drift",
                "timestamp": "2026-06-14T00:00:02+00:00",
                "event_type": "llm_call",
                "subsystem": "runtime",
                "action": "read",
                "summary": "llm",
            },
        ]
        for row in rows:
            self.log.append(SpineEvent.from_dict(row))

        self.tap.record(
            event_type="recall",
            summary="recall",
            trace_id="t-drift",
            event_id="e1",
            spine_written=True,
        )
        self.tap.record(
            event_type="chat",
            summary="chat only in runtime",
            trace_id="t-drift",
            spine_written=False,
        )

    def tearDown(self):
        self._tmpdir.cleanup()
        reset_execution_tap()

    def test_detector_missing_runtime_only(self):
        detector = RuntimeSpineDriftDetector()
        runtime_events = self.tap.events_for_trace("t-drift")
        spine_events = [
            {"event_id": "e1", "event_type": "recall", "trace_id": "t-drift"},
            {"event_id": "e2", "event_type": "llm_call", "trace_id": "t-drift"},
        ]
        report = detector.compare("t-drift", runtime_events, spine_events)
        self.assertGreaterEqual(report.missing_count, 1)
        self.assertLess(report.score, 1.0)

    def test_detector_extra_in_spine(self):
        detector = RuntimeSpineDriftDetector()
        runtime_events = [{"event_id": "e1", "event_type": "recall", "trace_id": "t-drift"}]
        spine_events = [
            {"event_id": "e1", "event_type": "recall", "trace_id": "t-drift"},
            {"event_id": "e99", "event_type": "control", "trace_id": "t-drift"},
        ]
        report = detector.compare("t-drift", runtime_events, spine_events)
        self.assertEqual(report.extra_count, 1)

    def test_annotator_marks_events(self):
        detector = RuntimeSpineDriftDetector()
        runtime_events = self.tap.events_for_trace("t-drift")
        spine_events = [
            {"event_id": "e1", "event_type": "recall", "trace_id": "t-drift", "summary": "recall"},
            {"event_id": "e2", "event_type": "llm_call", "trace_id": "t-drift", "summary": "llm"},
        ]
        drift = detector.compare("t-drift", runtime_events, spine_events)
        annotator = DriftAnnotator()
        annotated = annotator.annotate_events(spine_events, drift, runtime_events=runtime_events)
        statuses = {e["event_id"]: e["drift_status"] for e in annotated}
        self.assertIn("e1", statuses)
        self.assertEqual(statuses["e1"], "OK")

    def test_query_v2_enrichment(self):
        v1 = run_query(self.base, trace_id="t-drift")
        v2 = enrich_with_drift(v1, self.base)
        body = v2.to_dict()
        self.assertEqual(body["schema_version"], "spine-query-2")
        self.assertIn("drift_summary", body["meta"])
        self.assertTrue(any("drift_status" in e for e in body["events"]))

    def test_drift_api_helper(self):
        report = get_drift_report(self.base, "t-drift")
        self.assertEqual(report["trace_id"], "t-drift")
        self.assertIn("score", report)


if __name__ == "__main__":
    unittest.main()

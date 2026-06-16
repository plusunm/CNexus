"""Execution tap persistence + Explain v3 tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.execution_tap import get_execution_tap, reset_execution_tap
from core.runtime.tap_bootstrap import configure_execution_tap_persistence
from core.runtime.tap_storage import ExecutionTapLog
from core.spine.explain_v3 import build_drift_aware_explanation
from core.spine.integration import register_spine_writer
from core.spine.query.builder_v2 import apply_explain_v3, enrich_with_drift
from core.spine.query.builder import run_query
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEvent
from core.spine.writer import SpineWriter


class TestTapPersistence(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base = self._tmpdir.name
        reset_execution_tap()

    def tearDown(self):
        reset_execution_tap()
        self._tmpdir.cleanup()

    def test_persist_and_hydrate(self):
        configure_execution_tap_persistence(self.base)
        tap = get_execution_tap()
        tap.record(
            event_type="chat",
            summary="hello",
            trace_id="t-persist",
            spine_written=False,
        )
        self.assertTrue(ExecutionTapLog(self.base).path.exists())

        reset_execution_tap()
        configure_execution_tap_persistence(self.base)
        merged = get_execution_tap().events_for_trace_merged("t-persist")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["type"], "chat")


class TestExplainV3(unittest.TestCase):
    def test_caveats_for_missing(self):
        events = [
            {
                "event_id": "e1",
                "event_type": "chat",
                "drift_status": "MISSING",
                "confidence": 0.2,
            }
        ]
        out = build_drift_aware_explanation(
            "t1",
            events,
            fusion_v2={"explanation": {"summary": "base", "causal_story": ["chat (e1) recorded"]}},
            drift_summary={"score": 0.5, "missing_count": 1, "extra_count": 0, "mismatch_count": 0},
        )
        self.assertEqual(out["version"], "explain-v3")
        self.assertTrue(out["caveats"])
        self.assertIn("Epistemic confidence", out["summary"])

    def test_query_v2_includes_explain_v3(self):
        tmp = tempfile.TemporaryDirectory()
        base = tmp.name
        reset_execution_tap()
        register_spine_writer(SpineWriter(SpineEventLog(base)))
        log = SpineEventLog(base)
        log.append(
            SpineEvent.from_dict(
                {
                    "event_id": "e1",
                    "trace_id": "t-v3",
                    "timestamp": "2026-06-14T00:00:01+00:00",
                    "event_type": "recall",
                    "subsystem": "runtime",
                    "action": "read",
                    "summary": "recall",
                }
            )
        )
        get_execution_tap().record(
            event_type="chat",
            summary="orphan",
            trace_id="t-v3",
            spine_written=False,
        )
        v1 = run_query(base, trace_id="t-v3")
        v2 = enrich_with_drift(v1, base)
        body = v2.to_dict()
        self.assertIn("explain_v3", body["explanation"])
        self.assertEqual(body["meta"].get("explain_engine"), "explain-v3")
        register_spine_writer(None)
        reset_execution_tap()
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

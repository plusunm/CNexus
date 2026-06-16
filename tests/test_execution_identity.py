"""Execution Identity Layer v1 tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.identity.equivalence import ReplayEquivalence
from core.spine.identity.kernel import ExecutionIdentityKernel
from core.spine.identity.service import ExecutionIdentityService
from core.spine.identity.store import configure_identity_store, reset_identity_store
from core.spine.integration import register_spine_writer
from core.spine.query.builder_v3 import enrich_with_identity, run_query_v3
from core.spine.query.builder import run_query
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEvent
from core.spine.writer import SpineWriter


def _seed_events(trace_id: str, suffix: str = "") -> list[dict]:
    return [
        {
            "event_id": f"e1{suffix}",
            "trace_id": trace_id,
            "timestamp": "2026-06-14T00:00:01+00:00",
            "event_type": "dispatch",
            "subsystem": "control_plane",
            "action": "read",
            "summary": "dispatch",
        },
        {
            "event_id": f"e2{suffix}",
            "trace_id": trace_id,
            "timestamp": "2026-06-14T00:00:02+00:00",
            "event_type": "recall",
            "subsystem": "runtime",
            "action": "read",
            "summary": "recall user memory",
        },
    ]


class TestExecutionIdentityKernel(unittest.TestCase):
    def test_same_structure_same_identity(self):
        kernel = ExecutionIdentityKernel()
        bundle_a = {"graph": {"nodes": [{"phase": "trigger", "event_type": "dispatch"}], "edges": []}, "state": {}, "control": [], "events": []}
        bundle_b = {"graph": {"nodes": [{"phase": "trigger", "event_type": "dispatch"}], "edges": []}, "state": {}, "control": [], "events": []}
        self.assertEqual(kernel.compute(bundle_a), kernel.compute(bundle_b))

    def test_different_structure_different_identity(self):
        kernel = ExecutionIdentityKernel()
        a = {"graph": {"nodes": [{"phase": "trigger", "event_type": "dispatch"}], "edges": []}, "state": {}, "control": [], "events": []}
        b = {"graph": {"nodes": [{"phase": "trigger", "event_type": "chat"}], "edges": []}, "state": {}, "control": [], "events": []}
        self.assertNotEqual(kernel.compute(a), kernel.compute(b))


class TestReplayEquivalence(unittest.TestCase):
    def test_equivalent_traces(self):
        eq = ReplayEquivalence()
        result = eq.compare_traces("t1", _seed_events("t1"), "t2", _seed_events("t2"))
        self.assertTrue(result["equivalent"])
        self.assertEqual(result["identity_a"], result["identity_b"])


class TestIdentityQueryV3(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base = self._tmpdir.name
        reset_identity_store()
        configure_identity_store(self.base)
        register_spine_writer(SpineWriter(SpineEventLog(self.base)))
        self.log = SpineEventLog(self.base)
        for row in _seed_events("t-id-a"):
            self.log.append(SpineEvent.from_dict(row))
        for row in _seed_events("t-id-b"):
            self.log.append(SpineEvent.from_dict(row))

    def tearDown(self):
        register_spine_writer(None)
        reset_identity_store()
        self._tmpdir.cleanup()

    def test_query_v3_includes_identity(self):
        result = run_query_v3(self.base, trace_id="t-id-a")
        body = result.to_dict()
        self.assertEqual(body["schema_version"], "spine-query-3")
        identity = body["meta"]["identity"]
        self.assertTrue(identity["identity"].startswith("I-"))
        self.assertIn("equivalent_traces", identity)

    def test_store_registers_equivalent(self):
        svc = ExecutionIdentityService()
        events_a = _seed_events("t-x")
        events_b = _seed_events("t-y")
        id1 = svc.resolve_for_response(
            "t-x", events_a, control=[], state={"deltas": [], "patches": []}, execution={}, base_dir=None
        )["identity"]
        id2 = svc.resolve_for_response(
            "t-y", events_b, control=[], state={"deltas": [], "patches": []}, execution={}, base_dir=None
        )["identity"]
        self.assertEqual(id1, id2)


if __name__ == "__main__":
    unittest.main()

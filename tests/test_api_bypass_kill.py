"""API Bypass Kill + schema freeze contract tests."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = Path(__file__).resolve().parents[1]

from core.kernel.schema.schema_lock import SchemaViolation, validate_execution_record
from core.kernel.verify.protocol import run_verification


class TestApiBypassKill(unittest.TestCase):
    def test_memory_routes_use_dispatcher(self):
        path = ROOT / "brain-memory-ui" / "api" / "routes" / "memory.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn("get_dispatcher().memory_maintenance", source)
        self.assertIn("get_dispatcher().capture_cognition", source)
        self.assertIn("get_dispatcher().observe_read", source)
        self.assertNotRegex(source, r"runtime\.run_memory_maintenance")
        self.assertNotRegex(source, r"runtime\.process_capture_cognition")

    def test_reflective_routes_use_dispatcher(self):
        path = ROOT / "brain-memory-ui" / "api" / "routes" / "reflective.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn("get_dispatcher().reflect_review", source)
        self.assertIn("get_dispatcher().reflect_due_reviews", source)
        self.assertNotIn("get_runtime", source)

    def test_governance_routes_use_dispatcher(self):
        path = ROOT / "brain-memory-ui" / "api" / "routes" / "governance.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn("get_dispatcher().governance_validate", source)
        self.assertIn("get_dispatcher().observe_read", source)
        self.assertNotIn("get_runtime", source)

    def test_ci_bypass_scan_passes(self):
        script = ROOT / "ci" / "kernel_hard_contract" / "scan_for_bypass.py"
        proc = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class TestExecutionRecordSchemaFreeze(unittest.TestCase):
    def test_frozen_v1_valid(self):
        sample = {
            "version": "execution-record-v1",
            "trace_id": "t1",
            "intent_type": "recall",
            "result": "ok",
            "identity": None,
            "graph_invariant": None,
            "graph": None,
            "nodes": [],
            "edges": [],
            "equivalence": None,
            "state_projection": {},
            "causal_projection": {},
            "explain_projection": {},
            "replay_signature": None,
            "audit_log": {},
            "audit": {},
            "events": [],
            "derivation": {},
            "elapsed_ms": 1.0,
        }
        validate_execution_record(sample)

    def test_unknown_field_rejected(self):
        sample = {
            "version": "execution-record-v1",
            "trace_id": "t1",
            "intent_type": "recall",
            "result": "ok",
            "identity": None,
            "graph": None,
            "nodes": [],
            "edges": [],
            "state_projection": {},
            "causal_projection": {},
            "explain_projection": {},
            "replay_signature": None,
            "audit_log": {},
            "events": [],
            "derivation": {},
            "elapsed_ms": 1.0,
            "token_field": {},
        }
        with self.assertRaises(SchemaViolation):
            validate_execution_record(sample)

    def test_kernel_materialize_passes_schema(self):
        from core.kernel.hooks import enqueue_spine_event  # noqa: F401
        from core.kernel.intent import ExecutionIntent
        from core.kernel.kernel import ExecutionKernel

        runtime = MagicMock()
        runtime.recall.return_value = "ctx"
        kernel = ExecutionKernel(runtime)
        with patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "0"}):
            with patch("core.kernel.hooks.enqueue_spine_event"):
                record = kernel.execute(ExecutionIntent(type="recall", payload={"query": "a"}))
        data = record.to_dict()
        validate_execution_record(data)


class TestClosureScoreRegression(unittest.TestCase):
    def test_closure_score_improved_after_bypass_kill(self):
        report = run_verification()
        self.assertGreater(report.closure_score, 62.5)
        blocker_ids = {f.id for f in report.findings if f.severity.value == "blocker"}
        self.assertFalse(
            any("reflective" in bid or "memory" in bid or "governance" in bid for bid in blocker_ids),
            f"API bypass blockers should be cleared: {blocker_ids}",
        )


if __name__ == "__main__":
    unittest.main()

"""Kernel Final Verification Protocol — static + runtime closure tests."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_plane.types import DispatchContext, RouteKind
from core.kernel.enforce.exceptions import KernelViolation
from core.kernel.enforce.mode import hard_lock_mode, legacy_allowed
from core.kernel.intent import ExecutionIntent
from core.kernel.kernel import ExecutionKernel
from core.kernel.verify.protocol import (
    KERNEL_VERIFY_VERSION,
    Severity,
    format_report,
    run_verification,
)


class TestKernelFinalVerificationStatic(unittest.TestCase):
    def test_protocol_runs_and_scores(self):
        report = run_verification()
        self.assertEqual(report.version, KERNEL_VERIFY_VERSION)
        self.assertGreaterEqual(report.closure_score, 0.0)
        self.assertLessEqual(report.closure_score, 100.0)
        self.assertIn(report.status, ("OPEN", "PARTIAL", "CLOSED"))
        self.assertEqual(len(report.dimensions), 5)
        print("\n" + format_report(report))

    def test_hard_lock_env_contract(self):
        report = run_verification()
        self.assertTrue(report.env.get("KERNEL_HARD_LOCK_MODE"), "hard lock must be on by default")
        self.assertFalse(report.env.get("KERNEL_LEGACY_ALLOW"), "legacy must be disallowed")
        self.assertTrue(report.env.get("USE_EXECUTION_KERNEL"), "kernel must be enabled")

    def test_no_api_bypass_blockers(self):
        report = run_verification()
        blocker_ids = {f.id for f in report.findings if f.severity == Severity.BLOCKER}
        api_blockers = {bid for bid in blocker_ids if bid.startswith("api-bypass")}
        self.assertEqual(api_blockers, set(), f"API bypass blockers remain: {api_blockers}")

    def test_closure_score_improved_since_pre_lock(self):
        """Regression guard: post CP-3 Hard Lock score must exceed pre-lock baseline (~41)."""
        report = run_verification()
        self.assertGreater(
            report.closure_score,
            41.0,
            "closure score should improve after Kernel Hard Lock + UI Projection Lock v1",
        )


class TestKernelFinalVerificationRuntime(unittest.TestCase):
    def test_only_kernel_produces_record(self):
        runtime = MagicMock()
        runtime.recall.return_value = "ctx"
        kernel = ExecutionKernel(runtime)

        with patch.dict(
            os.environ,
            {
                "KERNEL_HARD_LOCK_MODE": "1",
                "KERNEL_ENFORCE_MODE": "1",
                "USE_EXECUTION_GRAPH": "0",
            },
        ):
            with patch("core.kernel.hooks.enqueue_spine_event"):
                record = kernel.execute(ExecutionIntent(type="recall", payload={"query": "a"}))

        self.assertEqual(record.intent_type, "recall")
        self.assertTrue(record.trace_id)
        stored = kernel.get_record(record.trace_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.trace_id, record.trace_id)

    def test_legacy_path_unreachable_under_hard_lock(self):
        from core.control_plane.dispatch import AuthorityDispatcher

        runtime = MagicMock()
        dispatcher = AuthorityDispatcher(runtime)
        ctx = DispatchContext(kind=RouteKind.MEMORY_READ, payload={"query": "x"})

        with patch.dict(
            os.environ,
            {
                "KERNEL_HARD_LOCK_MODE": "1",
                "KERNEL_ENFORCE_MODE": "0",
                "USE_EXECUTION_KERNEL": "0",
            },
        ):
            self.assertTrue(hard_lock_mode())
            self.assertFalse(legacy_allowed())
            with self.assertRaises(KernelViolation):
                dispatcher._execute_legacy(ctx)

    def test_dispatcher_kernel_truth_chain(self):
        from core.control_plane.dispatch import AuthorityDispatcher

        runtime = MagicMock()
        runtime.recall.return_value = "hit"
        dispatcher = AuthorityDispatcher(runtime)

        with patch.dict(
            os.environ,
            {
                "KERNEL_HARD_LOCK_MODE": "1",
                "USE_EXECUTION_GRAPH": "0",
            },
        ):
            with patch("core.kernel.hooks.enqueue_spine_event"):
                out = dispatcher._execute(
                    DispatchContext(kind=RouteKind.MEMORY_READ, payload={"query": "q"}),
                )

        self.assertEqual(out, "hit")
        runtime.recall.assert_called_once()


class TestKernelFinalVerificationReportFormat(unittest.TestCase):
    def test_format_report_contains_dimensions(self):
        report = run_verification()
        text = format_report(report)
        self.assertIn("Closure Score:", text)
        self.assertIn("kernel_entry_purity", text)
        self.assertIn("ui_projection_purity", text)


if __name__ == "__main__":
    unittest.main()

"""X3-a observability compliance AST guard tests."""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.verify.compliance import (
    ComplianceViolationError,
    assert_observability_compliance,
    scan_observe_leaks,
)


class TestObservabilityCompliance(unittest.TestCase):
    def test_detects_get_runtime_memory_stats(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        bad = tmp / "api" / "routes"
        bad.mkdir(parents=True)
        (bad / "leak.py").write_text(
            textwrap.dedent(
                """
                def handler():
                    from brain_memory.runtime import get_runtime
                    return get_runtime().memory_stats()
                """
            ),
            encoding="utf-8",
        )
        hits = scan_observe_leaks(tmp, include_baseline=False)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].method, "memory_stats")

    def test_allows_kernel_directory(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        kernel = tmp / "core" / "kernel"
        kernel.mkdir(parents=True)
        (kernel / "probe.py").write_text(
            "def ok():\n    return get_runtime().memory_stats()\n",
            encoding="utf-8",
        )
        hits = scan_observe_leaks(tmp, include_baseline=False)
        self.assertEqual(hits, [])

    def test_assert_raises_on_new_violation(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        core = tmp / "core" / "skill"
        core.mkdir(parents=True)
        (core / "new_leak.py").write_text(
            "def x():\n    return get_runtime().get_current_state()\n",
            encoding="utf-8",
        )
        with self.assertRaises(ComplianceViolationError) as ctx:
            assert_observability_compliance(tmp, include_baseline=False)
        self.assertEqual(ctx.exception.violations[0].method, "get_current_state")

    def test_baseline_excluded_by_default(self) -> None:
        assert_observability_compliance(include_baseline=False)

    def test_repo_has_zero_observe_leaks(self) -> None:
        hits = scan_observe_leaks(include_baseline=False)
        self.assertEqual(hits, [], msg=str(hits))


if __name__ == "__main__":
    unittest.main()

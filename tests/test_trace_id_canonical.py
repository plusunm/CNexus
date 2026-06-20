"""Layer 2 trace_id canonical format and legacy compat tests."""

from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.trace_context import get_trace_id, reset_trace_context, start_trace, trace_scope
from core.runtime.trace_id import (
    CANONICAL_TRACE_ID_RE,
    coerce_trace_id,
    generate_trace_id,
    is_canonical_trace_id,
    is_legacy_trace_id,
    normalize_trace_id,
)


class TestTraceIdCanonical(unittest.TestCase):
    def tearDown(self) -> None:
        reset_trace_context()

    def test_generate_matches_runbook_pattern(self) -> None:
        tid = generate_trace_id()
        self.assertRegex(tid, CANONICAL_TRACE_ID_RE)
        self.assertTrue(is_canonical_trace_id(tid))
        self.assertFalse(is_legacy_trace_id(tid))

    def test_is_legacy_semantic_ids(self) -> None:
        self.assertTrue(is_legacy_trace_id("trace-explicit"))
        self.assertTrue(is_legacy_trace_id("trace-evolved-1700000000000"))
        self.assertFalse(is_legacy_trace_id("t-abc1234567890abcd"))

    def test_normalize_upgrades_legacy_hex12_only(self) -> None:
        legacy = "trace-abcdef123456"
        normalized = normalize_trace_id(legacy)
        self.assertTrue(is_canonical_trace_id(normalized))
        self.assertTrue(normalized.startswith("t-abcdef123456"))

    def test_normalize_preserves_semantic_legacy(self) -> None:
        semantic = "trace-direct-recall-deadbeef"
        self.assertEqual(normalize_trace_id(semantic), semantic)

    def test_coerce_preserves_explicit_legacy(self) -> None:
        self.assertEqual(coerce_trace_id("trace-keep-me"), "trace-keep-me")

    def test_start_trace_generates_canonical_when_empty(self) -> None:
        tid = start_trace()
        self.assertTrue(is_canonical_trace_id(tid))

    def test_start_trace_preserves_explicit_legacy(self) -> None:
        tid = start_trace("trace-legacy-session-99")
        self.assertEqual(tid, "trace-legacy-session-99")
        self.assertTrue(is_legacy_trace_id(tid))


class TestTraceContextGeneration(unittest.TestCase):
    def setUp(self) -> None:
        reset_trace_context()

    def test_trace_scope_auto_generates_canonical(self) -> None:
        with trace_scope() as tid:
            self.assertTrue(is_canonical_trace_id(tid))
            self.assertEqual(get_trace_id(), tid)

    def test_trace_scope_explicit_legacy_unchanged(self) -> None:
        with trace_scope("trace-explicit-compat") as tid:
            self.assertEqual(tid, "trace-explicit-compat")
            self.assertTrue(is_legacy_trace_id(tid))


class TestLegacyCompatRead(unittest.TestCase):
    """Production-style legacy strings must remain readable after L2-1."""

    LEGACY_FIXTURES = (
        "trace-evolved-1700000000000",
        "trace-proj-1",
        "trace-r1",
        "trace-direct-recall-legacy",
    )

    def test_legacy_fixtures_not_canonical_but_valid_strings(self) -> None:
        for tid in self.LEGACY_FIXTURES:
            self.assertTrue(is_legacy_trace_id(tid), tid)
            self.assertFalse(is_canonical_trace_id(tid), tid)
            with trace_scope(tid):
                self.assertEqual(get_trace_id(), tid)

    def test_sigma_mapping_derives_from_legacy_timestamp_id(self) -> None:
        from core.evolved.sigma_mapping import derive_timestamps_from_trace

        out = derive_timestamps_from_trace("trace-evolved-1700000000000")
        self.assertIn("block_created_at", out)
        self.assertIn("2023", out["block_created_at"])


if __name__ == "__main__":
    unittest.main()

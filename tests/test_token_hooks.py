"""Token runtime hooks tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.spine.integration import register_spine_writer
from core.spine.storage import SpineEventLog
from core.spine.token.hooks import emit_tokens_for_llm_usage, maybe_emit_for_event_type
from core.spine.token.token_store import configure_token_store, read_tokens
from core.spine.types import SpineEvent
from core.spine.writer import SpineWriter


class TestTokenHooks(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base = self._tmpdir.name
        configure_token_store(self.base)
        register_spine_writer(SpineWriter(SpineEventLog(self.base)))

    def tearDown(self):
        register_spine_writer(None)
        self._tmpdir.cleanup()

    def test_llm_usage_hook(self):
        emit_tokens_for_llm_usage(
            "t-hook",
            spine_event_id="e-llm",
            prompt_tokens=100,
            completion_tokens=40,
            base_dir=self.base,
            caller="test",
        )
        rows = read_tokens("t-hook", base_dir=self.base)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total"], 140)
        self.assertEqual(rows[0]["source"], "llm_generate")

    def test_recall_spine_hook(self):
        event = SpineEvent(
            event_id="e-recall",
            trace_id="t-hook",
            timestamp="2026-06-14T00:00:01+00:00",
            event_type="recall",
            subsystem="gtbs",
            action="read",
            summary="recall test",
            payload={"query": "hello world", "result_count": 3},
        )
        maybe_emit_for_event_type(event, base_dir=self.base)
        rows = read_tokens("t-hook", base_dir=self.base)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["phase"], "RECALL")


if __name__ == "__main__":
    unittest.main()

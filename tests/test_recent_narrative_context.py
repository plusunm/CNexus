"""L3-1 — recent narrative context from Σ.T (cross-shard, legacy + canonical trace ids)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.personality.narrative.recent_context import (
    build_recent_narrative_prompt_block,
    format_recent_narrative,
    load_recent_narrative_prompt_block,
)
from core.runtime.trace_store import read_recent_interaction_steps


def _step_row(
    *,
    step: str,
    ts: float,
    trace_id: str,
) -> dict:
    return {
        "ts": ts,
        "mono_ms": int(ts * 1000),
        "type": "interaction_step",
        "step": step,
        "trace_id": trace_id,
    }


class TestReadRecentInteractionSteps(unittest.TestCase):
    def test_cross_shard_mixed_trace_ids_within_window(self) -> None:
        base = tempfile.mkdtemp()
        traces = Path(base) / "traces"
        traces.mkdir(parents=True)
        now = time.time()
        day_a = datetime.fromtimestamp(now - 86400, tz=timezone.utc).date()
        day_b = datetime.fromtimestamp(now - 60, tz=timezone.utc).date()

        legacy_tid = "trace-evolved-session-legacy"
        canonical_tid = "t-abcdef1234567890"

        rows_a = [
            _step_row(step="cdg_ingest", ts=now - 90000, trace_id=legacy_tid),
            {"ts": now - 89900, "mono_ms": 1, "type": "l3_tick"},
        ]
        rows_b = [
            _step_row(step="capture_user", ts=now - 120, trace_id=canonical_tid),
            _step_row(step="complete", ts=now - 30, trace_id=canonical_tid),
        ]
        (traces / f"{day_a.isoformat()}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows_a) + "\n",
            encoding="utf-8",
        )
        (traces / f"{day_b.isoformat()}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows_b) + "\n",
            encoding="utf-8",
        )

        steps = read_recent_interaction_steps(base, since_hours=48, limit=10)
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0]["step"], "cdg_ingest")
        self.assertEqual(steps[0]["trace_id"], legacy_tid)
        self.assertTrue(steps[1]["trace_id"].startswith("t-"))
        self.assertEqual(steps[-1]["step"], "complete")

    def test_respects_since_hours_and_limit(self) -> None:
        base = tempfile.mkdtemp()
        traces = Path(base) / "traces"
        traces.mkdir(parents=True)
        now = time.time()
        today = datetime.fromtimestamp(now, tz=timezone.utc).date()
        rows = [
            _step_row(step=f"step-{i}", ts=now - i * 3600, trace_id=f"t-{'a' * 16}")
            for i in range(6)
        ]
        (traces / f"{today.isoformat()}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n",
            encoding="utf-8",
        )

        steps = read_recent_interaction_steps(base, since_hours=2.5, limit=2)
        self.assertLessEqual(len(steps), 2)
        for row in steps:
            self.assertGreaterEqual(float(row["ts"]), now - 2.5 * 3600)

    def test_legacy_single_file_fallback(self) -> None:
        base = tempfile.mkdtemp()
        now = time.time()
        legacy = Path(base) / "execution_trace.jsonl"
        legacy.write_text(
            json.dumps(_step_row(step="recall_context", ts=now - 10, trace_id="trace-legacy-abc")) + "\n",
            encoding="utf-8",
        )
        steps = read_recent_interaction_steps(base, since_hours=1, limit=5)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["step"], "recall_context")


class TestRecentContextFormatting(unittest.TestCase):
    def test_format_recent_narrative_plain_ledger(self) -> None:
        ts = datetime(2026, 6, 20, 8, 30, tzinfo=timezone.utc).timestamp()
        text = format_recent_narrative(
            [
                _step_row(step="cdg_ingest", ts=ts, trace_id="trace-old-1"),
                _step_row(step="complete", ts=ts + 60, trace_id="t-1234567890abcdef"),
            ]
        )
        self.assertIn("cdg_ingest", text)
        self.assertIn("complete", text)
        self.assertIn("trace-old-1", text)
        self.assertIn("t-1234567890abcdef", text)

    def test_prompt_block_semantic_header(self) -> None:
        block = build_recent_narrative_prompt_block(
            [_step_row(step="capture_user", ts=time.time(), trace_id="t-abc1234567890abcd")]
        )
        self.assertIn("Recent Activity", block)
        self.assertIn("not your long-term identity", block)
        self.assertIn("capture_user", block)

    def test_load_empty_when_no_store(self) -> None:
        self.assertEqual(load_recent_narrative_prompt_block(None), "")
        self.assertEqual(load_recent_narrative_prompt_block(tempfile.mkdtemp()), "")


class TestRecallPipelineIntegration(unittest.TestCase):
    def test_recall_includes_recent_narrative_before_identity_block(self) -> None:
        from runtime.recall_pipeline import RecallPipeline

        base = tempfile.mkdtemp()
        traces = Path(base) / "traces"
        traces.mkdir(parents=True)
        now = time.time()
        today = datetime.fromtimestamp(now, tz=timezone.utc).date()
        (traces / f"{today.isoformat()}.jsonl").write_text(
            json.dumps(_step_row(step="interaction_step_marker", ts=now - 5, trace_id="t-fedcba9876543210"))
            + "\n",
            encoding="utf-8",
        )

        rt = MagicMock()
        rt.base_dir = base
        rt.recall_top_k = 3
        rt.runtime_mode = "g1"
        rt.router.hybrid_recall.return_value = []
        rt.context_engine.assemble.return_value = "MEMORY_CTX"
        rt.emotion_engine.format_context_block.return_value = ""
        rt.intent_engine.format_context_block.return_value = ""
        rt.reflective_engine.format_context_block.return_value = ""
        rt.values_governance.format_context_block.return_value = ""
        rt.narrative.generate_identity_anchor.return_value = "ANCHOR"
        rt.narrative.get_current_narrative_summary.return_value = "LONG_TERM_SUMMARY"
        rt.self_model.to_prompt_block.return_value = "SELF_BLOCK"
        rt.working_self.goal_focus = "g"
        rt.working_self.cumulative_coherence = 0.9
        rt.working_self.prediction_error = 0.1
        rt.attention.focus_scores_by_label.return_value = {}
        rt.goal_manager.motivation_boost.return_value = 0.0
        rt.goal_manager.active_goals.return_value = []

        pipeline = RecallPipeline(rt)
        full = pipeline.recall("hello", use_attention=False)

        anchor_pos = full.find("ANCHOR")
        recent_pos = full.find("Recent Activity")
        identity_pos = full.find("Identity Context — long-term")
        memory_pos = full.find("MEMORY_CTX")

        self.assertGreater(recent_pos, anchor_pos)
        self.assertGreater(identity_pos, recent_pos)
        self.assertGreater(memory_pos, identity_pos)
        self.assertIn("interaction_step_marker", full)
        self.assertIn("LONG_TERM_SUMMARY", full)
        self.assertTrue(pipeline.last_explain.get("recent_narrative_present"))


if __name__ == "__main__":
    unittest.main()

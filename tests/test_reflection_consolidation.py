"""L3-3 — daily reflection consolidation and fast-lane decide isolation."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evolved.cognitive_hooks import apply_consolidation_step
from core.personality.reflection.daily_consolidation import (
    propose_consolidation_deltas,
    run_daily_consolidation,
)
from core.runtime.l3_scheduler import L3GovernanceScheduler, L3TaskKind
from core.runtime.reflection_background import enqueue_daily_reflection
from core.runtime.trace_store import append_trace_row
from core.self_model import SelfModelStore
from core.self_model.domain_storage import DomainStorageAdapter


def _write_interaction_step(base_dir: str, *, step: str = "complete", trace_id: str = "t-abc123") -> None:
    append_trace_row(
        base_dir,
        {
            "type": "interaction_step",
            "step": step,
            "trace_id": trace_id,
            "message": "用户讨论了长期稳定与诚实协作",
        },
    )


class TestReflectionConsolidation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = SelfModelStore(self.tmp)
        self.adapter = DomainStorageAdapter(self.tmp)
        self.store.model.core_beliefs = {
            "稳定性优先": 0.93,
            "诚实第一": 0.96,
            "主体连续性": 0.91,
        }
        self.store.model.autobiographical_story = "基线自传体故事"
        self.store.model.identity_summary = "基线身份摘要"
        self.store.save()

    def test_consolidation_updates_decide_only(self) -> None:
        _write_interaction_step(self.tmp)
        cognize_path = self.adapter.domain_path("cognize")
        meta_path = self.adapter.domain_path("store_meta")
        decide_path = self.adapter.domain_path("decide")
        cognize_mtime = cognize_path.stat().st_mtime
        meta_mtime = meta_path.stat().st_mtime
        decide_before = json.loads(decide_path.read_text(encoding="utf-8"))
        time.sleep(0.05)

        result = run_daily_consolidation(self.store, base_dir=self.tmp)
        self.assertFalse(result.get("skipped"))
        self.assertEqual(result.get("step"), "DAILY_CONSOLIDATION")

        self.assertGreater(decide_path.stat().st_mtime, cognize_mtime)
        self.assertEqual(cognize_path.stat().st_mtime, cognize_mtime)
        self.assertEqual(meta_path.stat().st_mtime, meta_mtime)

        decide_after = json.loads(decide_path.read_text(encoding="utf-8"))
        self.assertIn("基线自传体故事", decide_after["autobiographical_story"])
        self.assertNotEqual(decide_after["autobiographical_story"], decide_before["autobiographical_story"])
        self.assertEqual(decide_after["identity_summary"], decide_before["identity_summary"])
        self.assertIn("稳定性优先", decide_after["core_beliefs"])

    def test_merge_append_never_clears_baseline(self) -> None:
        apply_consolidation_step(
            self.store,
            autobiography_delta="新增段落",
            beliefs_delta={"稳定性优先": 0.01},
        )
        self.assertIn("基线自传体故事", self.store.model.autobiographical_story)
        self.assertIn("新增段落", self.store.model.autobiographical_story)
        self.assertGreater(self.store.model.core_beliefs["稳定性优先"], 0.93)

    def test_propose_deltas_from_observed_ledger_only(self) -> None:
        ledger = "• 06-18 12:00 UTC — complete trace=t-abc123"
        deltas = propose_consolidation_deltas(ledger)
        self.assertTrue(deltas.get("autobiography_delta"))
        self.assertIsInstance(deltas.get("beliefs_delta"), dict)

    def test_l3_scheduler_runs_daily_reflection(self) -> None:
        _write_interaction_step(self.tmp)
        runtime = MagicMock()
        runtime.base_dir = self.tmp
        runtime.self_model_store = self.store

        scheduler = L3GovernanceScheduler()
        enqueued = enqueue_daily_reflection(runtime, scheduler)
        self.assertTrue(enqueued)

        while scheduler.queue_length():
            scheduler.run_tick()

        decide = json.loads(self.adapter.domain_path("decide").read_text(encoding="utf-8"))
        self.assertIn("Σ.T", decide["autobiographical_story"])


class TestFastLaneStripped(unittest.TestCase):
    """L0 chat contract: cognize-only persist — decide/meta domains stay locked."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = SelfModelStore(self.tmp)
        self.adapter = DomainStorageAdapter(self.tmp)
        self.store.save()

    def test_chat_cognize_step_does_not_persist_decide(self) -> None:
        from core.evolved.cognitive_hooks import apply_cognize_step

        decide_path = self.adapter.domain_path("decide")
        meta_path = self.adapter.domain_path("store_meta")
        cognize_path = self.adapter.domain_path("cognize")
        decide_mtime = decide_path.stat().st_mtime
        meta_mtime = meta_path.stat().st_mtime
        time.sleep(0.05)

        apply_cognize_step(self.store, user_input="hello fast lane", response="pong")

        self.assertGreater(cognize_path.stat().st_mtime, decide_mtime)
        self.assertEqual(decide_path.stat().st_mtime, decide_mtime)
        self.assertEqual(meta_path.stat().st_mtime, meta_mtime)

    def test_legacy_integrate_still_writes_all_domains(self) -> None:
        """Contrast — full integrate remains on non-chat paths only."""
        decide_path = self.adapter.domain_path("decide")
        decide_mtime = decide_path.stat().st_mtime
        time.sleep(0.05)

        self.store.integrate("深度协作", "响应", reflection="反思")

        self.assertGreater(decide_path.stat().st_mtime, decide_mtime)

    def test_runtime_chat_mode_branch_skips_integrate(self) -> None:
        import memory.filter as memory_filter
        from enum import Enum

        if not hasattr(memory_filter, "CaptureMode"):

            class _CaptureMode(str, Enum):
                CHAT = "chat"
                INGEST = "ingest"
                SYSTEM = "system"
                RAW = "raw"

            memory_filter.CaptureMode = _CaptureMode

        from brain_memory import runtime as runtime_module

        store = SelfModelStore(self.tmp)
        store.save()
        adapter = DomainStorageAdapter(self.tmp)
        decide_mtime = adapter.domain_path("decide").stat().st_mtime

        runtime = MagicMock()
        runtime.self_model_store = store
        runtime.dna_engine = MagicMock(dna=None)
        runtime.working_self = MagicMock(relationship_tone=0.7)
        runtime.narrative = MagicMock()
        runtime.config = {"reflective_use_llm": False, "reflection_cooldown_turns": 99}
        runtime._attention_turn = 1
        runtime._last_reflection_turn = 0
        runtime.reflective_engine = MagicMock()
        runtime.goal_manager = MagicMock(current_focus=lambda: None)

        original_integrate = store.integrate
        store.integrate = MagicMock(side_effect=original_integrate)  # type: ignore[method-assign]

        runtime_module.BrainMemoryRuntime._apply_post_cdg_interaction_updates(
            runtime,
            text="fast lane",
            response="pong",
            reflection="r",
            error=0.1,
            context="",
            chat_mode=True,
        )

        store.integrate.assert_not_called()
        self.assertEqual(adapter.domain_path("decide").stat().st_mtime, decide_mtime)


if __name__ == "__main__":
    unittest.main()

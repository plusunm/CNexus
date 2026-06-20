"""X2 domain-split SelfModel persistence tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evolved.cognitive_hooks import (
    apply_cognize_step,
    apply_decide_step,
    apply_store_selfmodel_step,
)
from core.self_model import SelfModel, SelfModelStore
from core.self_model.domain_storage import DomainStorageAdapter


class TestDomainStorageAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.adapter = DomainStorageAdapter(self.tmp)

    def test_legacy_migration_splits_and_renames(self) -> None:
        unified = self.adapter.unified_path
        unified.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "identity_summary": "测试身份",
            "autobiographical_story": "故事",
            "core_beliefs": {"稳定性优先": 0.9},
            "relational_models": {"user": {"trust": 0.8, "tone": "neutral"}},
            "self_expectations": {"consistency": 0.92},
            "future_projection": {"next_focus": "x"},
            "stable_behavioral_bias": {"cautious": 0.75},
            "coherence_score": 0.88,
            "last_reconstruction": "2026-01-01T00:00:00",
            "total_experiences": 3,
        }
        unified.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        model = self.adapter.load()
        self.assertEqual(model.total_experiences, 3)
        self.assertTrue(self.adapter.domains_complete())
        self.assertFalse(unified.exists())
        self.assertTrue(self.adapter.unified_legacy_path.exists())

        cognize = json.loads(self.adapter.domain_path("cognize").read_text(encoding="utf-8"))
        decide = json.loads(self.adapter.domain_path("decide").read_text(encoding="utf-8"))
        meta = json.loads(self.adapter.domain_path("store_meta").read_text(encoding="utf-8"))
        self.assertIn("relational_models", cognize)
        self.assertIn("identity_summary", decide)
        self.assertEqual(meta["total_experiences"], 3)

    def test_save_domain_does_not_touch_other_files_mtime(self) -> None:
        model = SelfModel()
        self.adapter.save_all_domains(model)
        decide_path = self.adapter.domain_path("decide")
        meta_path = self.adapter.domain_path("store_meta")
        decide_mtime = decide_path.stat().st_mtime
        meta_mtime = meta_path.stat().st_mtime
        time.sleep(0.05)

        model.coherence_score = 0.91
        self.adapter.save_domain("cognize", model)

        self.assertGreater(self.adapter.domain_path("cognize").stat().st_mtime, decide_mtime)
        self.assertEqual(decide_path.stat().st_mtime, decide_mtime)
        self.assertEqual(meta_path.stat().st_mtime, meta_mtime)


class TestSelfModelStoreDomainWrites(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = SelfModelStore(self.tmp)

    def test_integrate_persists_all_domains(self) -> None:
        self.store.integrate("稳定连续", "ok", reflection="r")
        adapter = DomainStorageAdapter(self.tmp)
        self.assertTrue(adapter.domains_complete())
        reloaded = SelfModelStore(self.tmp)
        self.assertGreater(reloaded.model.total_experiences, 0)

    def test_cognitive_hooks_partial_writes(self) -> None:
        adapter = DomainStorageAdapter(self.tmp)
        self.store.model.coherence_score = 0.77
        apply_cognize_step(self.store, user_input="hi", response="ho")
        cognize = json.loads(adapter.domain_path("cognize").read_text(encoding="utf-8"))
        self.assertEqual(cognize["coherence_score"], 0.77)
        self.assertFalse(adapter.domain_path("decide").exists())

        apply_decide_step(self.store, intent_type="control")
        self.assertTrue(adapter.domain_path("decide").exists())

        apply_store_selfmodel_step(self.store, block_updated_at="2026-06-19T12:00:00+00:00")
        meta = json.loads(adapter.domain_path("store_meta").read_text(encoding="utf-8"))
        self.assertEqual(meta["last_reconstruction"], "2026-06-19T12:00:00+00:00")

    def test_reload_merges_domains(self) -> None:
        self.store.integrate("经历", "响应", reflection="反思")
        store2 = SelfModelStore(self.tmp)
        self.assertIn("反思", store2.model.autobiographical_story)
        self.assertGreater(store2.model.total_experiences, 0)


if __name__ == "__main__":
    unittest.main()

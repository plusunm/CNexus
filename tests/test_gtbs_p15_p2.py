"""GTBS P1.5 / P1.2 tests — shadow persistence and capture propose-commit."""

import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory import create_runtime
from core.governance.gtbs.divergence_collector import GTBSShadowDivergenceCollector
from core.governance.gtbs.gatekeeper import RuntimeGatekeeper
from core.governance.gtbs.transaction_log import GTBSTransactionLog


@contextmanager
def isolated_memory_dir(path: str):
    """Pin BM_MEMORY_DIR so tests do not read/write shared staging data."""
    prev = os.environ.get("BM_MEMORY_DIR")
    os.environ["BM_MEMORY_DIR"] = path
    try:
        yield path
    finally:
        if prev is None:
            os.environ.pop("BM_MEMORY_DIR", None)
        else:
            os.environ["BM_MEMORY_DIR"] = prev


class TestGTBSShadowPersistence(unittest.TestCase):
    def test_collector_appends_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = GTBSShadowDivergenceCollector(tmp)
            collector.record({"type": "gtbs_shadow_observation", "x": 1})
            rows = collector.read_all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["x"], 1)

    def test_runtime_persists_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_memory_dir(tmp):
                runtime = create_runtime(base_dir=tmp)
                runtime.config.setdefault("cdg", {})["enable_gtbs_shadow"] = True
                runtime.config["cdg"]["gtbs_shadow_persist"] = True
                runtime._gtbs_shadow_observe({"a": 1}, {"b": 2}, context={"phase": "test"})
                path = GTBSShadowDivergenceCollector(runtime.base_dir).path
                self.assertTrue(path.exists())
            with open(path, encoding="utf-8") as fh:
                row = json.loads(fh.readline())
            self.assertEqual(row["type"], "gtbs_shadow_observation")

    def test_proposal_vs_reality_metrics(self):
        gk = RuntimeGatekeeper()
        out = gk.observe_runtime_event(
            {"memory": [], "beliefs": []},
            {"memory": [{"id": "1"}], "flags": []},
            proposal={
                "target_stores": ["storage"],
                "proposed_keys": ["memory", "beliefs"],
            },
        )
        pvr = out["proposal_vs_reality"]
        self.assertIsNotNone(pvr["key_jaccard"])
        self.assertIn("unexpected_changes", pvr)


class TestGTBSCapturePilot(unittest.TestCase):
    def test_capture_legacy_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_memory_dir(tmp):
                runtime = create_runtime(base_dir=tmp)
                self.assertFalse(runtime._gtbs_capture_enabled())
                mid = runtime.capture("user", "我希望长期构建稳定的人格 AI 系统", importance=0.7)
                self.assertIsInstance(mid, str)
                self.assertFalse(mid.startswith("denied"))
                log = GTBSTransactionLog(runtime.base_dir)
                self.assertEqual(len(log.read_all()), 0)

    def test_capture_gtbs_writes_transaction_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_memory_dir(tmp):
                runtime = create_runtime(base_dir=tmp)
                runtime.config.setdefault("cdg", {})["enable_gtbs_capture"] = True
                mid = runtime.capture("user", "我希望长期构建稳定的人格 AI 系统", importance=0.7)
                self.assertIsInstance(mid, str)
                events = GTBSTransactionLog(runtime.base_dir).read_all()
                types = [e["event_type"] for e in events]
                self.assertEqual(types, ["proposal", "approval", "commit"])
                self.assertEqual(events[-1]["payload"]["memory_id"], mid)


if __name__ == "__main__":
    unittest.main()

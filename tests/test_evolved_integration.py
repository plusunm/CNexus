"""CNexus-evolved integration tests — Layers 1–6."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evolved.migration_runner import MigrationRunner
from core.evolved.store_step import apply_sigma_to_block, build_store_projection, is_store_intent
from core.evolved.trace_emit import emit_sigma_trace
from core.kernel.record import ExecutionRecord
from core.runtime.execution_trace import trace_file_path
from core.runtime.trace_context import trace_scope
from memory.block import MemoryBlock
from memory.block_store import MemoryBlockStore


class TestEvolvedBlockStore(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.store = MemoryBlockStore(os.path.join(self._tmpdir, "blocks"))

    def test_persist_sigma_slot_on_create(self):
        with trace_scope("trace-evolved-1700000000000"):
            block = MemoryBlock.from_label("persona", "evolved content")
            created = self.store.create(block)
        self.assertEqual(created.metadata.get("sigma_slot"), "Σ.M")
        self.assertIn("block_updated_at", created.metadata)
        self.assertGreaterEqual(int(created.metadata.get("iteration_counter", 0)), 1)

        path = self.store._block_path(created.block_id)
        persisted = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["metadata"]["sigma_slot"], "Σ.M")

    def test_get_sigma_projection(self):
        with trace_scope("trace-proj-1"):
            created = self.store.create(MemoryBlock.from_label("intent", "goal"))
        proj = self.store.get_sigma_projection(created.block_id)
        self.assertIsNotNone(proj)
        self.assertEqual(proj["slot"], "Σ.M")
        self.assertEqual(proj["label"], "intent")


class TestEvolvedStoreProjection(unittest.TestCase):
    def test_build_store_projection_from_record(self):
        record = ExecutionRecord(
            trace_id="t-store-1",
            intent_type="capture",
            result={"block_id": "b1", "label": "working_memory"},
            state_projection={"stability_metrics": {"importance_snapshot": 0.8}},
        )
        proj = build_store_projection(record)
        self.assertEqual(proj["slot"], "Σ.M")
        self.assertEqual(proj["trace_id"], "t-store-1")
        self.assertEqual(proj["importance_snapshot"], 0.8)
        self.assertTrue(is_store_intent("capture"))

    def test_record_helper_methods(self):
        record = ExecutionRecord(trace_id="t-2", intent_type="recall", result="ok")
        self.assertEqual(record.build_sigma_trace()["slot"], "Σ.T")
        store_proj = record.build_store_projection()
        self.assertEqual(store_proj.get("intent_type"), "recall")


class TestEvolvedTraceEmit(unittest.TestCase):
    def test_emit_sigma_trace_writes_jsonl(self):
        tmp = tempfile.mkdtemp()
        record = ExecutionRecord(trace_id="t-trace-1", intent_type="chat", result={"ok": True})
        emit_sigma_trace(tmp, record)
        path = trace_file_path(tmp)
        self.assertTrue(path.exists())
        row = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertEqual(row["type"], "kernel_execution")
        self.assertEqual(row["sigma_trace_slot"], "Σ.T")
        self.assertEqual(row["trace_id"], "t-trace-1")


class TestMigrationRunner(unittest.TestCase):
    def test_loads_mapping_ir(self):
        runner = MigrationRunner()
        summary = runner.summary()
        if summary["loaded"]:
            self.assertGreaterEqual(summary["total_mappings"], 40)
            self.assertIn("exists", summary["classification_summary"])


class TestApplySigmaToBlock(unittest.TestCase):
    def test_apply_sigma_increments_iteration(self):
        block = MemoryBlock.from_label("emotion", "calm")
        sigma = apply_sigma_to_block(block, trace_id="t-3")
        self.assertEqual(sigma["slot"], "Σ.M")
        self.assertEqual(block.metadata.get("store_step"), "STORE")
        self.assertGreaterEqual(int(block.metadata.get("iteration_counter", 0)), 1)


if __name__ == "__main__":
    unittest.main()

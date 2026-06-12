import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.block import LABEL_PRIORITY
from memory.manager import MemoryManager
from runtime.router import HierarchicalRecallEngine, HierarchicalRecallRouter, RecallResult
from storage.manager import UnifiedStorageManager


class TestHierarchicalRecallEngine(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.storage = UnifiedStorageManager(base_dir=self._tmpdir, vector_dim=768)
        self.manager = MemoryManager(self._tmpdir, storage=self.storage, bypass_runtime_guard=True)
        self.engine = HierarchicalRecallEngine(self.storage, memory_manager=self.manager)

        self.manager.create_block("persona", "稳定、理性、工程优先的认知伙伴")
        self.manager.create_block("intent", "推进 L1 MemoryBlock 架构落地")
        self.manager.create_block("emotion", "情绪平稳，专注协作")

        self.storage.capture_memory(
            "user", "这是一条历史对话记录", layer="episodic", importance=0.4
        )
        self.storage.capture_memory(
            "user", "identity core belief", layer="identity", importance=0.9
        )

    def test_recall_blocks_by_label_priority(self):
        results = self.engine.recall_blocks("我的长期目标是什么")
        labels = [r["_label"] for r in results]
        self.assertIn("persona", labels)
        self.assertIn("intent", labels)
        self.assertEqual(labels[0], "persona")

    def test_always_in_context_core_blocks(self):
        results = self.engine.recall_blocks("随便聊聊")
        labels = {r["_label"] for r in results}
        self.assertIn("persona", labels)
        self.assertIn("emotion", labels)
        self.assertIn("intent", labels)

    def test_hybrid_recall_merges_blocks_and_episodic(self):
        results = self.engine.hybrid_recall("identity 目标", top_k=8)
        sources = {r.get("_source") for r in results}
        self.assertIn("block", sources)
        self.assertIn("episodic", sources)

    def test_inject_context_shows_structured_blocks(self):
        results = self.engine.hybrid_recall("persona intent", top_k=6)
        context = self.engine.inject_context(results)
        self.assertIn("Structured Memory Blocks", context)
        self.assertIn("persona", context)

    def test_route_returns_label_metadata(self):
        routed = self.engine.route("我的目标", top_k=6)
        self.assertGreater(routed["block_count"], 0)
        self.assertIn("persona", routed["used_labels"])
        self.assertIn("label_intent", routed)

    def test_backward_compat_router_alias(self):
        router = HierarchicalRecallRouter(self.storage, memory_manager=self.manager)
        self.assertIsInstance(router, HierarchicalRecallEngine)
        results = router.hybrid_recall("目标", top_k=4)
        self.assertTrue(any(r.get("_source") == "block" for r in results))

    def test_episodic_only_without_memory_manager(self):
        engine = HierarchicalRecallEngine(self.storage, memory_manager=None)
        results = engine.hybrid_recall("identity", top_k=4)
        self.assertTrue(all(r.get("_source") != "block" for r in results))
        self.assertTrue(len(results) > 0)

    def test_unified_recall_uses_block_store(self):
        results = self.engine.recall("我的长期目标", top_k=6)
        self.assertTrue(any(r.source == "block" for r in results))
        self.assertIn("persona", {r.label for r in results if r.source == "block"})
        stats = self.engine.get_stats()
        self.assertGreaterEqual(stats.get("returned", 0), 1)

    def test_recall_episodic_only_typed_blocks(self):
        self.manager.append_episodic_entry(
            "dialogue",
            {"speaker": "user", "utterance": "下一步做什么"},
        )
        results = self.engine.recall_episodic_only("dialogue", limit=3)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "episodic")

    def test_label_intent_detection(self):
        intent = self.engine.detect_label_intent("我的长期目标是什么")
        self.assertGreater(intent.get("intent", 0), 0.5)
        self.assertEqual(intent.get("persona", 0), 0.0)


class TestRuntimeBlockRecall(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_runtime_recall_includes_blocks(self):
        from brain_memory import BrainMemoryRuntime

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        runtime.capture(
            "user",
            "长期维护稳定的人格与身份连续性",
            layer="identity",
            importance=0.92,
        )
        ctx = runtime.recall("我的身份和目标")
        self.assertIn("Structured Memory Blocks", ctx)
        self.assertIn("persona", ctx)

    def test_get_core_context_blocks_priority(self):
        from brain_memory import BrainMemoryRuntime
        from memory.runtime_guard import runtime_write_context

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        with runtime_write_context():
            runtime.memory.create_block("emotion", "情绪平稳")
            runtime.memory.create_block("persona", "人格稳定")
            runtime.memory.create_block("intent", "推进架构")
        blocks = runtime.memory.get_core_context_blocks()
        self.assertEqual(blocks[0].label, "persona")
        self.assertEqual(
            blocks[0].label,
            max(blocks, key=lambda b: LABEL_PRIORITY.get(b.label, 0)).label,
        )


if __name__ == "__main__":
    unittest.main()

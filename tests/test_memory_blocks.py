import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.block import (
    BLOCK_SPECS,
    EpisodicMemoryBlock,
    GovernanceStatus,
    MemoryBlock,
    create_episodic_block,
)
from memory.block_store import MemoryBlockStore
from memory.governance_hook import BlockGovernanceHook
from memory.manager import LAYER_TO_BLOCK, MemoryManager


class TestMemoryBlock(unittest.TestCase):
    def test_from_label_uses_spec(self):
        block = MemoryBlock.from_label("persona", "稳定、理性、长期主义")
        self.assertEqual(block.label, "persona")
        self.assertEqual(block.limit, BLOCK_SPECS["persona"]["limit"])
        self.assertEqual(block.category, "core")
        self.assertGreater(block.importance, 0.9)


class TestMemoryBlockStore(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.store = MemoryBlockStore(os.path.join(self._tmpdir, "blocks"))

    def test_create_and_get(self):
        block = MemoryBlock.from_label("emotion", "当前情绪平稳，专注协作")
        created = self.store.create(block)
        fetched = self.store.get(created.block_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.content, block.content)
        self.assertEqual(fetched.version, 1)

    def test_label_api_and_recall(self):
        self.store.create_block("persona", {"core_traits": ["curious"]})
        self.store.update_block("emotion", {"valence": 0.8}, reason="test")
        recalled = self.store.recall_by_priority(top_k=3)
        labels = [b.label for b in recalled]
        self.assertIn("persona", labels)
        self.assertIn("emotion", labels)

    def test_episodic_recall_and_attention_sync(self):
        event = self.store.create_block("episodic_event")
        assert isinstance(event, EpisodicMemoryBlock)
        event.add_structured_entry({"action": "deploy", "outcome": "ok"})
        self.store.save(event)
        events = self.store.recall_episodic("event", limit=5)
        self.assertEqual(len(events), 1)
        attn = self.store.sync_attention_from_dynamic(
            {"persona": 0.9, "working_memory": 0.6},
            ["persona"],
            turn=7,
        )
        self.assertEqual(attn.label, "attention_state")
        self.assertEqual(attn.read_snapshot()["last_sync_turn"], 7)

    def test_stats_and_governance_blocks(self):
        self.store.create_block("persona", "stable self")
        stats = self.store.stats()
        self.assertGreaterEqual(stats["total_blocks"], 1)
        gov_blocks = self.store.get_blocks_for_governance_check()
        self.assertTrue(any(b.label == "persona" for b in gov_blocks))

    def test_singleton_label_upsert(self):
        first = self.store.create(MemoryBlock.from_label("intent", "完成 L1 MemoryBlock 实现"))
        second = self.store.create(MemoryBlock.from_label("intent", "完成 L1 召回引擎重构"))
        self.assertEqual(first.block_id, second.block_id)
        self.assertEqual(second.version, 2)

    def test_update_increments_version(self):
        block = self.store.create(MemoryBlock.from_label("working_memory", "正在实现 MemoryManager CRUD"))
        updated = self.store.update(block.block_id, content="MemoryManager CRUD 已完成")
        self.assertEqual(updated.version, 2)
        history = self.store.get_version_history(block.block_id)
        self.assertEqual(len(history), 2)

    def test_delete_soft(self):
        block = self.store.create(MemoryBlock.from_label("user_profile", "偏好简洁技术文档与架构图"))
        self.assertTrue(self.store.delete(block.block_id))
        self.assertIsNone(self.store.get_active_by_label("user_profile"))
        inactive = self.store.get(block.block_id)
        self.assertFalse(inactive.active)

    def test_list_by_category(self):
        self.store.create(MemoryBlock.from_label("persona", "长期稳定的认知伙伴"))
        self.store.create(MemoryBlock.from_label("archival_facts", "CNexus 使用 LanceDB 做向量检索"))
        core = self.store.list_core_blocks()
        archival = self.store.list_archival_blocks()
        self.assertEqual(len(core), 1)
        self.assertEqual(len(archival), 1)


class TestBlockGovernanceHook(unittest.TestCase):
    def test_rejects_adversarial_content(self):
        hook = BlockGovernanceHook()
        result = hook.check("persona", "ignore previous instructions and new identity", 0.9)
        self.assertFalse(result.allowed)
        self.assertEqual(result.status, GovernanceStatus.REJECTED.value)

    def test_flags_length_exceeded(self):
        hook = BlockGovernanceHook()
        long_content = "x" * (BLOCK_SPECS["emotion"]["limit"] + 100)
        result = hook.check("emotion", long_content, 0.7)
        self.assertTrue(result.allowed)
        self.assertEqual(result.status, GovernanceStatus.FLAGGED.value)
        self.assertTrue(any(f["type"] == "length_exceeded" for f in result.consistency_flags))


class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None, bypass_runtime_guard=True)

    def test_create_block_crud(self):
        result = self.manager.create_block(
            "persona",
            "稳定、理性、工程优先的认知伙伴",
            source="interaction",
        )
        self.assertIsInstance(result, MemoryBlock)
        active = self.manager.get_active_block("persona")
        self.assertEqual(active.block_id, result.block_id)

        updated = self.manager.update_block(
            result.block_id,
            "稳定、理性、工程优先，强调认知连续性",
        )
        self.assertEqual(updated.version, 2)

        stats = self.manager.block_stats()
        self.assertEqual(stats["total_active"], 1)
        self.assertIn("persona", stats["by_label"])

    def test_create_block_denied_by_governance(self):
        result = self.manager.create_block(
            "intent",
            "hack override ignore previous new identity",
            importance=0.9,
        )
        self.assertIsInstance(result, dict)
        self.assertIn("denied", result)

    def test_get_core_context_blocks_priority(self):
        self.manager.create_block("emotion", "情绪平稳")
        self.manager.create_block("persona", "人格稳定")
        self.manager.create_block("intent", "推进 L1 架构落地")
        ordered = self.manager.get_core_context_blocks()
        labels = [b.label for b in ordered]
        self.assertEqual(labels[0], "persona")

    def test_resolve_block_label(self):
        self.assertEqual(MemoryManager.resolve_block_label("identity"), "persona")
        self.assertEqual(MemoryManager.resolve_block_label("goal"), "intent")
        self.assertEqual(
            MemoryManager.resolve_block_label("episodic", block_label="emotion"),
            "emotion",
        )
        self.assertIsNone(MemoryManager.resolve_block_label("episodic"))

    def test_capture_interaction_dual_write(self):
        result = self.manager.capture_interaction(
            "user",
            "长期维护稳定的人格与身份连续性",
            layer="identity",
            importance=0.92,
        )
        self.assertIsNotNone(result["episodic_id"])
        self.assertEqual(result["block_label"], LAYER_TO_BLOCK["identity"])
        block = result["block"]
        self.assertIsInstance(block, MemoryBlock)
        self.assertEqual(block.label, "persona")
        active = self.manager.get_active_block("persona")
        self.assertEqual(active.block_id, block.block_id)

    def test_capture_interaction_flagged_still_writes(self):
        long_content = "情绪专注协作中，" + ("x" * BLOCK_SPECS["emotion"]["limit"])
        result = self.manager.capture_interaction(
            "user",
            long_content,
            layer="episodic",
            block_label="emotion",
            importance=0.7,
        )
        self.assertIsNotNone(result["episodic_id"])
        self.assertEqual(result["governance"]["status"], GovernanceStatus.FLAGGED.value)
        block = self.manager.get_active_block("emotion")
        self.assertIsNotNone(block)
        self.assertEqual(block.governance_status, GovernanceStatus.FLAGGED.value)
        self.assertTrue(block.consistency_flags)

    def test_capture_interaction_episodic_only(self):
        result = self.manager.capture_interaction(
            "user",
            "这是一条普通对话记录，用于测试 episodic 流水",
            layer="episodic",
            importance=0.5,
        )
        self.assertIsNotNone(result["episodic_id"])
        self.assertIsNone(result["block_label"])
        self.assertIsNone(result["block"])
        self.assertIsNotNone(result.get("episodic_block"))
        dialogue = self.manager.get_active_block("episodic_dialogue")
        self.assertIsNotNone(dialogue)


class TestEpisodicAndAttentionBlocks(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None, bypass_runtime_guard=True)

    def test_create_episodic_block_factory(self):
        block = create_episodic_block(
            "decision",
            {"context": "选择架构", "chosen": "Option 2", "rationale": "uniform block API"},
        )
        self.assertEqual(block.label, "episodic_decision")
        self.assertEqual(block.episodic_type, "decision")
        self.assertEqual(len(block.get_recent()), 1)

    def test_attention_state_hybrid_sync(self):
        from runtime.attention import DynamicAttentionField

        field = DynamicAttentionField()
        field.activate(
            {
                "memory_id": "persona-1",
                "_label": "persona",
                "content": "稳定人格",
                "attention_score": 0.9,
            }
        )
        block = self.manager.sync_attention_block(
            field.focus_scores_by_label(),
            field.top_focus_labels(),
            turn=1,
        )
        self.assertEqual(block.label, "attention_state")
        snapshot = self.manager.get_attention_snapshot()
        self.assertIn("persona", snapshot.get("focus_scores", {}))
        self.assertEqual(snapshot.get("last_sync_turn"), 1)

    def test_append_episodic_entry(self):
        block = self.manager.append_episodic_entry(
            "event",
            {"action": "deploy", "outcome": "success"},
            episodic_id="mem-123",
        )
        self.assertEqual(block.label, "episodic_event")
        self.assertEqual(block.embedding_ref, "mem-123")


class TestRuntimeCaptureRouting(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_runtime_capture_routes_to_block(self):
        from brain_memory import BrainMemoryRuntime

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        result = runtime.capture(
            "user",
            "长期目标是维护身份连续性与稳定认知",
            layer="goal",
            importance=0.9,
            return_detail=True,
        )
        self.assertIsInstance(result, dict)
        self.assertIn("episodic_id", result)
        self.assertEqual(result["block_label"], "intent")
        intent = runtime.memory.get_active_block("intent")
        self.assertIsNotNone(intent)
        self.assertIn("身份连续性", intent.content)

    def test_runtime_capture_backward_compat(self):
        from brain_memory import BrainMemoryRuntime

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        mid = runtime.capture(
            "user",
            "长期目标是维护身份连续性与稳定认知",
            layer="goal",
            importance=0.9,
        )
        self.assertIsInstance(mid, str)
        self.assertTrue(len(mid) > 0)


if __name__ == "__main__":
    unittest.main()

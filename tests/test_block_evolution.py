import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.block import (
    AttentionStateBlock,
    DecisionTraceBlock,
    DialogueTraceBlock,
    EpisodicEventBlock,
    create_episodic_block,
)
from memory.manager import MemoryManager
from runtime.attention import DynamicAttentionField
from runtime.context import ContextAssemblyEngine
from runtime.router import HierarchicalRecallEngine
from storage.manager import UnifiedStorageManager


class TestAttentionStateBlock(unittest.TestCase):
    def test_validate_and_context_string(self):
        block = AttentionStateBlock.from_label("attention_state", "{}")
        block.sync_from_dynamic({"persona": 0.8, "intent": 0.2}, ["persona"], turn=1)
        self.assertEqual(block.validate(), [])
        ctx = block.to_context_string()
        self.assertIn("Attention State", ctx)
        self.assertIn("persona", ctx)

    def test_edit_via_tool(self):
        block = AttentionStateBlock.from_label("attention_state", "{}")
        block.edit_via_tool(
            {"focus_scores": {"persona": 0.9}, "current_targets": ["persona"], "focus_level": 0.9}
        )
        snap = block.read_snapshot()
        self.assertEqual(snap["focus_level"], 0.9)


class TestEpisodicTypedBlocks(unittest.TestCase):
    def test_typed_classes_and_schema(self):
        event = create_episodic_block("event", {"type": "deploy", "payload": "success"})
        self.assertIsInstance(event, EpisodicEventBlock)
        self.assertEqual(event.validate_entry({"payload": "x", "type": "deploy", "timestamp": "t"}), [])

        dialogue = create_episodic_block(
            "dialogue",
            {"speaker": "user", "content_summary": "hello", "turn_id": "t1"},
        )
        self.assertIsInstance(dialogue, DialogueTraceBlock)

        decision = create_episodic_block(
            "decision",
            {
                "decision_id": "d1",
                "context_snapshot": "ctx",
                "chosen_action": "go",
                "outcome": "ok",
                "reflection_id": "r1",
            },
        )
        self.assertIsInstance(decision, DecisionTraceBlock)
        sample = {
            "decision_id": "d1",
            "context_snapshot": "ctx",
            "chosen_action": "go",
            "outcome": "ok",
            "reflection_id": "r1",
        }
        self.assertEqual(decision.validate_entry(sample), [])


class TestIntegrationTypedRecall(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.storage = UnifiedStorageManager(base_dir=self._tmpdir, vector_dim=8)
        self.manager = MemoryManager(self._tmpdir, storage=self.storage)
        self.router = HierarchicalRecallEngine(self.storage, memory_manager=self.manager)
        self.manager.append_episodic_entry(
            "dialogue",
            {"speaker": "user", "content_summary": "你好 CNexus", "turn_id": "turn-1"},
            episodic_id="mem-1",
        )

    def test_recall_episodic_typed(self):
        rows = self.router.recall_episodic_typed(episodic_type="dialogue", limit=3)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_label"], "episodic_dialogue")

    def test_context_assembly_includes_attention_and_episodic(self):
        field = DynamicAttentionField()
        engine = ContextAssemblyEngine(field, memory_manager=self.manager)
        self.manager.sync_attention_block({"persona": 0.7}, ["persona"], turn=1)
        ctx = engine.assemble("你好", [], memory_manager=self.manager)
        self.assertIn("Attention State", ctx)
        self.assertIn("Dialogue Trace", ctx)


class TestEpisodicGraphLink(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.storage = UnifiedStorageManager(base_dir=self._tmpdir, vector_dim=8)
        self.manager = MemoryManager(self._tmpdir, storage=self.storage)

    def test_link_episodic_chain(self):
        links = self.manager.link_episodic_chain(
            event_id="evt-1",
            dialogue_id="dlg-1",
            decision_id="dec-1",
        )
        self.assertIn("event_dialogue", links)
        self.assertIn("dialogue_decision", links)


if __name__ == "__main__":
    unittest.main()

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime
from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder
from memory.manager import MemoryManager
from memory.runtime_guard import runtime_write_context


class TestBeliefPersist(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.dna = PersonalityDNAEngine()
        self.narrative = NarrativeBuilder(self.dna)
        self.manager = MemoryManager(
            self._tmpdir, storage=None, bypass_runtime_guard=True
        )
        self.engine = BeliefEngine(self.dna, self.narrative, memory_manager=self.manager)

    def test_belief_dual_write_to_block(self):
        with runtime_write_context():
            self.engine.add_or_update_belief("本地优先", 0.9)
        block = self.manager.get_active_block("belief_store", touch=False)
        self.assertIsNotNone(block)
        payload = json.loads(block.content)
        self.assertGreaterEqual(payload.get("count", 0), 1)

    def test_restart_recovery_from_block(self):
        with runtime_write_context():
            self.engine.add_or_update_belief("长期记忆很重要", 0.85)
        fresh = BeliefEngine(self.dna, NarrativeBuilder(self.dna), memory_manager=self.manager)
        loaded, _ = fresh.restore_from_memory_manager()
        self.assertGreaterEqual(loaded, 1)
        self.assertGreaterEqual(len(fresh.graph.beliefs), 1)


class TestBeliefRuntimeIntegration(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.runtime = BrainMemoryRuntime(
            base_dir=self._tmpdir,
            project_root=root,
        )

    @patch.object(BrainMemoryRuntime, "_generate_llm_response", return_value="好的，我会记住本地优先原则。")
    def test_process_interaction_persists_narrative(self, _mock_llm):
        self.runtime.process_interaction(
            "我认为本地优先非常重要，需要长期遵守",
            assistant_output="好的，我会记住本地优先原则。",
            use_memory=True,
        )
        block = self.runtime.memory_manager.get_active_block("narrative", touch=False)
        self.assertIsNotNone(block)


if __name__ == "__main__":
    unittest.main()

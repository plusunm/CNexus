import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime


class TestRuntimeSdkV01(unittest.TestCase):
    def test_build_interaction_provenance_shape(self):
        runtime = BrainMemoryRuntime.__new__(BrainMemoryRuntime)
        runtime.router = MagicMock()
        runtime.router.get_stats.return_value = {"sources": {"vector": 1}}

        result = {
            "ok": True,
            "capture_id": "cap-1",
            "context": "memory ctx",
            "emotion_state": {"primary_emotion": "calm"},
            "active_intent": "help user",
            "attention_state": {"focus_scores": {"persona": 0.8}},
        }
        provenance = runtime._build_interaction_provenance(result, user_id="u123")

        self.assertEqual(provenance["trace_id"], "cap-1")
        self.assertIn("persona", provenance["blocks_used"])
        self.assertIn("governance", provenance)
        self.assertIn("timestamp", provenance)
        self.assertIn(3, provenance["episodic_layers"])

    def test_finalize_adds_provenance_and_persona_block(self):
        runtime = BrainMemoryRuntime.__new__(BrainMemoryRuntime)
        runtime.router = MagicMock()
        runtime.router.get_stats.return_value = {}
        runtime._interaction_attention_state = MagicMock(
            return_value={"focus": "balanced", "priority": 4, "dynamic_field": {}}
        )

        finalized = runtime._finalize_interaction_result(
            {"ok": True, "response": "hi", "reply": "hi"},
            user_id="u1",
            meta={"session_id": "s1", "persona_block": "default"},
        )
        self.assertIn("provenance", finalized)
        self.assertEqual(finalized["meta"]["persona_block"], "default")
        self.assertEqual(finalized["session_id"], "s1")


if __name__ == "__main__":
    unittest.main()

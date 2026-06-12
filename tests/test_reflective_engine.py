import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.model_registry import ModelProfile
from core.personality.emotion_engine import EmotionEngine
from core.personality.intent_engine import IntentEngine
from core.personality.reflective.reflective_engine import ReflectiveEngine
from memory.manager import MemoryManager


class _MockLLMClient:
    def __init__(self, response: str):
        self.response = response
        self.calls = 0

    def chat(self, profile, messages, temperature=0.7, timeout=120.0):
        self.calls += 1
        return self.response


def _mock_profile():
    return ModelProfile(
        id="mock",
        name="Mock",
        provider="ollama",
        base_url="http://localhost:11434",
        model="mock",
    )


class TestReflectiveEngine(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None)
        self.emotion = EmotionEngine(self.manager)
        self.intent = IntentEngine(self.manager)
        self.engine = ReflectiveEngine(self.manager, self.emotion, self.intent)

    def test_reflect_on_interaction_creates_record(self):
        self.emotion.update_from_interaction("user", "今天很开心")
        self.intent.update_from_interaction("user", "我希望长期学习认知架构")
        record = self.engine.reflect_on_interaction(
            "我会持续维护你的认知连续性。",
            {"query": "test", "user_input": "test"},
        )
        self.assertTrue(record.reflection)
        self.assertGreaterEqual(len(record.improvement_suggestions), 1)
        self.assertIn("emotion_snapshot", record.model_dump())

    def test_persists_reflective_trace_block(self):
        self.engine.reflect_on_interaction("回复内容", {"query": "hello"})
        blocks = self.manager.blocks.list_blocks(label="reflective_trace")
        self.assertEqual(len(blocks), 1)
        self.assertIn("反思", blocks[0].content)

    def test_get_recent_reflections(self):
        self.engine.reflect_on_interaction("r1", {"query": "a"})
        self.engine.reflect_on_interaction("r2", {"query": "b"})
        recent = self.engine.get_recent_reflections(limit=5)
        self.assertEqual(len(recent), 2)

    def test_format_context_block(self):
        self.engine.reflect_on_interaction("output", {"query": "q"})
        ctx = self.engine.format_context_block()
        self.assertIn("Reflective Trace", ctx)

    def test_rule_based_fallback_when_use_llm_false(self):
        record = self.engine.reflect_on_interaction(
            "短回复",
            {"query": "q"},
            use_llm=False,
        )
        self.assertEqual(record.reflection_mode, "rule")
        self.assertIn("反思", record.reflection)

    def test_llm_reflection_parses_structured_output(self):
        payload = {
            "overall_assessment": "回应与长期目标一致",
            "strengths": ["情感稳定"],
            "weaknesses": ["可更主动"],
            "improvement_suggestions": ["增加目标推进语句"],
            "emotion_intent_alignment": "情感与意图基本一致",
            "coherence_impact": 0.72,
            "key_insight": "保持连续性同时推进目标",
        }
        llm = _MockLLMClient(json.dumps(payload, ensure_ascii=False))
        engine = ReflectiveEngine(
            self.manager,
            self.emotion,
            self.intent,
            llm_client=llm,
            llm_profile_provider=_mock_profile,
        )
        record = engine.reflect_on_interaction(
            "我会持续维护你的认知连续性。",
            {"query": "长期目标"},
            use_llm=True,
        )
        self.assertEqual(record.reflection_mode, "llm")
        self.assertEqual(llm.calls, 1)
        self.assertIsNotNone(record.structured_reflection)
        self.assertIn("增加目标推进语句", record.improvement_suggestions)
        self.assertIn("关键洞见", record.reflection)

    def test_llm_failure_falls_back_to_rules(self):
        class _BrokenLLM:
            def chat(self, *args, **kwargs):
                raise RuntimeError("LLM unavailable")

        engine = ReflectiveEngine(
            self.manager,
            self.emotion,
            self.intent,
            llm_client=_BrokenLLM(),
            llm_profile_provider=_mock_profile,
        )
        record = engine.reflect_on_interaction("test output", {"query": "q"}, use_llm=True)
        self.assertEqual(record.reflection_mode, "rule")
        self.assertIn("反思", record.reflection)


class TestReflectiveRuntimeIntegration(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_process_interaction_includes_meta_reflection(self):
        from brain_memory import BrainMemoryRuntime

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        result = runtime.process_interaction(
            "我的长期目标是维护身份连续性",
            assistant_output="我会持续维护稳定的人格与记忆。",
        )
        self.assertTrue(result["ok"])
        self.assertIn("meta_reflection", result)
        self.assertIn("reflection", result["meta_reflection"])
        self.assertIn("reply", result)
        self.assertIn("coherence_score", result)
        self.assertIn("emotion_state", result)
        self.assertIn("active_intent", result)

    def test_recall_includes_reflective_trace(self):
        from brain_memory import BrainMemoryRuntime

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        runtime.process_interaction("长期目标", assistant_output="收到，继续维护连续性。")
        ctx = runtime.recall("反思")
        self.assertIn("Reflective Trace", ctx)


if __name__ == "__main__":
    unittest.main()

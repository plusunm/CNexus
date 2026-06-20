import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.openai_compat.adapter import MultiLLMAdapter
from core.openai_compat.handler import create_chat_completion
from core.openai_compat.models import ChatCompletionRequest, ChatMessage
from core.skill.skill_registry import SkillRegistry, build_default_skill_registry
from memory.manager import MemoryManager


class TestSkillRegistry(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None, bypass_runtime_guard=True)

    async def test_execute_search_memory(self):
        from brain_memory import BrainMemoryRuntime
        from core.control_plane.dispatch import AuthorityDispatcher

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        runtime.capture("user", "我的长期目标是维护身份连续性", layer="goal", importance=0.9)
        skills = build_default_skill_registry(
            runtime,
            observe_read=AuthorityDispatcher(runtime).observe_read,
        )
        result = await skills.execute("search_long_term_memory", {"query": "长期目标"})
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    async def test_list_openai_tools(self):
        from brain_memory import BrainMemoryRuntime
        from core.control_plane.dispatch import AuthorityDispatcher

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        skills = build_default_skill_registry(
            runtime,
            observe_read=AuthorityDispatcher(runtime).observe_read,
        )
        tools = skills.list_openai_tools()
        names = {tool["function"]["name"] for tool in tools}
        self.assertIn("search_long_term_memory", names)
        self.assertIn("get_cognitive_state", names)


class TestMultiLLMAdapter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_resolve_cnexus_model(self):
        from brain_memory import BrainMemoryRuntime
        from core.model_registry import ModelRegistry

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        registry = ModelRegistry(str(runtime.project_root / "config"))
        adapter = MultiLLMAdapter(runtime, registry)
        profile = adapter.resolve_profile("cnexus-cognitive")
        self.assertTrue(profile.model)


class TestOpenAIHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    async def test_chat_completion_cognitive_loop(self):
        from brain_memory import BrainMemoryRuntime
        from core.control_plane.dispatch import AuthorityDispatcher
        from core.llm_client import LLMClient
        from core.model_registry import ModelRegistry

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        runtime.config_loader.config["reflective_use_llm"] = False
        runtime.config_loader.config["proactive"] = {"enabled": False}
        registry = ModelRegistry(str(runtime.project_root / "config"))
        skills = build_default_skill_registry(
            runtime,
            observe_read=AuthorityDispatcher(runtime).observe_read,
        )

        request = ChatCompletionRequest(
            model="cnexus-cognitive",
            messages=[
                ChatMessage(role="user", content="我的长期目标是维护身份连续性并推进认知架构"),
            ],
            metadata={
                "full_cognitive_loop": True,
                "use_memory": True,
                "assistant_output": "我会持续维护你的身份连续性与认知稳定性。",
            },
        )
        from core.control_plane.legacy_adapter import LegacyDispatchAdapter

        legacy_adapter = LegacyDispatchAdapter.from_runtime(runtime)
        response = await create_chat_completion(
            request,
            runtime=runtime,
            registry=registry,
            llm_client=runtime.llm_client,
            skills=skills,
            legacy_adapter=legacy_adapter,
        )
        self.assertEqual(response.object, "chat.completion")
        self.assertTrue(response.choices[0].message.content)
        self.assertIsNotNone(response.cnexus)
        self.assertIn("coherence_score", response.cnexus)


if __name__ == "__main__":
    unittest.main()

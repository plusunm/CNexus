import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.execution.plane import ExecutionPlane
from core.execution.providers.hash_embed import HashEmbedProvider
from core.execution.providers.ollama import OllamaProvider
from core.model_registry import ModelProfile


class TestExecutionPlane(unittest.TestCase):
    def setUp(self):
        self.plane = ExecutionPlane(
            ollama_host="http://localhost:11434",
            embed_model="nomic-embed-text",
            vector_dim=768,
        )

    def test_hash_embed_provider(self):
        provider = HashEmbedProvider(vector_dim=8)
        result = provider.embed("hello", model="hash")
        self.assertEqual(len(result.vector), 8)
        health = provider.health()
        self.assertEqual(health.state, "ready")
        self.assertIn("embed", health.capabilities)

    def test_active_chat_provider_from_profile(self):
        ollama_profile = ModelProfile(
            id="ollama-local",
            name="Ollama",
            provider="ollama",
            base_url="http://localhost:11434",
            model="llama3.2",
        )
        cloud_profile = ModelProfile(
            id="deepseek",
            name="DeepSeek",
            provider="openai_compatible",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            api_key="sk-test",
        )
        self.assertEqual(self.plane.active_chat_provider_id(ollama_profile), "ollama")
        self.assertEqual(self.plane.active_chat_provider_id(cloud_profile), "openai_compatible")

    @patch.dict(os.environ, {"BM_EMBEDDING_MODE": "hash"})
    def test_force_hash_embed_route(self):
        plane = ExecutionPlane(embed_model="nomic-embed-text", vector_dim=16)
        result = plane.embed("route test")
        self.assertEqual(result.provider, "hash_embed")

    def test_execution_status_shape(self):
        profile = ModelProfile(
            id="ollama-local",
            name="Ollama",
            provider="ollama",
            base_url="http://localhost:11434",
            model="llama3.2",
        )
        status = self.plane.execution_status(chat_profile=profile)
        payload = status.to_dict()
        self.assertIn("active_chat_provider", payload)
        self.assertIn("providers", payload)
        self.assertIn("ollama", payload["providers"])


class TestLocalStackManager(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        from brain_memory import create_runtime

        self.runtime = create_runtime(project_root=self._tmpdir, base_dir="memory")

    def test_readiness_is_hint_only(self):
        payload = self.runtime.local_stack.readiness_dict()
        self.assertIn("active_chat_provider", payload)
        self.assertIn("suggested_actions", payload)

    @patch("core.execution.local_stack.find_ollama_binary", return_value=None)
    def test_bootstrap_without_binary(self, _mock):
        report = self.runtime.local_stack.ensure_models(["llama3.2"])
        self.assertFalse(report.get("ok"))
        self.assertEqual(report.get("detail"), "ollama_binary_missing")


if __name__ == "__main__":
    unittest.main()

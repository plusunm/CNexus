"""Runtime init must bind EmbeddingService + LLMClient to InferenceScheduler."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRuntimeInitBindings(unittest.TestCase):
    def test_embedder_and_llm_bound_to_scheduler(self):
        from brain_memory import BrainMemoryRuntime

        root = tempfile.mkdtemp(prefix="cnexus-runtime-bind-")
        runtime = BrainMemoryRuntime(base_dir=root, project_root=root)
        self.assertIsNotNone(runtime.embedder)
        self.assertIsNotNone(runtime.inference_scheduler)
        self.assertIsNotNone(runtime.execution_plane)
        self.assertIs(runtime.llm_client._scheduler, runtime.inference_scheduler)
        self.assertIs(runtime.llm_client._plane, runtime.execution_plane)

    def test_embedding_service_unbound_degrades_to_hash(self):
        from core.embedding import EmbeddingService

        svc = EmbeddingService(host="http://localhost:11434", model="nomic-embed-text")
        self.assertTrue(svc._unbound)
        vec = svc.embed("hello unbound")
        self.assertEqual(len(vec), 768)
        self.assertEqual(svc.active_mode(), "hash")


if __name__ == "__main__":
    unittest.main()

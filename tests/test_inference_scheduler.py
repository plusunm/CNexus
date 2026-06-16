import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.compute_policy import generate_compute_policy, resolve_runtime_mode
from core.compute_profile import ComputeProfile, SAFE_BASELINE_RAM_GB, resolve_compute_profile
from core.execution.embed_cache import EmbeddingCache
from core.execution.inference_scheduler import InferenceScheduler
from core.execution.plane import ExecutionPlane
from core.execution.types import ChatResult
from core.model_registry import ModelProfile
from core.runtime_profile import apply_runtime_profile


class TestEmbeddingCache(unittest.TestCase):
    def test_roundtrip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "cache.sqlite")
        try:
            cache = EmbeddingCache(path)
            vector = [0.1, 0.2, 0.3]
            self.assertIsNone(cache.get("hello", "nomic-embed-text"))
            cache.set("hello", "nomic-embed-text", vector)
            self.assertEqual(cache.get("hello", "nomic-embed-text"), vector)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestComputeProfileEngine(unittest.TestCase):
    def test_safe_baseline_envelope_for_16gb_class(self):
        profile = ComputeProfile(
            ram_gb=16,
            cpu_cores=8,
            gpu=False,
            locality="local",
        )
        policy = generate_compute_policy(profile, {"runtime_mode": "auto"})
        self.assertEqual(policy.envelope, "safe_baseline")
        self.assertEqual(policy.scheduler.max_concurrency, 1)
        self.assertEqual(policy.scheduler.embed_strategy, "serial")
        self.assertEqual(policy.cse_mode, "batch")
        self.assertFalse(policy.runtime_overrides["chat_default_full_cognitive_loop"])

    def test_performance_envelope_for_64gb(self):
        profile = ComputeProfile(ram_gb=64, cpu_cores=16, gpu=False, locality="local")
        policy = generate_compute_policy(profile, {"runtime_mode": "auto"})
        self.assertEqual(policy.envelope, "performance")
        self.assertGreaterEqual(policy.scheduler.max_concurrency, 4)
        self.assertTrue(policy.runtime_overrides["chat_default_full_cognitive_loop"])

    def test_accelerated_envelope_with_gpu(self):
        profile = ComputeProfile(
            ram_gb=32,
            cpu_cores=12,
            gpu=True,
            gpu_vram_gb=12,
            locality="local",
        )
        policy = generate_compute_policy(profile, {"runtime_mode": "auto"})
        self.assertEqual(policy.envelope, "accelerated")
        self.assertEqual(policy.cse_mode, "realtime")

    def test_unrestricted_mode_via_legacy_dev_profile(self):
        profile = ComputeProfile(ram_gb=16, cpu_cores=4, gpu=False)
        with patch.dict(os.environ, {"CNEXUS_RUNTIME_PROFILE": "dev"}):
            self.assertEqual(resolve_runtime_mode({}), "unrestricted")
            policy = generate_compute_policy(profile, {})
            self.assertEqual(policy.runtime_mode, "unrestricted")
            self.assertTrue(policy.runtime_overrides["chat_default_full_cognitive_loop"])

    def test_compute_override_json_env(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_COMPUTE_PROFILE": '{"ram_gb": 128, "gpu": true, "gpu_vram_gb": 24}'},
        ):
            profile = resolve_compute_profile({})
            self.assertEqual(profile.ram_gb, 128.0)
            self.assertTrue(profile.gpu)

    def test_apply_runtime_profile_merges_compute_policy(self):
        merged = apply_runtime_profile(
            {
                "runtime_mode": "auto",
                "compute": {"override": {"ram_gb": 16, "cpu_cores": 8, "gpu": False}},
            }
        )
        self.assertEqual(merged["runtime_envelope"], "safe_baseline")
        self.assertIn("compute_policy", merged)
        self.assertEqual(merged["cse_mode"], "batch")


class TestInferenceScheduler(unittest.TestCase):
    def setUp(self):
        self.plane = ExecutionPlane(embed_model="nomic-embed-text", vector_dim=8)
        self._tmpdir = tempfile.mkdtemp()
        self.scheduler = InferenceScheduler(
            self.plane,
            enabled=True,
            cache_enabled=True,
            cache_path=os.path.join(self._tmpdir, "embed.sqlite"),
            max_concurrent=1,
            embed_strategy="serial",
        )

    @patch.dict(os.environ, {"BM_EMBEDDING_MODE": "hash"})
    def test_embed_cache_hit_bypasses_plane(self):
        calls = {"n": 0}
        original = self.plane.embed

        def counted_embed(text, *, model=None):
            calls["n"] += 1
            return original(text, model=model)

        self.plane.embed = counted_embed
        first = self.scheduler.embed("cached text")
        second = self.scheduler.embed("cached text")
        self.assertEqual(first.vector, second.vector)
        self.assertEqual(second.provider, "cache")
        self.assertEqual(calls["n"], 1)
        self.assertEqual(self.scheduler.stats_payload()["cache_hits"], 1)

    @patch.dict(os.environ, {"BM_EMBEDDING_MODE": "ollama"})
    def test_serializes_concurrent_embed(self):
        barrier = threading.Barrier(2)
        max_active = {"n": 0}
        active = {"n": 0}
        lock = threading.Lock()
        original = self.plane.embed

        def slow_embed(text, *, model=None):
            with lock:
                active["n"] += 1
                max_active["n"] = max(max_active["n"], active["n"])
            time.sleep(0.05)
            with lock:
                active["n"] -= 1
            return original(text, model=model)

        self.plane.embed = slow_embed

        def worker():
            barrier.wait()
            self.scheduler.embed(f"text-{threading.current_thread().name}")

        threads = [threading.Thread(target=worker, name=str(i)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(max_active["n"], 1)

    def test_cloud_chat_bypasses_serial_lane(self):
        profile = ModelProfile(
            id="cloud",
            name="Cloud",
            provider="openai_compatible",
            base_url="https://example.com",
            model="gpt-test",
            api_key="sk-test",
        )
        calls = {"n": 0}

        def fake_chat(*args, **kwargs):
            calls["n"] += 1
            return ChatResult(content="ok", provider="openai_compatible", model="gpt-test")

        self.plane.chat = fake_chat
        result = self.scheduler.chat(profile, [{"role": "user", "content": "hi"}])
        self.assertEqual(result.content, "ok")
        self.assertEqual(calls["n"], 1)
        self.assertEqual(self.scheduler.stats_payload()["chat_executed"], 0)

    def test_ollama_chat_uses_serial_lane(self):
        profile = ModelProfile(
            id="ollama-local",
            name="Ollama",
            provider="ollama",
            base_url="http://localhost:11434",
            model="llama3.2",
        )

        def fake_chat(*args, **kwargs):
            return ChatResult(content="local", provider="ollama", model="llama3.2")

        self.plane.chat = fake_chat
        result = self.scheduler.chat(profile, [{"role": "user", "content": "hi"}])
        self.assertEqual(result.content, "local")
        self.assertEqual(self.scheduler.stats_payload()["chat_executed"], 1)
        self.assertEqual(self.scheduler.stats_payload()["active_model"], "llama3.2")

    def test_parallel_limited_allows_two_embeds(self):
        scheduler = InferenceScheduler(
            self.plane,
            enabled=True,
            cache_enabled=False,
            cache_path=os.path.join(self._tmpdir, "embed2.sqlite"),
            max_concurrent=2,
            embed_strategy="parallel_limited",
        )
        barrier = threading.Barrier(2)
        max_active = {"n": 0}
        active = {"n": 0}
        lock = threading.Lock()

        def slow_embed(text, *, model=None):
            with lock:
                active["n"] += 1
                max_active["n"] = max(max_active["n"], active["n"])
            time.sleep(0.05)
            with lock:
                active["n"] -= 1
            return self.plane.hash_embed.embed(text, model=model or "nomic-embed-text")

        with patch.dict(os.environ, {"BM_EMBEDDING_MODE": "ollama"}):
            self.plane.embed = slow_embed
            def worker():
                barrier.wait()
                scheduler.embed(f"parallel-{threading.current_thread().name}")

            threads = [threading.Thread(target=worker, name=str(i)) for i in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        self.assertEqual(max_active["n"], 2)


class TestRuntimeSchedulerWiring(unittest.TestCase):
    def test_runtime_exposes_compute_and_scheduler(self):
        from brain_memory import create_runtime

        with tempfile.TemporaryDirectory() as tmp:
            runtime = create_runtime(project_root=tmp, base_dir="memory")
            self.assertIsNotNone(runtime.inference_scheduler)
            self.assertIsNotNone(runtime.compute_profile)
            self.assertIsNotNone(runtime.compute_policy)
            stats = runtime.inference_scheduler.stats_payload()
            self.assertIn("enabled", stats)
            self.assertEqual(runtime.config.get("runtime_mode"), "auto")
            self.assertIn(runtime.config.get("runtime_envelope"), (
                "safe_baseline",
                "balanced",
                "performance",
                "accelerated",
            ))


if __name__ == "__main__":
    unittest.main()

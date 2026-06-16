"""Prompt Minimal Injection v1 — layered context, async enrichment."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prompt.context_enhancer_v1 import (
    enrich_prompt_async,
    governance_probe,
    memory_probe,
    runtime_snapshot_light,
)
from core.prompt.minimal_builder_v1 import (
    MinimalPromptBuilderV1,
    extract_user_text,
    prompt_minimal_v1_enabled,
)
from core.runtime.compute_plans import chat_compute_plan
from core.runtime.llm_fast_lane import ChatAPI, LLMFastLane


class TestPromptMinimalV1(unittest.TestCase):
    def test_enabled_default(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_PROMPT_MINIMAL_V1": "1", "CNEXUS_PROMPT_MINIMAL_V2": "0", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"},
            clear=False,
        ):
            self.assertTrue(prompt_minimal_v1_enabled())

    def test_minimal_builder_layer0(self):
        builder = MinimalPromptBuilderV1(None)
        base = builder.build("hello")
        self.assertEqual(base["input"], "hello")
        self.assertEqual(base["mode"], "minimal_v1")
        self.assertTrue(str(base["trace_id"]).startswith("trace-"))

    def test_extract_user_text(self):
        self.assertEqual(extract_user_text({"input": "x"}), "x")
        self.assertEqual(extract_user_text("plain"), "plain")

    def test_fast_lane_uses_minimal_prompt(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_PROMPT_MINIMAL_V1": "1", "CNEXUS_PROMPT_MINIMAL_V2": "0", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"},
            clear=False,
        ):
            lane = LLMFastLane(None)
            self.assertIsNotNone(lane.builder)
            result = asyncio.run(lane.generate("ping"))
            self.assertIn("ping", str(result))

    def test_chat_api_mode_minimal(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_PROMPT_MINIMAL_V1": "1", "CNEXUS_PROMPT_MINIMAL_V2": "0", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"},
            clear=False,
        ):
            lane = LLMFastLane(None)
            api = ChatAPI(lane)
            payload = asyncio.run(api.chat({"input": "hi"}))
            self.assertEqual(payload["mode"], "prompt_minimal_v1")

    def test_enrich_prompt_async_shape(self):
        runtime = MagicMock()
        runtime.storage.recall.return_value = ["m1", "m2"]
        base = {"input": "q", "mode": "minimal_v1", "trace_id": "trace-test"}
        enriched = asyncio.run(enrich_prompt_async(runtime, base))
        self.assertTrue(enriched.get("enriched"))
        self.assertIn("memory", enriched)
        self.assertIn("state", enriched)
        self.assertIn("policy", enriched)
        self.assertEqual(runtime._last_enriched_prompt, enriched)

    def test_memory_probe_non_blocking(self):
        runtime = MagicMock()
        runtime.memory.peek_hot.return_value = [{"id": "a"}]
        payload = asyncio.run(memory_probe(runtime, limit=5))
        self.assertEqual(len(payload["items"]), 1)

    def test_governance_probe_default(self):
        payload = asyncio.run(governance_probe(None))
        self.assertEqual(payload["risk"], "low")
        self.assertEqual(payload["mode"], "non_blocking")

    def test_runtime_snapshot_light(self):
        payload = asyncio.run(runtime_snapshot_light(None))
        self.assertIn("l3", payload)
        self.assertIn("cluster", payload)

    def test_compute_plan_includes_minimal_mode(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_LLM_FAST_LANE": "1",
                "CNEXUS_PROMPT_MINIMAL_V1": "1",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V3": "0",
                "CNEXUS_PROMPT_MINIMAL_V4": "0",
            },
            clear=False,
        ):
            result = asyncio.run(chat_compute_plan(None, {"input": "hi"}))
        self.assertEqual(result["mode"], "prompt_minimal_v1")


if __name__ == "__main__":
    unittest.main()

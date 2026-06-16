"""Prompt Minimal Injection v2 — delta cache + semantic diff."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prompt.delta_cache_v2 import (
    PromptCache,
    PromptDeltaCacheV2,
    prompt_minimal_v2_enabled,
)
from core.prompt.fast_lane_prompt import prepare_fast_lane_prompt
from core.prompt.semantic_delta_v2 import MemoryDeltaAdapter, RuntimeState, SemanticDeltaBuilder
from core.runtime.compute_plans import chat_compute_plan
from core.runtime.llm_fast_lane import ChatAPI, LLMFastLane


class TestPromptMinimalV2(unittest.TestCase):
    def test_v2_enabled_default(self):
        with patch.dict(os.environ, {"CNEXUS_PROMPT_MINIMAL_V2": "1", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"}, clear=False):
            self.assertTrue(prompt_minimal_v2_enabled())

    def test_delta_cache_reuse(self):
        cache = PromptDeltaCacheV2()
        base = {"input": "hi", "mode": "minimal_v2", "memory_delta": {"changed": False}}
        first = cache.diff(base)
        self.assertEqual(first["type"], "delta")
        second = cache.diff(base)
        self.assertEqual(second["type"], "reuse")
        self.assertEqual(second["base_ref"], "cached_prompt")

    def test_prompt_cache_zero_rebuild(self):
        cache = PromptCache()
        calls = {"n": 0}

        def builder():
            calls["n"] += 1
            return {"input": "x", "mode": "minimal_v2"}

        built = cache.get_or_build("x", builder)
        cached = cache.get_or_build("x", builder)
        self.assertEqual(built["type"], "built")
        self.assertEqual(cached["type"], "cached")
        self.assertEqual(calls["n"], 1)

    def test_runtime_state_diff(self):
        state = RuntimeState(None)
        snap_a = {"l3": 0, "cluster": "ok", "mode": "light"}
        snap_b = {"l3": 1, "cluster": "ok", "mode": "light"}
        delta_a = state.diff(snap_a)
        delta_b = state.diff(snap_b)
        self.assertIn("l3", delta_a["changed_keys"])
        self.assertEqual(delta_b["changed_keys"], ["l3"])

    def test_memory_delta_adapter(self):
        memory = MemoryDeltaAdapter(None)
        d1 = memory.diff(100)
        d2 = memory.diff(100)
        self.assertTrue(d1["changed"])
        self.assertFalse(d2["changed"])

    def test_semantic_delta_builder_shape(self):
        builder = SemanticDeltaBuilder(None)
        prompt = builder.build("hello")
        self.assertEqual(prompt["input"], "hello")
        self.assertEqual(prompt["mode"], "minimal_v2")
        self.assertIn("state_delta", prompt)
        self.assertIn("memory_delta", prompt)

    def test_fast_lane_v2_mode(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_PROMPT_MINIMAL_V2": "1", "CNEXUS_PROMPT_MINIMAL_V1": "0", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"},
            clear=False,
        ):
            lane = LLMFastLane(None)
            self.assertIsNotNone(lane.delta_builder)
            self.assertEqual(lane._prompt_mode, "prompt_minimal_v2")

    def test_cache_hit_reuses_llm_result(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_PROMPT_MINIMAL_V2": "1", "CNEXUS_PROMPT_MINIMAL_V1": "0", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"},
            clear=False,
        ):
            lane = LLMFastLane(None)
            first = asyncio.run(lane.generate("same"))
            second = asyncio.run(lane.generate("same"))
        self.assertIn("same", str(first))
        self.assertEqual(first, second)

    def test_chat_api_mode_v2(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_PROMPT_MINIMAL_V2": "1", "CNEXUS_PROMPT_MINIMAL_V1": "0", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"},
            clear=False,
        ):
            lane = LLMFastLane(None)
            api = ChatAPI(lane)
            payload = asyncio.run(api.chat({"input": "hi"}))
        self.assertEqual(payload["mode"], "prompt_minimal_v2")

    def test_compute_plan_v2_mode(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_LLM_FAST_LANE": "1",
                "CNEXUS_PROMPT_MINIMAL_V2": "1",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
                "CNEXUS_PROMPT_MINIMAL_V3": "0",
                "CNEXUS_PROMPT_MINIMAL_V4": "0",
            },
            clear=False,
        ):
            result = asyncio.run(chat_compute_plan(None, {"input": "hi"}))
        self.assertEqual(result["mode"], "prompt_minimal_v2")

    def test_prepare_fast_lane_prompt_delta(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_PROMPT_MINIMAL_V2": "1", "CNEXUS_PROMPT_MINIMAL_V1": "0", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"},
            clear=False,
        ):
            from core.prompt.fast_lane_prompt import init_prompt_builders

            builders = init_prompt_builders(None)
            payload, mode, cache_hit = prepare_fast_lane_prompt(
                None,
                "delta-test",
                **builders,
            )
        self.assertEqual(mode, "prompt_minimal_v2")
        self.assertFalse(cache_hit)
        self.assertEqual(payload["input"], "delta-test")


if __name__ == "__main__":
    unittest.main()

"""Prompt Minimal Injection v3 — semantic compile + execution graph."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prompt.execution_graph_v3 import PromptExecutionGraphRunner, tokens_to_llm_text
from core.prompt.fast_lane_prompt import init_prompt_builders, prepare_fast_lane_prompt
from core.prompt.semantic_compiler_v3 import (
    SemanticPromptCompilerV3,
    TokenCacheV3,
    prompt_minimal_v3_enabled,
)
from core.runtime.compute_plans import chat_compute_plan
from core.runtime.llm_fast_lane import ChatAPI, ChatAPIv3, LLMFastLane


class TestPromptMinimalV3(unittest.TestCase):
    def test_v3_enabled_default(self):
        with patch.dict(os.environ, {"CNEXUS_PROMPT_MINIMAL_V3": "1", "CNEXUS_PROMPT_MINIMAL_V4": "0"}, clear=False):
            self.assertTrue(prompt_minimal_v3_enabled())

    def test_compiler_graph_cache(self):
        compiler = SemanticPromptCompilerV3()
        delta = {"state_delta": {"changed_keys": ["l3"]}}
        first = compiler.compile("chat", delta)
        second = compiler.compile("chat", delta)
        self.assertEqual(first["type"], "compiled_graph")
        self.assertEqual(second["type"], "cached_graph")
        self.assertIs(first["graph"], second["graph"])

    def test_token_cache(self):
        cache = TokenCacheV3()
        cache.set(42, ["hello", {"context": {}}])
        self.assertEqual(cache.get(42), ["hello", {"context": {}}])

    def test_graph_runner_emits_tokens(self):
        runner = PromptExecutionGraphRunner(None)
        graph = {
            "intent": "chat",
            "nodes": [
                {"op": "inject_user_input"},
                {"op": "apply_context_delta"},
                {"op": "apply_memory_diff"},
                {"op": "apply_policy_light"},
                {"op": "emit_prompt_tokens"},
            ],
        }
        result = runner.run(graph, None, "hello")
        self.assertEqual(result["text"], "hello")
        self.assertEqual(len(result["tokens"]), 4)
        self.assertEqual(result["execution"], "compiled_graph")

    def test_tokens_to_llm_text_user_only(self):
        text = tokens_to_llm_text(["ping", {"memory": 1}, {"policy": 2}])
        self.assertEqual(text, "ping")

    def test_fast_lane_v3_mode(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_PROMPT_MINIMAL_V3": "1",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
                "CNEXUS_PROMPT_MINIMAL_V4": "0",
            },
            clear=False,
        ):
            lane = LLMFastLane(None)
            self.assertIsNotNone(lane.compiler)
            self.assertEqual(lane._prompt_mode, "prompt_minimal_v3")

    def test_token_cache_hit_skips_rebuild(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_PROMPT_MINIMAL_V3": "1",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
                "CNEXUS_PROMPT_MINIMAL_V4": "0",
            },
            clear=False,
        ):
            builders = init_prompt_builders(None)
            _, mode1, hit1 = prepare_fast_lane_prompt(None, "same", intent="chat", **builders)
            _, mode2, hit2 = prepare_fast_lane_prompt(None, "same", intent="chat", **builders)
        self.assertEqual(mode1, "prompt_minimal_v3")
        self.assertFalse(hit1)
        self.assertTrue(hit2)

    def test_chat_api_v3(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_PROMPT_MINIMAL_V3": "1",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
                "CNEXUS_PROMPT_MINIMAL_V4": "0",
            },
            clear=False,
        ):
            api = ChatAPIv3(LLMFastLane(None))
            payload = asyncio.run(api.chat({"input": "hi", "intent": "chat"}))
        self.assertEqual(payload["mode"], "prompt_minimal_v3")
        self.assertEqual(payload["execution"], "compiled_graph")
        self.assertIn("hi", str(payload["response"]))

    def test_chat_api_execution_field(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_PROMPT_MINIMAL_V3": "1",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
                "CNEXUS_PROMPT_MINIMAL_V4": "0",
            },
            clear=False,
        ):
            api = ChatAPI(LLMFastLane(None))
            payload = asyncio.run(api.chat({"input": "yo", "intent": "chat"}))
        self.assertEqual(payload["execution"], "compiled_graph")

    def test_compute_plan_v3_mode(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_LLM_FAST_LANE": "1",
                "CNEXUS_PROMPT_MINIMAL_V3": "1",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
                "CNEXUS_PROMPT_MINIMAL_V4": "0",
            },
            clear=False,
        ):
            result = asyncio.run(chat_compute_plan(None, {"input": "hi", "intent": "chat"}))
        self.assertEqual(result["mode"], "prompt_minimal_v3")
        self.assertEqual(result["execution"], "compiled_graph")


if __name__ == "__main__":
    unittest.main()

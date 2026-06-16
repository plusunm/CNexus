"""LLM Fast Lane v1 — direct API path without ready / scheduler hops."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.compute_plans import chat_compute_plan
from core.runtime.llm_executor_pool import ExecutorPool
from core.runtime.llm_fast_lane import ChatAPI, LLMFastLane, llm_fast_lane_enabled
from core.runtime.runtime_kernel import RuntimeKernel


class TestLLMFastLane(unittest.TestCase):
    def test_fast_lane_enabled_default(self):
        with patch.dict(os.environ, {"CNEXUS_LLM_FAST_LANE": "1"}, clear=False):
            self.assertTrue(llm_fast_lane_enabled())

    def test_executor_not_shared_with_l3(self):
        self.assertFalse(ExecutorPool.shared_with_l3)

    def test_generate_without_client(self):
        lane = LLMFastLane(None)
        result = asyncio.run(lane.generate("hello"))
        self.assertIn("hello", str(result))

    def test_generate_timeout(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_PROMPT_MINIMAL_V1": "0", "CNEXUS_PROMPT_MINIMAL_V2": "0", "CNEXUS_PROMPT_MINIMAL_V3": "0", "CNEXUS_PROMPT_MINIMAL_V4": "0"},
            clear=False,
        ):
            lane = LLMFastLane(None, timeout_s=0.001)

            def slow_call(prompt: str) -> str:
                import time

                time.sleep(0.05)
                return str(prompt)

            lane._call_llm = slow_call  # type: ignore[method-assign]
            result = asyncio.run(lane.generate("slow"))
        self.assertEqual(result.get("status"), "timeout")
        self.assertEqual(result.get("mode"), "fast_lane_v1")

    def test_chat_api_shape(self):
        lane = LLMFastLane(None)
        api = ChatAPI(lane)
        payload = asyncio.run(api.chat({"input": "ping"}))
        self.assertEqual(payload["path"], "fast_lane_v1")
        self.assertIn("ping", str(payload["response"]))

    def test_runtime_kernel_sync_bypass(self):
        kernel = RuntimeKernel(None)
        out = kernel.llm_generate_sync("test")
        self.assertIn("test", out)

    def test_chat_compute_plan_uses_fast_lane(self):
        with patch.dict(os.environ, {"CNEXUS_LLM_FAST_LANE": "1"}, clear=False):
            result = asyncio.run(chat_compute_plan(None, {"input": "hi"}))
        self.assertEqual(result["path"], "fast_lane_v1")
        self.assertEqual(result["type"], "chat_result")


if __name__ == "__main__":
    unittest.main()

"""Prompt Minimal v4 — intent bus, promptless execution."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.intent.execution_graph_v4 import ExecutionGraphV4
from core.intent.intent_bus_v4 import IntentBusV4, prompt_minimal_v4_enabled
from core.intent.llm_backend_v4 import LLMBackendV4
from core.intent.runtime_kernel_v4 import APIv4, RuntimeKernelV4, extract_v4_chat_response
from core.runtime.compute_plans import chat_compute_plan
from core.runtime.llm_fast_lane import ChatAPI, ChatAPIv4, LLMFastLane


class TestPromptMinimalV4(unittest.TestCase):
    def test_v4_enabled_default(self):
        with patch.dict(os.environ, {"CNEXUS_PROMPT_MINIMAL_V4": "1"}, clear=False):
            self.assertTrue(prompt_minimal_v4_enabled())

    def test_intent_bus_emit_chat(self):
        bus = IntentBusV4()

        async def handler(payload):
            return {"response": f"ok:{payload.get('input')}"}

        bus.register("chat", handler)
        result = asyncio.run(bus.emit("chat", {"input": "hi"}))
        self.assertEqual(result["mode"], "promptless_v4")
        self.assertEqual(result["results"][0]["response"], "ok:hi")

    def test_intent_bus_no_handler(self):
        bus = IntentBusV4()
        result = asyncio.run(bus.emit("missing", {}))
        self.assertEqual(result["status"], "no_handler")

    def test_llm_backend_raw(self):
        backend = LLMBackendV4(None)
        result = asyncio.run(backend.generate({"input": "ping"}))
        self.assertIn("ping", str(result["response"]))

    def test_execution_graph_chat(self):
        backend = LLMBackendV4(None)
        graph = ExecutionGraphV4(None, llm_backend=backend)
        result = asyncio.run(graph.execute("chat", {"input": "hello"}))
        self.assertIn("hello", str(result["response"]))

    def test_execution_graph_status(self):
        graph = ExecutionGraphV4(None)
        result = asyncio.run(graph.execute("status", {}))
        self.assertEqual(result["status"], "ok")
        self.assertIn("l3", result)

    def test_runtime_kernel_v4_handle(self):
        bus = IntentBusV4()
        graph = ExecutionGraphV4(None)
        kernel = RuntimeKernelV4(bus, graph)
        result = asyncio.run(kernel.handle_request("status", {}))
        self.assertEqual(result["mode"], "promptless_v4")

    def test_extract_v4_chat_response(self):
        bus_result = {
            "results": [{"response": "LLM_RESPONSE:hi", "status": "ok"}],
            "mode": "promptless_v4",
        }
        text = extract_v4_chat_response(bus_result)
        self.assertIn("hi", str(text))

    def test_fast_lane_v4_mode(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_PROMPT_MINIMAL_V4": "1",
                "CNEXUS_PROMPT_MINIMAL_V3": "0",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
            },
            clear=False,
        ):
            lane = LLMFastLane(None)
            self.assertIsNotNone(lane._kernel_v4)
            self.assertEqual(lane._prompt_mode, "prompt_minimal_v4")
            self.assertIsNone(lane.compiler)

    def test_chat_api_v4_execution(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_PROMPT_MINIMAL_V4": "1",
                "CNEXUS_PROMPT_MINIMAL_V3": "0",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
            },
            clear=False,
        ):
            lane = LLMFastLane(None)
            payload = asyncio.run(ChatAPI(lane).chat({"input": "yo", "intent": "chat"}))
        self.assertEqual(payload["mode"], "prompt_minimal_v4")
        self.assertEqual(payload["execution"], "intent_bus")

    def test_api_v4_endpoint(self):
        bus = IntentBusV4()
        graph = ExecutionGraphV4(None)
        kernel = RuntimeKernelV4(bus, graph)
        api = APIv4(kernel)
        payload = asyncio.run(api.endpoint({"intent": "status", "input": ""}))
        self.assertEqual(payload["mode"], "prompt_minimal_v4")

    def test_compute_plan_v4_mode(self):
        with patch.dict(
            os.environ,
            {
                "CNEXUS_LLM_FAST_LANE": "1",
                "CNEXUS_PROMPT_MINIMAL_V4": "1",
                "CNEXUS_PROMPT_MINIMAL_V3": "0",
                "CNEXUS_PROMPT_MINIMAL_V2": "0",
                "CNEXUS_PROMPT_MINIMAL_V1": "0",
            },
            clear=False,
        ):
            result = asyncio.run(chat_compute_plan(None, {"input": "hi", "intent": "chat"}))
        self.assertEqual(result["mode"], "prompt_minimal_v4")
        self.assertEqual(result["execution"], "intent_bus")

    def test_memory_query_intent(self):
        runtime = MagicMock()
        runtime.storage.recall.return_value = ["m1"]
        graph = ExecutionGraphV4(runtime)
        result = asyncio.run(graph.execute("memory_query", {"query": "q"}))
        self.assertEqual(len(result["items"]), 1)


if __name__ == "__main__":
    unittest.main()

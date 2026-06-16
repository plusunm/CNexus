"""LLM Fast Lane v2 — streaming, pooled connections, zero-hop."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from typing import AsyncIterator, List
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.llm_connection_pool import LLMConnection, LLMConnectionPool, get_llm_connection_pool
from core.runtime.llm_fast_lane_v2 import (
    ChatFastStreamAPI,
    LLMFastLaneV2,
    llm_fast_lane_v2_enabled,
    warm_llm_socket,
)


class TestLLMFastLaneV2(unittest.TestCase):
    def test_v2_enabled_default(self):
        with patch.dict(os.environ, {"CNEXUS_LLM_FAST_LANE_V2": "1"}, clear=False):
            self.assertTrue(llm_fast_lane_v2_enabled())

    def test_connection_pool_acquire_release(self):
        pool = LLMConnectionPool(size=4)
        conn_a = pool.acquire()
        conn_b = pool.acquire()
        self.assertIsInstance(conn_a, LLMConnection)
        self.assertIsInstance(conn_b, LLMConnection)
        pool.release(conn_a)

    def test_stream_generate_without_client(self):
        tokens: List[str] = []

        async def on_token(t: str) -> None:
            tokens.append(t)

        lane = LLMFastLaneV2(None)
        result = asyncio.run(lane.stream_generate("hello", on_token))
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["path"], "fast_lane_v2")
        self.assertIn("hello", "".join(tokens))

    def test_stream_chat_api_shape(self):
        seen: List[str] = []

        async def on_token(t: str) -> None:
            seen.append(t)

        lane = LLMFastLaneV2(None)
        api = ChatFastStreamAPI(lane)
        result = asyncio.run(api.chat_stream({"input": "ping"}, on_token))
        self.assertEqual(result["status"], "done")
        self.assertIn("ping", "".join(seen))

    def test_warm_llm_socket_stub(self):
        runtime = MagicMock()
        pool = LLMConnectionPool(size=2)
        runtime.llm_connection_pool = pool
        warmed = asyncio.run(warm_llm_socket(runtime))
        self.assertTrue(warmed)
        self.assertTrue(getattr(runtime, "llm_socket_warmed", False))

    def test_parse_sse_line_integration(self):
        from core.runtime.llm_connection_pool import _parse_openai_sse_line

        line = 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
        self.assertEqual(_parse_openai_sse_line(line), "Hi")
        self.assertIsNone(_parse_openai_sse_line("data: [DONE]"))

    def test_mock_stream_tokens(self):
        async def fake_stream(prompt: str) -> AsyncIterator[str]:
            for part in ("one ", "two"):
                yield part

        lane = LLMFastLaneV2(None)
        conn = lane.connection_pool.acquire()
        conn.stream_chat = fake_stream  # type: ignore[method-assign]

        async def collect() -> List[str]:
            out: List[str] = []
            async for t in lane.stream_tokens("x"):
                out.append(t)
            return out

        with patch.object(lane.connection_pool, "acquire", return_value=conn):
            parts = asyncio.run(collect())
        self.assertEqual(parts, ["one ", "two"])


if __name__ == "__main__":
    unittest.main()

"""LLM connection pool — keep-alive sockets for Fast Lane v2 zero-hop streaming."""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_pools: Dict[str, "LLMConnectionPool"] = {}
_pools_lock = threading.Lock()


def default_pool_size() -> int:
    raw = os.environ.get("CNEXUS_LLM_FAST_LANE_POOL_SIZE", "4").strip()
    try:
        return max(1, min(8, int(raw)))
    except ValueError:
        return 4


class LLMConnection:
    """Pooled keep-alive connection — direct ExecutionPlane stream path."""

    def __init__(
        self,
        *,
        plane: Optional[Any] = None,
        profile: Optional[Any] = None,
        conn_id: int = 0,
    ) -> None:
        self._plane = plane
        self._profile = profile
        self.conn_id = conn_id
        self._async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=4, max_connections=8),
        )
        self._sync_client = httpx.Client(
            timeout=httpx.Timeout(10.0, connect=3.0),
            limits=httpx.Limits(max_keepalive_connections=4, max_connections=8),
        )

    def ping(self) -> bool:
        """Lightweight warm — validates keep-alive socket."""
        profile = self._profile
        if profile is None:
            return True
        base = str(getattr(profile, "base_url", "") or "").rstrip("/")
        if not base:
            return True
        try:
            self._sync_client.get(base, timeout=2.0)
            return True
        except Exception:
            try:
                self._sync_client.head(base, timeout=2.0)
                return True
            except Exception as exc:
                logger.debug("LLMConnection ping %s: %s", self.conn_id, exc)
                return False

    async def stream_chat(self, prompt: str) -> AsyncIterator[str]:
        messages: List[dict] = [{"role": "user", "content": prompt}]
        profile = self._profile
        plane = self._plane

        if profile is None or plane is None:
            for ch in f"LLM_RESPONSE:{prompt}":
                yield ch
            return

        if getattr(profile, "provider", "") == "ollama":
            async for token in self._stream_ollama_fallback(messages, plane, profile):
                yield token
            return

        async for token in self._stream_openai_compat(messages, profile):
            yield token

    async def _stream_openai_compat(self, messages: List[dict], profile: Any) -> AsyncIterator[str]:
        url = _chat_completions_url(str(profile.base_url))
        headers = {"Content-Type": "application/json"}
        api_key = str(getattr(profile, "api_key", "") or "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload: Dict[str, Any] = {
            "model": profile.model,
            "messages": messages,
            "temperature": 0.7,
            "stream": True,
        }
        host = (urlparse(str(profile.base_url)).hostname or "").lower()
        if "deepseek.com" in host:
            payload["thinking"] = {"type": "disabled"}

        async with self._async_client.stream(
            "POST",
            url,
            json=payload,
            headers=headers,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                token = _parse_openai_sse_line(line)
                if token:
                    yield token

    async def _stream_ollama_fallback(
        self,
        messages: List[dict],
        plane: Any,
        profile: Any,
    ) -> AsyncIterator[str]:
        import asyncio

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: plane.chat(profile, messages, temperature=0.7, timeout=60.0),
        )
        text = str(getattr(result, "content", result))
        for part in text.split():
            yield part + " "

    async def aclose(self) -> None:
        await self._async_client.aclose()
        self._sync_client.close()


class LLMConnectionPool:
    def __init__(
        self,
        *,
        plane: Optional[Any] = None,
        profile: Optional[Any] = None,
        size: int = 4,
    ) -> None:
        self.plane = plane
        self.profile = profile
        self.size = size
        self.pool: List[LLMConnection] = [
            LLMConnection(plane=plane, profile=profile, conn_id=i) for i in range(size)
        ]
        self._index = 0
        self._lock = threading.Lock()

    def acquire(self) -> LLMConnection:
        with self._lock:
            conn = self.pool[self._index % len(self.pool)]
            self._index += 1
            return conn

    def release(self, conn: LLMConnection) -> None:
        _ = conn  # keep-alive — no teardown

    async def aclose(self) -> None:
        for conn in self.pool:
            await conn.aclose()


def _pool_key(plane: Optional[Any], profile: Optional[Any]) -> str:
    profile_id = getattr(profile, "id", None) or getattr(profile, "model", "default")
    return f"{id(plane)}:{profile_id}"


def get_llm_connection_pool(
    runtime: Optional[Any] = None,
    *,
    llm_client: Optional[Any] = None,
    profile: Optional[Any] = None,
    size: Optional[int] = None,
) -> LLMConnectionPool:
    client = llm_client or (getattr(runtime, "llm_client", None) if runtime else None)
    plane = getattr(client, "_plane", None) if client is not None else None
    if profile is None and runtime is not None:
        registry = getattr(runtime, "model_registry", None) or getattr(runtime, "registry", None)
        if registry is not None and hasattr(registry, "get_default"):
            profile = registry.get_default()

    key = _pool_key(plane, profile)
    with _pools_lock:
        pool = _pools.get(key)
        if pool is None:
            pool = LLMConnectionPool(
                plane=plane,
                profile=profile,
                size=size or default_pool_size(),
            )
            _pools[key] = pool
        if runtime is not None:
            setattr(runtime, "llm_connection_pool", pool)
        return pool


def _chat_completions_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    if url.startswith("http://"):
        url = "https://" + url[len("http://") :]
    parsed = urlparse(url)
    path = (parsed.path or "").rstrip("/")
    if path.endswith("/chat/completions"):
        return url
    if path.endswith("/v1"):
        return f"{url}/chat/completions"
    return f"{url}/v1/chat/completions"


def _parse_openai_sse_line(line: str) -> Optional[str]:
    if not line or not line.startswith("data:"):
        return None
    data = line[5:].strip()
    if data == "[DONE]":
        return None
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None
    choices = payload.get("choices") or []
    if not choices:
        return None
    delta = choices[0].get("delta") or {}
    content = delta.get("content")
    if content:
        return str(content)
    return None

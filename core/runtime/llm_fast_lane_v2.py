"""LLM Fast Lane v2 — streaming zero-hop with pooled keep-alive connections."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Optional

from core.prompt.fast_lane_prompt import (
    init_prompt_builders,
    prepare_fast_lane_prompt,
    resolve_user_text,
)
from core.runtime.llm_background_side_effects import schedule_background_side_effects
from core.runtime.llm_connection_pool import get_llm_connection_pool
from core.runtime.llm_fast_lane import LLMFastLane

logger = logging.getLogger(__name__)

TokenCallback = Callable[[str], Awaitable[None]]


def llm_fast_lane_v2_enabled() -> bool:
    flag = os.environ.get("CNEXUS_LLM_FAST_LANE_V2", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def default_v2_timeout_s() -> float:
    raw = os.environ.get("CNEXUS_LLM_FAST_LANE_V2_TIMEOUT_SEC", "30").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 30.0


class LLMFastLaneV2:
    """Stream tokens over pooled sockets — no scheduler / ready gate."""

    def __init__(
        self,
        runtime: Optional[Any] = None,
        *,
        llm_client: Optional[Any] = None,
        profile: Optional[Any] = None,
        timeout_s: Optional[float] = None,
    ) -> None:
        self.runtime = runtime
        self.llm_client = llm_client or LLMFastLane._resolve_client(runtime)
        self.profile = profile or LLMFastLane._resolve_profile(runtime)
        self.timeout_s = timeout_s if timeout_s is not None else default_v2_timeout_s()
        self.connection_pool = get_llm_connection_pool(
            runtime,
            llm_client=self.llm_client,
            profile=self.profile,
        )
        builders = init_prompt_builders(runtime)
        self._compiler = builders["compiler"]
        self._runner = builders["runner"]
        self._token_cache = builders["token_cache"]
        self._delta_builder = builders["delta_builder"]
        self._delta_cache = builders["delta_cache"]
        self._prompt_cache = builders["prompt_cache"]
        self._builder = builders["builder"]

    def _resolve_stream_prompt(
        self,
        user_input: str,
        *,
        intent: str = "chat",
        context_delta: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload, _mode, _cache_hit = prepare_fast_lane_prompt(
            self.runtime,
            user_input,
            intent=intent,
            context_delta=context_delta,
            compiler=self._compiler,
            runner=self._runner,
            token_cache=self._token_cache,
            delta_builder=self._delta_builder,
            delta_cache=self._delta_cache,
            prompt_cache=self._prompt_cache,
            builder=self._builder,
        )
        return resolve_user_text(payload)

    async def stream_generate(
        self,
        prompt: str,
        on_token: TokenCallback,
        timeout_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        effective = timeout_s if timeout_s is not None else self.timeout_s
        user_text = self._resolve_stream_prompt(prompt)
        conn = self.connection_pool.acquire()
        try:

            async def _pump() -> None:
                async for token in conn.stream_chat(user_text):
                    await on_token(token)

            await asyncio.wait_for(_pump(), timeout=effective)
            return {"status": "done", "path": "fast_lane_v2"}
        except asyncio.TimeoutError:
            return {"status": "timeout", "path": "fast_lane_v2", "mode": "fast_lane_v2"}
        except Exception as exc:
            logger.debug("LLMFastLaneV2 stream failed: %s", exc)
            return {"status": "failed", "error": str(exc), "path": "fast_lane_v2"}
        finally:
            self.connection_pool.release(conn)

    async def stream_tokens(self, prompt: str, timeout_s: Optional[float] = None) -> AsyncIterator[str]:
        effective = timeout_s if timeout_s is not None else self.timeout_s
        user_text = self._resolve_stream_prompt(prompt)
        conn = self.connection_pool.acquire()
        try:
            async def _iter() -> AsyncIterator[str]:
                async for token in conn.stream_chat(user_text):
                    yield token

            deadline = asyncio.get_running_loop().time() + effective
            async for token in _iter():
                if asyncio.get_running_loop().time() > deadline:
                    break
                yield token
        finally:
            self.connection_pool.release(conn)


class ChatFastStreamAPI:
    """SSE-facing streaming chat — no system_ready / scheduler."""

    def __init__(self, lane_v2: LLMFastLaneV2) -> None:
        self.lane = lane_v2

    async def chat_stream(
        self,
        request: Dict[str, Any],
        send_token: TokenCallback,
    ) -> Dict[str, Any]:
        prompt = str(request.get("input") or request.get("message") or "")
        return await self.lane.stream_generate(prompt, on_token=send_token)


async def warm_llm_socket(
    runtime: Optional[Any] = None,
    *,
    llm_client: Optional[Any] = None,
    profile: Optional[Any] = None,
) -> bool:
    """Pre-warm pooled keep-alive connections — reduces first-token latency."""
    pool = getattr(runtime, "llm_connection_pool", None) if runtime is not None else None
    if pool is None:
        pool = get_llm_connection_pool(runtime, llm_client=llm_client, profile=profile)
    loop = asyncio.get_running_loop()

    def _ping_all() -> int:
        ok = 0
        for conn in pool.pool:
            if conn.ping():
                ok += 1
        return ok

    warmed = await loop.run_in_executor(None, _ping_all)
    if runtime is not None:
        setattr(runtime, "llm_socket_warmed", warmed > 0)
    return warmed > 0


def get_llm_fast_lane_v2(
    runtime: Optional[Any] = None,
    *,
    llm_client: Optional[Any] = None,
    profile: Optional[Any] = None,
) -> LLMFastLaneV2:
    return LLMFastLaneV2(runtime, llm_client=llm_client, profile=profile)


async def stream_generate_with_side_effects(
    runtime: Optional[Any],
    prompt: str,
    on_token: TokenCallback,
    *,
    llm_client: Optional[Any] = None,
    profile: Optional[Any] = None,
    timeout_s: Optional[float] = None,
    emit_reasoning_meta: bool = True,
) -> Dict[str, Any]:
    from core.runtime.conscious_flow.reasoning_trace import (
        reasoning_trace_enabled,
        resolve_reasoning_trace_for_query,
    )
    from core.runtime.conscious_flow.chunked_response import ChunkedResponseMeta

    reasoning_meta: Optional[Dict[str, Any]] = None
    if emit_reasoning_meta and runtime is not None and reasoning_trace_enabled():
        trace = resolve_reasoning_trace_for_query(runtime, prompt, run_if_missing=True)
        if trace is not None:
            reasoning_meta = ChunkedResponseMeta(
                phase="reasoning",
                reasoning_trace=trace.to_dict(),
            ).to_dict()
            preview = trace.summary[:160]
            if preview:
                await on_token(f"[thinking] {preview}\n\n")

    lane = LLMFastLaneV2(runtime, llm_client=llm_client, profile=profile, timeout_s=timeout_s)
    result = await lane.stream_generate(prompt, on_token, timeout_s=timeout_s)
    if reasoning_meta is not None:
        result["reasoning_trace"] = reasoning_meta.get("reasoning_trace")
        result["stream_phases"] = ["reasoning", "decision"]
    schedule_background_side_effects(runtime, prompt)
    return result

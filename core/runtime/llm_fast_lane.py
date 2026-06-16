"""LLM Fast Lane v1 — direct model path, no ready / cluster / memory inline."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union

from core.intent.intent_bus_v4 import prompt_minimal_v4_enabled
from core.intent.runtime_kernel_v4 import (
    APIv4,
    extract_v4_chat_response,
    get_runtime_kernel_v4,
)
from core.prompt.fast_lane_prompt import (
    init_prompt_builders,
    prepare_fast_lane_prompt,
    resolve_prompt_mode,
    resolve_user_text,
)
from core.runtime.llm_executor_pool import ExecutorPool, ensure_runtime_llm_executor

logger = logging.getLogger(__name__)

LLMResponse = Union[str, Dict[str, Any]]
PromptPayload = Union[str, Dict[str, Any]]


def llm_fast_lane_enabled() -> bool:
    flag = os.environ.get("CNEXUS_LLM_FAST_LANE", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def default_fast_lane_timeout_s() -> float:
    raw = os.environ.get("CNEXUS_LLM_FAST_LANE_TIMEOUT_SEC", "3").strip()
    try:
        return max(0.5, float(raw))
    except ValueError:
        return 3.0


class LLMFastLane:
    """Bypass system_ready, scheduler hops, and inline memory hydrate."""

    def __init__(
        self,
        runtime: Optional[Any] = None,
        *,
        llm_client: Optional[Any] = None,
        profile: Optional[Any] = None,
        timeout_s: Optional[float] = None,
    ) -> None:
        self.runtime = runtime
        self.llm_client = llm_client or self._resolve_client(runtime)
        self.profile = profile or self._resolve_profile(runtime)
        self.timeout_s = timeout_s if timeout_s is not None else default_fast_lane_timeout_s()
        self.llm_executor = ensure_runtime_llm_executor(runtime)
        self._kernel_v4 = None
        self.compiler = None
        self.runner = None
        self.token_cache = None
        self.delta_builder = None
        self.delta_cache = None
        self.prompt_cache = None
        self.builder = None

        if prompt_minimal_v4_enabled():
            self._kernel_v4 = get_runtime_kernel_v4(
                runtime,
                llm_client=self.llm_client,
                profile=self.profile,
                timeout_s=self.timeout_s,
            )
            self._prompt_mode = "prompt_minimal_v4"
            return

        builders = init_prompt_builders(runtime)
        self.compiler = builders["compiler"]
        self.runner = builders["runner"]
        self.token_cache = builders["token_cache"]
        self.delta_builder = builders["delta_builder"]
        self.delta_cache = builders["delta_cache"]
        self.prompt_cache = builders["prompt_cache"]
        self.builder = builders["builder"]
        self._prompt_mode = resolve_prompt_mode(
            compiler=self.compiler,
            delta_builder=self.delta_builder if self.compiler is None else None,
            builder=self.builder,
        )

    def _prepare_prompt(
        self,
        user_input: str,
        *,
        intent: str = "chat",
        context_delta: Optional[Dict[str, Any]] = None,
    ) -> tuple[PromptPayload, bool]:
        payload, _mode, cache_hit = prepare_fast_lane_prompt(
            self.runtime,
            user_input,
            intent=intent,
            context_delta=context_delta,
            compiler=self.compiler,
            runner=self.runner,
            token_cache=self.token_cache,
            delta_builder=self.delta_builder,
            delta_cache=self.delta_cache,
            prompt_cache=self.prompt_cache,
            builder=self.builder,
        )
        return payload, cache_hit

    async def generate(
        self,
        user_input: str,
        timeout_s: Optional[float] = None,
        *,
        intent: str = "chat",
        context_delta: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        if self._kernel_v4 is not None:
            payload: Dict[str, Any] = {
                "input": user_input,
                "intent": intent,
            }
            if context_delta:
                payload["delta"] = context_delta
            bus_result = await self._kernel_v4.handle_request(intent, payload)
            return extract_v4_chat_response(bus_result)

        prompt_payload, cache_hit = self._prepare_prompt(
            user_input,
            intent=intent,
            context_delta=context_delta,
        )
        if cache_hit and self.delta_cache is not None and self.compiler is None:
            reused = self.delta_cache.reuse_result()
            if reused is not None:
                return reused

        effective = timeout_s if timeout_s is not None else self.timeout_s
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self.llm_executor, self._call_llm, prompt_payload)
        try:
            result = await asyncio.wait_for(future, timeout=effective)
            if self.delta_cache is not None and self.compiler is None:
                self.delta_cache.store_result(result)
            return result
        except asyncio.TimeoutError:
            return {"status": "timeout", "mode": self._prompt_mode}

    def _call_llm(self, prompt: PromptPayload) -> str:
        if isinstance(prompt, dict) and prompt.get("cache_hit"):
            user_text = str(prompt.get("input") or "")
        else:
            user_text = resolve_user_text(prompt)
        client = self.llm_client
        profile = self.profile
        if client is None:
            return f"LLM_RESPONSE:{user_text}"

        messages: List[dict] = [{"role": "user", "content": user_text}]
        timeout = float(self.timeout_s)

        try:
            plane = getattr(client, "_plane", None)
            if plane is not None and profile is not None:
                result = plane.chat(profile, messages, temperature=0.7, timeout=timeout)
                return str(getattr(result, "content", result))

            if profile is not None and hasattr(client, "chat"):
                return str(client.chat(profile, messages, temperature=0.7, timeout=timeout))

            if hasattr(client, "chat") and profile is None:
                try:
                    return str(client.chat(user_text))
                except TypeError:
                    pass
        except Exception as exc:
            logger.debug("LLMFastLane direct call failed: %s", exc)

        return f"LLM_RESPONSE:{user_text}"

    @staticmethod
    def _resolve_client(runtime: Optional[Any]) -> Optional[Any]:
        if runtime is None:
            return None
        return getattr(runtime, "llm_client", None)

    @staticmethod
    def _resolve_profile(runtime: Optional[Any]) -> Optional[Any]:
        if runtime is None:
            return None
        registry = getattr(runtime, "model_registry", None) or getattr(runtime, "registry", None)
        if registry is not None and hasattr(registry, "get_default"):
            profile = registry.get_default()
            if profile is not None and getattr(profile, "enabled", True):
                return profile
        return None


class ChatAPI:
    """HTTP-facing fast chat — never calls system_ready."""

    def __init__(self, llm_lane: LLMFastLane) -> None:
        self.llm_lane = llm_lane

    async def chat(self, request: Dict[str, Any]) -> Dict[str, Any]:
        user_input = str(request.get("input") or request.get("message") or "")
        intent = str(request.get("intent") or "chat")
        context_delta = request.get("delta")
        if not isinstance(context_delta, dict):
            context_delta = None
        result = await self.llm_lane.generate(
            user_input,
            intent=intent,
            context_delta=context_delta,
        )
        mode = self.llm_lane._prompt_mode
        path = "fast_lane_v1"
        execution = _resolve_execution_mode(mode)
        if isinstance(result, dict) and result.get("status") == "timeout":
            return {
                "response": "",
                "status": "timeout",
                "path": path,
                "mode": result.get("mode") or mode,
                "execution": execution,
            }
        return {
            "response": result,
            "status": "ok",
            "path": path,
            "mode": mode,
            "execution": execution,
        }


def _resolve_execution_mode(mode: str) -> Optional[str]:
    if mode == "prompt_minimal_v4":
        return "intent_bus"
    if mode == "prompt_minimal_v3":
        return "compiled_graph"
    return None


class ChatAPIv4:
    """Promptless API — intent bus only."""

    def __init__(self, kernel: Any) -> None:
        self._api = APIv4(kernel)

    async def chat(self, request: Dict[str, Any]) -> Dict[str, Any]:
        payload = await self._api.endpoint(request)
        bus_result = payload.get("response") or {}
        intent = str(request.get("intent") or "chat")
        if intent == "chat":
            text = extract_v4_chat_response(bus_result)
            if isinstance(text, dict) and text.get("status") == "timeout":
                return {
                    "response": "",
                    "status": "timeout",
                    "mode": "prompt_minimal_v4",
                    "execution": "intent_bus",
                }
            return {
                "response": text,
                "status": "ok",
                "mode": "prompt_minimal_v4",
                "execution": "intent_bus",
            }
        return {
            "response": bus_result,
            "status": "ok",
            "mode": "prompt_minimal_v4",
            "execution": "intent_bus",
        }


class ChatAPIv3:
    """Intent-driven chat — compiled execution graph path."""

    def __init__(self, llm_lane: LLMFastLane) -> None:
        self.llm_lane = llm_lane

    async def chat(self, request: Dict[str, Any]) -> Dict[str, Any]:
        user_input = str(request.get("input") or request.get("message") or "")
        intent = str(request.get("intent") or "chat")
        context_delta = request.get("delta")
        if not isinstance(context_delta, dict):
            context_delta = None
        result = await self.llm_lane.generate(
            user_input,
            intent=intent,
            context_delta=context_delta,
        )
        if isinstance(result, dict) and result.get("status") == "timeout":
            return {
                "response": "",
                "status": "timeout",
                "mode": "prompt_minimal_v3",
                "execution": "compiled_graph",
            }
        return {
            "response": result,
            "status": "ok",
            "mode": "prompt_minimal_v3",
            "execution": "compiled_graph",
        }


def get_llm_fast_lane(
    runtime: Optional[Any] = None,
    *,
    llm_client: Optional[Any] = None,
    profile: Optional[Any] = None,
) -> LLMFastLane:
    return LLMFastLane(runtime, llm_client=llm_client, profile=profile)

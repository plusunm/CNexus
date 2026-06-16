"""LLM backend v4 — raw payload execution, no prompt assembly."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from core.runtime.llm_executor_pool import ensure_runtime_llm_executor

logger = logging.getLogger(__name__)


class LLMBackendV4:
    """Execution backend — chat_raw only, zero prompt formatting."""

    def __init__(
        self,
        runtime: Optional[Any] = None,
        *,
        llm_client: Optional[Any] = None,
        profile: Optional[Any] = None,
        timeout_s: float = 3.0,
    ) -> None:
        self.runtime = runtime
        self.llm_client = llm_client
        self.profile = profile
        self.timeout_s = timeout_s
        self._executor = ensure_runtime_llm_executor(runtime)

    async def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw_input = str(payload.get("input") or payload.get("message") or "")
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self._executor, self.chat_raw, raw_input)
        try:
            text = await asyncio.wait_for(future, timeout=self.timeout_s)
            return {"response": text, "status": "ok", "backend": "llm_v4"}
        except asyncio.TimeoutError:
            return {"response": "", "status": "timeout", "backend": "llm_v4"}

    def chat_raw(self, raw_input: str) -> str:
        client = self.llm_client
        profile = self.profile
        if client is None:
            return f"LLM_RESPONSE:{raw_input}"

        messages: List[dict] = [{"role": "user", "content": raw_input}]
        timeout = float(self.timeout_s)

        try:
            plane = getattr(client, "_plane", None)
            if plane is not None and profile is not None:
                result = plane.chat(profile, messages, temperature=0.7, timeout=timeout)
                return str(getattr(result, "content", result))

            if profile is not None and hasattr(client, "chat"):
                return str(client.chat(profile, messages, temperature=0.7, timeout=timeout))

            raw_chat = getattr(client, "chat_raw", None)
            if callable(raw_chat):
                return str(raw_chat(raw_input))

            if hasattr(client, "chat") and profile is None:
                try:
                    return str(client.chat(raw_input))
                except TypeError:
                    pass
        except Exception as exc:
            logger.debug("LLMBackendV4 chat_raw failed: %s", exc)

        return f"LLM_RESPONSE:{raw_input}"


def get_llm_backend_v4(
    runtime: Optional[Any] = None,
    *,
    llm_client: Optional[Any] = None,
    profile: Optional[Any] = None,
    timeout_s: float = 3.0,
) -> LLMBackendV4:
    if runtime is not None:
        existing = getattr(runtime, "_llm_backend_v4", None)
        if isinstance(existing, LLMBackendV4):
            return existing
        backend = LLMBackendV4(runtime, llm_client=llm_client, profile=profile, timeout_s=timeout_s)
        setattr(runtime, "_llm_backend_v4", backend)
        runtime.llm_backend = backend
        return backend
    return LLMBackendV4(None, llm_client=llm_client, profile=profile, timeout_s=timeout_s)

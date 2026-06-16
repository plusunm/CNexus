"""MultiLLMAdapter — resolve model strings to ModelProfile + LLMClient calls."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from core.llm_client import LLMClient
from core.model_registry import ModelProfile, ModelRegistry


CNEXUS_MODEL_IDS = frozenset({"cnexus-cognitive", "cnexus-cognitive-pro"})


class MultiLLMAdapter:
    """Route model aliases to configured providers via existing LLMClient."""

    def __init__(
        self,
        runtime: Any,
        registry: ModelRegistry,
        llm_client: Optional[LLMClient] = None,
    ):
        self.runtime = runtime
        self.registry = registry
        self.llm = llm_client or getattr(runtime, "llm_client", None)
        if self.llm is None:
            self.llm = LLMClient()
        if self.llm._scheduler is None and hasattr(runtime, "inference_scheduler"):
            self.llm.bind_scheduler(runtime.inference_scheduler)
        elif self.llm._plane is None and hasattr(runtime, "execution_plane"):
            self.llm.bind_plane(runtime.execution_plane)
        if self.llm._scheduler is None and self.llm._plane is None:
            raise RuntimeError(
                "MultiLLMAdapter requires runtime.llm_client or a bound InferenceScheduler/ExecutionPlane"
            )

    def resolve_profile(self, model: str) -> ModelProfile:
        if model in CNEXUS_MODEL_IDS:
            default = self.registry.get_default()
            if default and default.enabled:
                return default
            return self._profile_from_runtime_config(model)

        by_id = self.registry.get(model)
        if by_id and by_id.enabled:
            return by_id

        model_lower = model.lower()
        for profile in self.registry.models:
            if not profile.enabled:
                continue
            if profile.model.lower() == model_lower or profile.id.lower() == model_lower:
                return profile

        provider = self._detect_provider(model_lower)
        preset = self._preset_for_provider(provider)
        if preset:
            return preset.model_copy(update={"model": model})

        return self._profile_from_runtime_config(model)

    def _profile_from_runtime_config(self, model: str) -> ModelProfile:
        cfg = self.runtime.config
        return ModelProfile(
            id=f"resolved-{model}",
            name=f"Resolved {model}",
            provider="ollama",
            base_url=cfg.get("ollama_host", "http://localhost:11434"),
            api_key="",
            model=cfg.get("llm_model", model),
            enabled=True,
        )

    @staticmethod
    def _detect_provider(model: str) -> str:
        if "claude" in model or "anthropic" in model:
            return "anthropic"
        if "ollama" in model or model.startswith(("llama", "qwen", "mistral", "gemma")):
            return "ollama"
        if "grok" in model:
            return "grok"
        if "deepseek" in model:
            return "deepseek"
        if "moonshot" in model or "kimi" in model:
            return "moonshot"
        if "qwen" in model or "dashscope" in model:
            return "qwen"
        if "glm" in model or "zhipu" in model:
            return "zhipu"
        return "openai_compatible"

    def _preset_for_provider(self, provider: str) -> Optional[ModelProfile]:
        aliases = {
            "ollama": ("ollama-local", "ollama"),
            "openai": ("openai-default", "openai"),
            "openai_compatible": ("openai-default", "openai_compatible"),
            "deepseek": ("deepseek-chat", "deepseek"),
            "grok": ("openai-default", "openai_compatible"),
            "anthropic": ("openai-default", "openai_compatible"),
            "moonshot": ("moonshot-kimi", "moonshot"),
            "qwen": ("qwen-turbo", "qwen"),
            "zhipu": ("zhipu-glm4", "zhipu"),
        }
        preferred_ids = aliases.get(provider, ())
        for model_id in preferred_ids:
            profile = self.registry.get(model_id)
            if profile and profile.enabled:
                return profile
        enabled = [m for m in self.registry.models if m.enabled]
        return enabled[0] if enabled else None

    def generate_sync(
        self,
        messages: List[Dict[str, str]],
        model: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        profile = self.resolve_profile(model)
        return self.llm.chat(profile, messages, temperature=temperature)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        return await asyncio.to_thread(
            self.generate_sync,
            messages,
            model,
            temperature=temperature,
        )

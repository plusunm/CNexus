from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from core.execution.providers.hash_embed import HashEmbedProvider
from core.execution.providers.ollama import OllamaProvider
from core.execution.providers.openai_compat import OpenAICompatibleProvider
from core.execution.types import ChatResult, EmbedResult, ExecutionStatus, ProviderHealth
from core.model_registry import ModelProfile

logger = logging.getLogger(__name__)


class ExecutionPlane:
    """Unified chat/embed routing — CNexus Core stays provider-agnostic."""

    def __init__(
        self,
        *,
        ollama_host: str = "http://localhost:11434",
        embed_model: str = "nomic-embed-text",
        vector_dim: int = 768,
        embedding_fallback: str = "hash",
        fail_loud_in_production: bool = False,
    ):
        self.ollama_host = ollama_host.rstrip("/")
        self.embed_model = embed_model
        self.vector_dim = vector_dim
        self.embedding_fallback = embedding_fallback
        self.fail_loud_in_production = fail_loud_in_production

        self.ollama = OllamaProvider(host=self.ollama_host)
        self.openai_compat = OpenAICompatibleProvider()
        self.hash_embed = HashEmbedProvider(vector_dim=vector_dim)

        mode = os.environ.get("BM_EMBEDDING_MODE", "auto").lower()
        self._force_hash = mode == "hash"
        self._force_ollama = mode == "ollama"
        self._ollama_embed_available: Optional[bool] = None

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "ExecutionPlane":
        fail_loud = bool(cfg.get("embedding_fail_loud_in_production", False))
        if os.environ.get("CNEXUS_ENV") == "production":
            fail_loud = fail_loud or bool(cfg.get("embedding_fail_loud_in_production", True))
        return cls(
            ollama_host=str(cfg.get("ollama_host", "http://localhost:11434")),
            embed_model=str(cfg.get("embedding_model", "nomic-embed-text")),
            vector_dim=int(cfg.get("vector_dim", 768)),
            embedding_fallback=str(cfg.get("embedding_fallback", "hash")),
            fail_loud_in_production=fail_loud,
        )

    def chat(
        self,
        profile: ModelProfile,
        messages: List[dict],
        *,
        temperature: float = 0.7,
        timeout: float = 120.0,
    ) -> ChatResult:
        if profile.provider == "ollama":
            return self.ollama.chat(
                messages,
                model=profile.model,
                base_url=profile.base_url,
                temperature=temperature,
                timeout=timeout,
            )
        return self.openai_compat.chat(
            messages,
            model=profile.model,
            base_url=profile.base_url,
            api_key=profile.api_key or "",
            temperature=temperature,
            timeout=timeout,
        )

    def embed(self, text: str, *, model: Optional[str] = None) -> EmbedResult:
        embed_model = model or self.embed_model

        if self._force_hash:
            return self.hash_embed.embed(text, model=embed_model)

        if self._ollama_embed_available is False and not self._force_ollama:
            return self._fallback_embed(text, embed_model, reason="ollama_marked_unavailable")

        try:
            result = self.ollama.embed(text, model=embed_model)
            self._ollama_embed_available = True
            return result
        except Exception as exc:
            if self._force_ollama:
                raise RuntimeError(f"Ollama embedding required but failed: {exc}") from exc
            if self.fail_loud_in_production and os.environ.get("CNEXUS_ENV") == "production":
                raise RuntimeError(
                    f"Production embedding requires Ollama but fallback would be used: {exc}"
                ) from exc
            if self._ollama_embed_available is not False:
                logger.warning("Embed provider fallback to hash: %s", exc)
            self._ollama_embed_available = False
            return self._fallback_embed(text, embed_model, reason=str(exc))

    def _fallback_embed(self, text: str, model: str, *, reason: str = "") -> EmbedResult:
        if self.embedding_fallback == "zero":
            return EmbedResult(
                vector=[0.0] * self.vector_dim,
                provider="zero_embed",
                model=model,
            )
        result = self.hash_embed.embed(text, model=model)
        if reason:
            logger.debug("Hash embed fallback: %s", reason)
        return result

    def active_embed_provider_id(self) -> str:
        if self._force_hash:
            return self.hash_embed.provider_id
        if self._force_ollama:
            return self.ollama.provider_id
        if self._ollama_embed_available is False:
            return self.hash_embed.provider_id
        health = self.ollama.health(embed_model=self.embed_model)
        if health.reachable and not any(i.startswith("embed_model_not_pulled") for i in health.issues):
            return self.ollama.provider_id
        return self.hash_embed.provider_id

    def active_chat_provider_id(self, profile: Optional[ModelProfile]) -> Optional[str]:
        if profile is None:
            return None
        if profile.provider == "ollama":
            return self.ollama.provider_id
        return self.openai_compat.provider_id

    def provider_health(
        self,
        *,
        chat_profile: Optional[ModelProfile] = None,
    ) -> Dict[str, ProviderHealth]:
        chat_model = chat_profile.model if chat_profile and chat_profile.provider == "ollama" else ""
        ollama_health = self.ollama.health(
            chat_model=chat_model,
            embed_model=self.embed_model,
        )
        openai_health = self.openai_compat.health(
            api_key_set=bool(chat_profile and (chat_profile.api_key or "").strip()),
            base_url=chat_profile.base_url if chat_profile else "",
        )
        hash_health = self.hash_embed.health()
        return {
            self.ollama.provider_id: ollama_health,
            self.openai_compat.provider_id: openai_health,
            self.hash_embed.provider_id: hash_health,
        }

    def execution_status(self, *, chat_profile: Optional[ModelProfile] = None) -> ExecutionStatus:
        providers = self.provider_health(chat_profile=chat_profile)
        active_chat = self.active_chat_provider_id(chat_profile)
        active_embed = self.active_embed_provider_id()

        suggested: List[str] = []
        ollama = providers[self.ollama.provider_id]
        for issue in ollama.issues:
            if issue.startswith("chat_model_not_pulled:"):
                suggested.append(f"pull:{issue.split(':', 1)[1]}")
            elif issue.startswith("embed_model_not_pulled:"):
                suggested.append(f"pull:{issue.split(':', 1)[1]}")
            elif issue == "not_running":
                suggested.append("start:ollama")
            elif issue == "not_installed":
                suggested.append("install:ollama")

        return ExecutionStatus(
            active_chat_provider=active_chat,
            active_embed_provider=active_embed,
            providers=providers,
            suggested_actions=suggested,
        )

    def embedding_status_payload(self) -> dict:
        configured = os.environ.get("BM_EMBEDDING_MODE", "auto").lower()
        active_provider = self.active_embed_provider_id()
        active_mode = "ollama" if active_provider == self.ollama.provider_id else "hash"
        from core.ollama_manager import is_ollama_running

        ollama_ok = active_mode == "ollama" and is_ollama_running(self.ollama_host)
        return {
            "configured_mode": configured,
            "active_mode": active_mode,
            "active_provider": active_provider,
            "ollama_reachable": ollama_ok,
            "model": self.embed_model,
            "host": self.ollama_host,
            "used_on": ["capture", "recall"],
            "not_used_on": ["reflection", "chat_llm"],
        }

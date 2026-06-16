import logging
import os
from typing import List, Literal, Optional

from core.execution.providers.hash_embed import HashEmbedProvider
from core.execution.inference_scheduler import InferenceScheduler
from core.execution.plane import ExecutionPlane

logger = logging.getLogger(__name__)

FallbackMode = Literal["hash", "zero"]
EmbedMode = Literal["auto", "hash", "ollama"]


class EmbeddingService:
    """Embedding facade — cache-first via Inference Scheduler when bound."""

    def __init__(
        self,
        plane: Optional[ExecutionPlane] = None,
        scheduler: Optional[InferenceScheduler] = None,
        vector_dim: int = 768,
        fallback: str = "hash",
        fail_loud_in_production: bool = False,
        host: str = "",
        model: str = "",
    ):
        self._plane = plane
        self._scheduler = scheduler
        ref = scheduler.plane if scheduler else plane
        self.vector_dim = vector_dim
        self.fallback = fallback if fallback in ("hash", "zero") else "hash"
        self._fail_loud_in_production = fail_loud_in_production
        self._unbound = ref is None
        self._hash_provider: Optional[HashEmbedProvider] = None

        if self._unbound:
            if self._fail_loud_in_production and os.environ.get("CNEXUS_ENV") == "production":
                raise ValueError("EmbeddingService requires plane or scheduler in production")
            logger.warning(
                "EmbeddingService unbound — degrading to %s fallback (no plane/scheduler)",
                self.fallback,
            )
            self._hash_provider = HashEmbedProvider(vector_dim=vector_dim)
            self.host = host or "http://localhost:11434"
            self.model = model or "nomic-embed-text"
            return

        self._plane = ref
        self.host = host or ref.ollama_host
        self.model = model or ref.embed_model

    def _fallback_vector(self, text: str) -> List[float]:
        if self.fallback == "zero":
            return [0.0] * self.vector_dim
        provider = self._hash_provider or HashEmbedProvider(vector_dim=self.vector_dim)
        return list(provider.embed(text, model=self.model or "hash").vector)

    def check_ollama(self) -> bool:
        if self._unbound:
            return False
        return bool(self.status_payload().get("ollama_reachable"))

    def active_mode(self) -> str:
        if self._unbound:
            return self.fallback
        return str(self.status_payload().get("active_mode", "hash"))

    def status_payload(self) -> dict:
        if self._unbound:
            return {
                "active_mode": self.fallback,
                "unbound": True,
                "ollama_reachable": False,
                "configured_host": self.host,
                "configured_model": self.model,
            }
        payload = self._plane.embedding_status_payload()
        if self._scheduler:
            payload["scheduler"] = self._scheduler.stats_payload()
        return payload

    def embed(self, text: str) -> List[float]:
        if self._unbound:
            return self._fallback_vector(text)
        if self._scheduler is not None:
            result = self._scheduler.embed(text, model=self.model)
        else:
            result = self._plane.embed(text, model=self.model)
        vector = list(result.vector)
        if len(vector) != self.vector_dim and self.vector_dim:
            logger.warning(
                "Embed dimension mismatch: got %s expected %s",
                len(vector),
                self.vector_dim,
            )
        return vector

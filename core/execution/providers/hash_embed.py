from __future__ import annotations

import hashlib
import math
from typing import List

from core.execution.types import ChatResult, EmbedResult, ProviderHealth


class HashEmbedProvider:
    """Deterministic local embed fallback — dev / offline only."""

    provider_id = "hash_embed"
    capabilities = frozenset({"embed"})

    def __init__(self, vector_dim: int = 768):
        self.vector_dim = vector_dim

    def chat(
        self,
        messages: List[dict],
        *,
        model: str,
        base_url: str = "",
        api_key: str = "",
        temperature: float = 0.7,
        timeout: float = 120.0,
    ) -> ChatResult:
        raise NotImplementedError("hash_embed provider does not support chat")

    def _hash_vector(self, text: str) -> List[float]:
        out: List[float] = []
        counter = 0
        while len(out) < self.vector_dim:
            digest = hashlib.sha256(f"{text}:{counter}".encode("utf-8")).digest()
            for byte in digest:
                out.append((byte / 127.5) - 1.0)
                if len(out) >= self.vector_dim:
                    break
            counter += 1
        norm = math.sqrt(sum(x * x for x in out)) or 1.0
        return [x / norm for x in out]

    def embed(self, text: str, *, model: str, timeout: float = 8.0) -> EmbedResult:
        return EmbedResult(
            vector=self._hash_vector(text),
            provider=self.provider_id,
            model=model or "hash",
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            state="ready",
            capabilities=["embed"],
            reachable=True,
            issues=[],
            details={"mode": "deterministic_hash"},
        )

import hashlib
import logging
import math
import os
from typing import List, Literal, Optional

import httpx

logger = logging.getLogger(__name__)

FallbackMode = Literal["hash", "zero"]
EmbedMode = Literal["auto", "hash", "ollama"]


class EmbeddingService:
    """Ollama embedding with deterministic hash fallback when unavailable."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        vector_dim: int = 768,
        fallback: FallbackMode = "hash",
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.vector_dim = vector_dim
        self.fallback = fallback
        self._ollama_available: Optional[bool] = None
        mode = os.environ.get("BM_EMBEDDING_MODE", "auto").lower()
        self._force_hash = mode == "hash"
        self._force_ollama = mode == "ollama"

    def _hash_embed(self, text: str) -> List[float]:
        """Deterministic pseudo-embedding — usable for recall without Ollama."""
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

    def _fallback_embed(self, text: str) -> List[float]:
        if self.fallback == "zero":
            return [0.0] * self.vector_dim
        return self._hash_embed(text)

    def check_ollama(self) -> bool:
        if self._force_hash:
            return False
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.host}/api/tags")
                self._ollama_available = resp.status_code == 200
        except Exception:
            self._ollama_available = False
        return bool(self._ollama_available)

    def embed(self, text: str) -> List[float]:
        if self._force_hash:
            return self._fallback_embed(text)

        if self._ollama_available is False and not self._force_ollama:
            return self._fallback_embed(text)

        last_exc: Exception | None = None
        payloads = [
            (f"{self.host}/api/embed", {"model": self.model, "input": text}),
            (f"{self.host}/api/embeddings", {"model": self.model, "prompt": text}),
        ]
        for url, body in payloads:
            try:
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(url, json=body)
                    resp.raise_for_status()
                    data = resp.json()
                    embedding = data.get("embedding") or (
                        data.get("embeddings", [None])[0] if data.get("embeddings") else None
                    )
                    if embedding:
                        self._ollama_available = True
                        return embedding
            except Exception as exc:
                last_exc = exc

        if self._force_ollama:
            raise RuntimeError(f"Ollama embedding required but failed: {last_exc}")

        if self._ollama_available is not False:
            logger.warning(
                "Ollama embedding unavailable, using %s fallback: %s",
                self.fallback,
                last_exc,
            )
        self._ollama_available = False
        return self._fallback_embed(text)

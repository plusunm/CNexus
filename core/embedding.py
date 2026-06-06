import logging
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Ollama embedding service with zero-vector fallback."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "nomic-embed-text", vector_dim: int = 768):
        self.host = host.rstrip("/")
        self.model = model
        self.vector_dim = vector_dim

    def embed(self, text: str) -> List[float]:
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{self.host}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                resp.raise_for_status()
                embedding = resp.json().get("embedding")
                if embedding:
                    return embedding
        except Exception as exc:
            logger.warning("Ollama embedding failed, using zero vector: %s", exc)
        return [0.0] * self.vector_dim

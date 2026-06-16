from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import httpx

from core.execution.types import ChatResult, EmbedResult, ProviderHealth
from core.ollama_manager import get_ollama_status, is_ollama_running


def _ollama_client(timeout: float) -> httpx.Client:
    """Local Ollama must bypass system HTTP proxy (otherwise 502 on localhost)."""
    return httpx.Client(timeout=timeout, trust_env=False)


class OllamaProvider:
    provider_id = "ollama"
    capabilities = frozenset({"chat", "embed"})

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host.rstrip("/")
        self._cached_tags: Optional[Set[str]] = None

    def _tags(self, *, refresh: bool = False) -> Set[str]:
        if self._cached_tags is not None and not refresh:
            return self._cached_tags
        names: Set[str] = set()
        if not is_ollama_running(self.host):
            self._cached_tags = names
            return names
        try:
            with _ollama_client(3.0) as client:
                resp = client.get(f"{self.host}/api/tags")
                resp.raise_for_status()
                for item in resp.json().get("models") or []:
                    name = item.get("name") or item.get("model") or ""
                    if name:
                        names.add(str(name).split(":")[0])
                        names.add(str(name))
        except Exception:
            pass
        self._cached_tags = names
        return names

    def model_pulled(self, model: str) -> bool:
        base = model.split(":")[0]
        tags = self._tags(refresh=True)
        return model in tags or base in tags or any(t.startswith(f"{base}:") for t in tags)

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
        host = (base_url or self.host).rstrip("/")
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        with _ollama_client(timeout) as client:
            resp = client.post(f"{host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data.get("message", {}).get("content", "") or ""
        return ChatResult(content=content, provider=self.provider_id, model=model, raw=data)

    def embed(self, text: str, *, model: str, timeout: float = 8.0) -> EmbedResult:
        host = self.host
        last_exc: Exception | None = None
        payloads = [
            (f"{host}/api/embed", {"model": model, "input": text}),
            (f"{host}/api/embeddings", {"model": model, "prompt": text}),
        ]
        for url, body in payloads:
            try:
                with _ollama_client(timeout) as client:
                    resp = client.post(url, json=body)
                    resp.raise_for_status()
                    data = resp.json()
                    embedding = data.get("embedding") or (
                        data.get("embeddings", [None])[0] if data.get("embeddings") else None
                    )
                    if embedding:
                        self._cached_tags = None
                        return EmbedResult(
                            vector=list(embedding),
                            provider=self.provider_id,
                            model=model,
                        )
            except Exception as exc:
                last_exc = exc
        raise RuntimeError(f"Ollama embed failed: {last_exc}")

    def health(self, *, chat_model: str = "", embed_model: str = "") -> ProviderHealth:
        status = get_ollama_status(self.host)
        running = bool(status.get("running"))
        issues: List[str] = []
        if not status.get("installed") and not running:
            issues.append("not_installed")
        elif not running:
            issues.append("not_running")
        if chat_model and running and not self.model_pulled(chat_model):
            issues.append(f"chat_model_not_pulled:{chat_model}")
        if embed_model and running and not self.model_pulled(embed_model):
            issues.append(f"embed_model_not_pulled:{embed_model}")

        if not running:
            state = "unavailable"
        elif issues:
            state = "degraded"
        else:
            state = "ready"

        return ProviderHealth(
            provider_id=self.provider_id,
            state=state,
            capabilities=["chat", "embed"],
            reachable=running,
            issues=issues,
            details={
                "host": self.host,
                "installed": bool(status.get("installed")),
                "binary_found": bool(status.get("binary_found")),
                "binary_path": status.get("binary_path"),
            },
        )

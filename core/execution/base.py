from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from core.execution.types import Capability, ChatResult, EmbedResult, ProviderHealth


@runtime_checkable
class ExecutionProvider(Protocol):
    provider_id: str
    capabilities: frozenset[Capability]

    def chat(
        self,
        messages: List[dict],
        *,
        model: str,
        base_url: str,
        api_key: str = "",
        temperature: float = 0.7,
        timeout: float = 120.0,
    ) -> ChatResult: ...

    def embed(self, text: str, *, model: str, timeout: float = 8.0) -> EmbedResult: ...

    def health(self) -> ProviderHealth: ...

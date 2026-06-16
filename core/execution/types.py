from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

Capability = Literal["chat", "embed"]
ProviderId = Literal["ollama", "openai_compatible", "hash_embed"]
HealthState = Literal["ready", "degraded", "unavailable"]


@dataclass
class ChatResult:
    content: str
    provider: str
    model: str
    raw: Optional[Dict[str, Any]] = None


@dataclass
class EmbedResult:
    vector: List[float]
    provider: str
    model: str


@dataclass
class ProviderHealth:
    provider_id: str
    state: HealthState
    capabilities: List[Capability]
    reachable: bool = False
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionStatus:
    """Provider selection hint — not a cognition gate."""

    active_chat_provider: Optional[str]
    active_embed_provider: Optional[str]
    providers: Dict[str, ProviderHealth]
    suggested_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_chat_provider": self.active_chat_provider,
            "active_embed_provider": self.active_embed_provider,
            "providers": {
                pid: {
                    "state": h.state,
                    "capabilities": list(h.capabilities),
                    "reachable": h.reachable,
                    "issues": list(h.issues),
                    "details": dict(h.details),
                }
                for pid, h in self.providers.items()
            },
            "suggested_actions": list(self.suggested_actions),
        }

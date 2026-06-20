"""Legacy HTTP API → AuthorityDispatcher adapter (eliminates direct runtime bypass)."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from core.control_plane.dispatch import AuthorityDispatcher
from core.control_plane.types import RouteKind, build_dispatch_context

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime

LEGACY_CALLER = "legacy_api"
LEGACY_CHANNEL = "legacy-web-api"
LEGACY_V1_CHANNEL = "legacy-v1-api"
LEGACY_OPENAI_CHANNEL = "legacy-openai-api"


class LegacyDispatchAdapter:
    """Route legacy /api/* mutation paths through AuthorityDispatcher."""

    def __init__(self, dispatcher: AuthorityDispatcher) -> None:
        self._dispatcher = dispatcher

    @classmethod
    def from_runtime(cls, runtime: "BrainMemoryRuntime") -> "LegacyDispatchAdapter":
        return cls(AuthorityDispatcher(runtime))

    @property
    def runtime(self) -> "BrainMemoryRuntime":
        return self._dispatcher.runtime

    def chat(
        self,
        *,
        message: str,
        use_memory: bool = True,
        temperature: float = 0.7,
        llm_client: Any,
        llm_profile: Any,
        allow_proactive: bool = True,
        trace_id: Optional[str] = None,
        channel: str = LEGACY_CHANNEL,
    ) -> Dict[str, Any]:
        return self.interact(
            message=message,
            use_memory=use_memory,
            temperature=temperature,
            llm_client=llm_client,
            llm_profile=llm_profile,
            allow_proactive=allow_proactive,
            trace_id=trace_id,
            channel=channel,
        )

    def interact(
        self,
        *,
        message: str,
        use_memory: bool = True,
        temperature: float = 0.7,
        llm_client: Any = None,
        llm_profile: Any = None,
        allow_proactive: bool = True,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        assistant_output: Optional[str] = None,
        chat_mode: bool = True,
        trace_id: Optional[str] = None,
        channel: str = LEGACY_V1_CHANNEL,
    ) -> Dict[str, Any]:
        meta = dict(metadata or {})
        if user_id:
            meta.setdefault("user_id", user_id)
        payload: Dict[str, Any] = {
            "message": message,
            "use_memory": use_memory,
            "temperature": temperature,
            "allow_proactive": allow_proactive,
            "chat_mode": chat_mode,
            "metadata": meta,
        }
        if llm_client is not None:
            payload["llm_client"] = llm_client
        if llm_profile is not None:
            payload["llm_profile"] = llm_profile
        if assistant_output is not None:
            payload["assistant_output"] = assistant_output
        if user_id is not None:
            payload["user_id"] = user_id
        return self._dispatcher.dispatch(
            build_dispatch_context(
                RouteKind.CHAT_SEND,
                payload,
                caller=LEGACY_CALLER,
                channel=channel,
                trace_id=trace_id,
            )
        )

    def capture(
        self,
        *,
        role: str,
        content: str,
        layer: str = "episodic",
        importance: float = 0.5,
        meta: Optional[Dict[str, Any]] = None,
        return_detail: bool = False,
        trace_id: Optional[str] = None,
        channel: str = LEGACY_V1_CHANNEL,
    ) -> Any:
        capture_meta = dict(meta or {})
        if return_detail:
            capture_meta["return_detail"] = True
        return self._dispatcher.dispatch(
            build_dispatch_context(
                RouteKind.MEMORY_WRITE,
                {
                    "role": role,
                    "content": content,
                    "layer": layer,
                    "importance": importance,
                    "meta": dict(capture_meta, source="api"),
                },
                caller=LEGACY_CALLER,
                channel=channel,
                trace_id=trace_id,
            )
        )

    def governance_cycle(
        self,
        *,
        trace_id: Optional[str] = None,
        channel: str = LEGACY_CHANNEL,
    ) -> Dict[str, Any]:
        return self._dispatcher.dispatch(
            build_dispatch_context(
                RouteKind.GOVERNANCE_CYCLE,
                {},
                caller=LEGACY_CALLER,
                channel=channel,
                trace_id=trace_id,
            )
        )

    def recall_preview(
        self,
        query: str,
        *,
        top_k: Optional[int] = None,
        trace_id: Optional[str] = None,
        channel: str = LEGACY_CHANNEL,
    ) -> str:
        payload: Dict[str, Any] = {"query": query}
        if top_k is not None:
            payload["top_k"] = top_k
        return self._dispatcher.dispatch(
            build_dispatch_context(
                RouteKind.MEMORY_READ,
                payload,
                caller=LEGACY_CALLER,
                channel=channel,
                trace_id=trace_id,
            )
        )

    def memory_recall(
        self,
        *,
        query: str,
        top_k: Optional[int] = None,
        trace_id: Optional[str] = None,
        channel: str = LEGACY_V1_CHANNEL,
    ) -> str:
        return self.recall_preview(
            query,
            top_k=top_k,
            trace_id=trace_id,
            channel=channel,
        )

    def observe_read(self, kind: str, **payload: Any) -> Any:
        """Read-only observe surface — routes through kernel OBSERVE intent."""
        return self._dispatcher.observe_read(kind, **payload)

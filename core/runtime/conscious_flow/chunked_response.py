"""L4-3 — ChunkedResponse streaming with reasoning meta phase."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from core.runtime.conscious_flow.reasoning_trace import ReasoningTrace


@dataclass
class ChunkedResponseMeta:
    phase: str
    reasoning_trace: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"phase": self.phase}
        if self.reasoning_trace is not None:
            payload["reasoning_trace"] = dict(self.reasoning_trace)
        return payload


@dataclass
class ChunkedResponse:
    content: str
    meta: ChunkedResponseMeta = field(default_factory=lambda: ChunkedResponseMeta(phase="decision"))

    def to_dict(self) -> Dict[str, Any]:
        return {"content": self.content, "meta": self.meta.to_dict()}


def iter_reasoning_enhanced_chunks(
    *,
    reasoning_trace: Optional[ReasoningTrace],
    final_content: str,
) -> Iterator[ChunkedResponse]:
    """Emit reasoning meta first, then decision content — signals 'thinking' not lag."""
    if reasoning_trace is not None:
        yield ChunkedResponse(
            content="",
            meta=ChunkedResponseMeta(
                phase="reasoning",
                reasoning_trace=reasoning_trace.to_dict(),
            ),
        )
    yield ChunkedResponse(
        content=final_content,
        meta=ChunkedResponseMeta(phase="decision"),
    )


def build_stream_payload(
    *,
    reasoning_trace: Optional[ReasoningTrace],
    final_content: str,
) -> List[Dict[str, Any]]:
    """SSE-friendly chunk list for fast-lane streaming adapters."""
    return [chunk.to_dict() for chunk in iter_reasoning_enhanced_chunks(
        reasoning_trace=reasoning_trace,
        final_content=final_content,
    )]

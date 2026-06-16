"""Token event schema — execution-attributed resource facts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

TokenSource = Literal[
    "llm_generate",
    "recall",
    "explain_v3",
    "causal_expand",
    "identity_hash",
    "control_decision",
]

CostLevel = Literal["low", "mid", "high", "spike"]


@dataclass
class TokenEvent:
    trace_id: str
    event_id: str
    source: str
    tokens_in: int
    tokens_out: int
    total: int
    spine_event_id: Optional[str] = None
    causal_edge_id: Optional[str] = None
    identity_id: Optional[str] = None
    phase: str = "EXEC"
    timestamp: float = 0.0
    mode: str = ""
    cost_level: CostLevel = "mid"
    entry: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TokenTraceSummary:
    trace_id: str
    tokens_in: int
    tokens_out: int
    total: int
    mode: str
    cost_level: CostLevel
    entry: str
    event_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_cost_level(total: int, *, avg: float) -> CostLevel:
    if avg <= 0:
        return "mid"
    ratio = total / avg
    if ratio >= 2.5:
        return "spike"
    if ratio >= 1.5:
        return "high"
    if ratio < 0.5:
        return "low"
    return "mid"


def infer_source_from_event(event: dict[str, Any]) -> str:
    etype = str(event.get("event_type") or "").lower()
    if etype in ("llm", "llm_generate", "chat"):
        return "llm_generate"
    if etype in ("recall",):
        return "recall"
    if etype in ("explain", "explanation"):
        return "explain_v3"
    if etype in ("control",):
        return "control_decision"
    if etype in ("causal", "causal_expand"):
        return "causal_expand"
    return "llm_generate"


def infer_phase_from_event(event: dict[str, Any]) -> str:
    etype = str(event.get("event_type") or "").lower()
    if etype in ("recall",):
        return "RECALL"
    if etype in ("explain", "explanation"):
        return "EXPLAIN"
    if etype in ("control",):
        return "CONTROL"
    return "EXEC"


def estimate_tokens_from_event(event: dict[str, Any]) -> tuple[int, int]:
    """Derive token counts from event payload or heuristics (introspect proxy)."""
    payload = event.get("payload") or {}
    usage = payload.get("usage") or payload.get("token_usage") or {}
    if usage:
        tin = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        tout = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        if tin or tout:
            return tin, tout

    etype = str(event.get("event_type") or "").lower()
    heuristics: dict[str, tuple[int, int]] = {
        "llm": (500, 200),
        "llm_generate": (500, 200),
        "chat": (400, 180),
        "recall": (300, 80),
        "explain": (600, 400),
        "explanation": (600, 400),
        "control": (50, 20),
        "write_intent": (80, 30),
        "state": (40, 10),
    }
    return heuristics.get(etype, (120, 60))

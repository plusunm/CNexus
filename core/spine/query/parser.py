"""Minimal Spine Query DSL parser — TRACE + optional EXPLAIN."""

from __future__ import annotations

import re
from typing import Optional

from core.spine.query.types import ExplainMode, ParsedQuery

_TRACE_RE = re.compile(
    r"^\s*TRACE\s+(\S+)(?:\s+EXPLAIN\s+(\S+))?\s*$",
    re.IGNORECASE,
)

_VALID_MODES = frozenset({"causal", "linear", "event", "control", "state", "explain"})


def _normalize_mode(raw: Optional[str]) -> ExplainMode:
    if not raw:
        return "causal"
    mode = raw.strip().lower()
    if mode in _VALID_MODES:
        return mode  # type: ignore[return-value]
    return "causal"


def parse_query_text(query: str, *, limit: int = 200) -> ParsedQuery:
    text = (query or "").strip()
    if not text:
        raise ValueError("query_empty")

    match = _TRACE_RE.match(text)
    if not match:
        raise ValueError("query_parse_failed")

    trace_id = match.group(1)
    mode = _normalize_mode(match.group(2))
    return ParsedQuery(trace_id=trace_id, mode=mode, limit=limit)


def resolve_query(
    *,
    query: Optional[str] = None,
    trace_id: Optional[str] = None,
    mode: str = "causal",
    limit: int = 200,
) -> ParsedQuery:
    if query and query.strip():
        parsed = parse_query_text(query, limit=limit)
        if trace_id and trace_id != parsed.trace_id:
            parsed.trace_id = trace_id
        return parsed
    if trace_id and trace_id.strip():
        return ParsedQuery(trace_id=trace_id.strip(), mode=_normalize_mode(mode), limit=limit)
    raise ValueError("trace_id_required")

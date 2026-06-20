"""Layer 2 — canonical trace_id SSOT (Runbook: t-{uuid.hex[:16]})."""

from __future__ import annotations

import re
import uuid
from typing import Optional

CANONICAL_TRACE_ID_RE = re.compile(r"^t-[0-9a-f]{16}$")
_LEGACY_HEX12_RE = re.compile(r"^trace-([0-9a-f]{12})$", re.IGNORECASE)


def generate_trace_id() -> str:
    """Create a new Runbook-canonical trace identifier."""
    return f"t-{uuid.uuid4().hex[:16]}"


def is_legacy_trace_id(trace_id: Optional[str]) -> bool:
    """True for pre-L2 `trace-*` identifiers (including semantic legacy strings)."""
    return bool(trace_id) and str(trace_id).startswith("trace-")


def is_canonical_trace_id(trace_id: Optional[str]) -> bool:
    """True when trace_id matches `t-` + 16 lowercase hex chars."""
    return bool(trace_id) and CANONICAL_TRACE_ID_RE.match(str(trace_id)) is not None


def normalize_trace_id(raw: Optional[str]) -> str:
    """Compat read: upgrade old `trace-{12hex}` to canonical; preserve semantic legacy ids."""
    tid = (raw or "").strip()
    if not tid:
        return generate_trace_id()
    if is_canonical_trace_id(tid):
        return tid
    match = _LEGACY_HEX12_RE.match(tid)
    if match:
        hex12 = match.group(1).lower()
        return f"t-{hex12}{hex12[:4]}"
    return tid


def coerce_trace_id(raw: Optional[str]) -> str:
    """Bind helper: explicit id preserved (legacy or canonical); empty → generate."""
    tid = (raw or "").strip()
    if tid:
        return tid
    return generate_trace_id()

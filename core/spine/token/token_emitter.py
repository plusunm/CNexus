"""Token emission interceptor — bind tokens to spine events at write time."""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from core.spine.identity.store import get_identity_store
from core.spine.token.token_schema import classify_cost_level
from core.spine.token.token_store import append_token_event


def emit_token_event(
    trace_id: str,
    *,
    event_id: str | None = None,
    source: str,
    tokens_in: int,
    tokens_out: int,
    phase: str,
    spine_event_id: str | None = None,
    causal_edge_id: str | None = None,
    base_dir: str | None = None,
    mode: str = "",
    entry: str = "",
) -> dict[str, Any]:
    total = tokens_in + tokens_out
    identity_id = get_identity_store().identity_for_trace(trace_id)

    event = {
        "trace_id": trace_id,
        "event_id": event_id or str(uuid.uuid4()),
        "source": source,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "total": total,
        "spine_event_id": spine_event_id,
        "causal_edge_id": causal_edge_id,
        "identity_id": identity_id,
        "phase": phase,
        "timestamp": time.time(),
        "mode": mode,
        "entry": entry,
        "cost_level": classify_cost_level(total, avg=max(total, 1)),
    }
    append_token_event(event, base_dir=base_dir)
    return event

"""Incremental narrative lines for streaming frames."""

from __future__ import annotations

from typing import Any, Optional


class StreamingNarrativeEngine:
    def update(
        self,
        *,
        event: dict[str, Any],
        causal_delta: dict[str, Any],
        state_delta: dict[str, Any],
        control_delta: Optional[dict[str, Any]],
    ) -> str:
        if control_delta:
            return (
                f"[CONTROL] {control_delta.get('policy')} → {control_delta.get('decision')} "
                f"at {control_delta.get('event_id')}"
            )
        if state_delta.get("delta"):
            keys = ", ".join(str(k) for k in list(state_delta["delta"].keys())[:3])
            return f"[STATE] updated fields: {keys} at {event.get('event_id')}"
        added = causal_delta.get("added_edges") or []
        if added:
            edge = added[0]
            return f"[CAUSE] linked {edge[0]} → {edge[1]}"
        etype = str(event.get("event_type") or "event")
        return f"[EVENT] {etype} {event.get('event_id')}"

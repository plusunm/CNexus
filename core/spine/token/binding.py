"""Token → Execution binding — map token events onto spine graph."""

from __future__ import annotations

from typing import Any

from core.spine.query.engine import query_by_trace
from core.spine.query.subgraph import build_subgraph


def find_closest_event(events: list[dict[str, Any]], event_id: str | None = None) -> dict[str, Any] | None:
    if not events:
        return None
    if event_id:
        for e in events:
            if str(e.get("event_id") or "") == event_id:
                return e
    return events[-1]


def find_edge(subgraph: dict[str, Any], event: dict[str, Any] | None) -> str | None:
    if not event:
        return None
    eid = str(event.get("event_id") or "")
    for edge in subgraph.get("edges") or []:
        if str(edge.get("to") or "") == eid:
            return str(edge.get("from") or "") + "->" + eid
    edges = subgraph.get("edges") or []
    if edges:
        last = edges[-1]
        return f"{last.get('from')}->{last.get('to')}"
    return None


def bind_tokens_to_execution(
    trace_id: str,
    token_events: list[dict[str, Any]],
    *,
    base_dir: str,
) -> list[dict[str, Any]]:
    """Bind token events to spine events and causal edges."""
    events = query_by_trace(base_dir, trace_id, limit=5000)
    subgraph = build_subgraph(events)
    bound: list[dict[str, Any]] = []

    for t in token_events:
        row = dict(t)
        if not row.get("spine_event_id"):
            closest = find_closest_event(events, row.get("event_id"))
            if closest:
                row["spine_event_id"] = closest.get("event_id")
        if not row.get("causal_edge_id"):
            spine_eid = row.get("spine_event_id")
            spine_event = find_closest_event(events, spine_eid)
            row["causal_edge_id"] = find_edge(subgraph, spine_event)
        bound.append(row)
    return bound


class TokenExecutionBinder:
    """Minimal binder for spine_event ↔ llm_trace pairing."""

    def bind(self, spine_event: dict[str, Any], llm_trace: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_id": spine_event.get("event_id"),
            "token_cost": {
                "input_tokens": int(llm_trace.get("input_tokens") or llm_trace.get("tokens_in") or 0),
                "output_tokens": int(llm_trace.get("output_tokens") or llm_trace.get("tokens_out") or 0),
                "total": int(llm_trace.get("total_tokens") or llm_trace.get("total") or 0),
            },
            "execution_phase": spine_event.get("event_type"),
            "trace_id": spine_event.get("trace_id"),
        }

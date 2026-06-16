"""Token layer service — observatory, trace field, influence overlay."""

from __future__ import annotations

import time
from typing import Any

from core.spine.cost.gravity_field import TokenCostGravityField
from core.spine.identity.store import get_identity_store
from core.spine.query.engine import query_by_trace
from core.spine.query.index import TraceIndex
from core.spine.query.subgraph import build_subgraph
from core.spine.storage import SpineEventLog
from core.spine.token.binding import bind_tokens_to_execution
from core.spine.token.influence.causal_overlay import build_influence_overlay
from core.spine.token.influence.edge_reweight import reweight_causal_edges
from core.spine.token.token_schema import (
    TokenTraceSummary,
    classify_cost_level,
    estimate_tokens_from_event,
    infer_phase_from_event,
    infer_source_from_event,
)
from core.spine.token.token_store import configure_token_store, read_all_tokens, read_tokens


def _synthesize_from_spine(base_dir: str, trace_id: str) -> list[dict[str, Any]]:
    """Derive token events from spine rows when no explicit token log exists."""
    events = query_by_trace(base_dir, trace_id, limit=5000)
    rows: list[dict[str, Any]] = []
    for event in events:
        tin, tout = estimate_tokens_from_event(event)
        total = tin + tout
        rows.append({
            "trace_id": trace_id,
            "event_id": str(event.get("event_id") or ""),
            "source": infer_source_from_event(event),
            "tokens_in": tin,
            "tokens_out": tout,
            "total": total,
            "spine_event_id": event.get("event_id"),
            "phase": infer_phase_from_event(event),
            "timestamp": _parse_ts(event),
            "mode": str(event.get("event_type") or ""),
            "entry": str(event.get("entry") or event.get("summary") or ""),
            "identity_id": get_identity_store().identity_for_trace(trace_id),
        })
    return rows


def _parse_ts(event: dict[str, Any]) -> float:
    ts = event.get("timestamp") or event.get("ts")
    if isinstance(ts, (int, float)):
        return float(ts)
    return time.time()


def _resolve_token_events(base_dir: str, trace_id: str) -> list[dict[str, Any]]:
    configure_token_store(base_dir)
    stored = read_tokens(trace_id, base_dir=base_dir)
    if stored:
        return bind_tokens_to_execution(trace_id, stored, base_dir=base_dir)
    synthesized = _synthesize_from_spine(base_dir, trace_id)
    return bind_tokens_to_execution(trace_id, synthesized, base_dir=base_dir)


def build_trace_token_report(base_dir: str, trace_id: str) -> dict[str, Any]:
    """Full token report: gravity field + bindings + influence overlay."""
    events = query_by_trace(base_dir, trace_id, limit=5000)
    token_events = _resolve_token_events(base_dir, trace_id)
    gravity = TokenCostGravityField().build(events, token_events)
    subgraph = build_subgraph(events)
    reweighted = reweight_causal_edges(subgraph, gravity["field"])
    influence = build_influence_overlay(reweighted)

    identity_id = get_identity_store().identity_for_trace(trace_id)
    total = int(gravity.get("total_cost") or 0)

    return {
        "trace_id": trace_id,
        "total_tokens": total,
        "total_cost": total,
        "by_phase": gravity.get("by_phase") or {},
        "bindings": gravity.get("bindings") or [],
        "field": gravity.get("field") or {},
        "gradient": gravity.get("gradient") or {},
        "token_events": token_events,
        "causal": reweighted,
        "influence": influence,
        "identity_id": identity_id,
    }


def build_token_observatory(base_dir: str, *, limit: int = 100) -> list[dict[str, Any]]:
    """Aggregate token traces for Token Observatory view."""
    configure_token_store(base_dir)
    rows = SpineEventLog(base_dir).read_all()
    trace_ids = TraceIndex(rows).trace_ids()[:limit]

    summaries: list[TokenTraceSummary] = []
    for trace_id in trace_ids:
        token_events = _resolve_token_events(base_dir, trace_id)
        if not token_events:
            continue
        tin = sum(int(t.get("tokens_in") or 0) for t in token_events)
        tout = sum(int(t.get("tokens_out") or 0) for t in token_events)
        total = sum(int(t.get("total") or 0) for t in token_events)
        mode = token_events[0].get("mode") or token_events[0].get("source") or "unknown"
        entry = str(token_events[0].get("entry") or "")
        summaries.append(
            TokenTraceSummary(
                trace_id=trace_id,
                tokens_in=tin,
                tokens_out=tout,
                total=total,
                mode=str(mode),
                cost_level="mid",
                entry=entry,
                event_count=len(token_events),
            )
        )

    if not summaries:
        stored = read_all_tokens(base_dir=base_dir)
        by_trace: dict[str, list[dict[str, Any]]] = {}
        for row in stored:
            tid = str(row.get("trace_id") or "")
            if tid:
                by_trace.setdefault(tid, []).append(row)
        for trace_id, events in by_trace.items():
            tin = sum(int(t.get("tokens_in") or 0) for t in events)
            tout = sum(int(t.get("tokens_out") or 0) for t in events)
            total = sum(int(t.get("total") or 0) for t in events)
            summaries.append(
                TokenTraceSummary(
                    trace_id=trace_id,
                    tokens_in=tin,
                    tokens_out=tout,
                    total=total,
                    mode=str(events[0].get("mode") or events[0].get("source") or "unknown"),
                    cost_level="mid",
                    entry=str(events[0].get("entry") or ""),
                    event_count=len(events),
                )
            )

    if not summaries:
        return []

    avg = sum(s.total for s in summaries) / len(summaries)
    result: list[dict[str, Any]] = []
    for s in summaries:
        s.cost_level = classify_cost_level(s.total, avg=avg)
        result.append(s.to_dict())
    return sorted(result, key=lambda x: -int(x.get("total") or 0))

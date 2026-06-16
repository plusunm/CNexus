"""Spine Query Engine v1 — filter, edges, control, state extraction."""

from __future__ import annotations

from typing import Any

from core.spine.query.index import TraceIndex
from core.spine.storage import SpineEventLog


def load_spine_rows(base_dir: str) -> list[dict[str, Any]]:
    return SpineEventLog(base_dir).read_all()


def query_by_trace(base_dir: str, trace_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
    rows = load_spine_rows(base_dir)
    return TraceIndex(rows).events_for(trace_id, limit=limit)


def build_edges(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        parent = event.get("parent_event_id")
        child = event.get("event_id")
        if not parent or not child:
            continue
        key = (str(parent), str(child))
        if key in seen:
            continue
        seen.add(key)
        edges.append({"from": key[0], "to": key[1], "kind": "parent"})
    return edges


def extract_control(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    control: list[dict[str, Any]] = []
    for event in events:
        decision = event.get("decision")
        is_control = str(event.get("event_type") or "") == "control"
        if not decision and not is_control:
            continue
        control.append(
            {
                "event_id": event.get("event_id"),
                "decision": decision,
                "caller": event.get("caller"),
                "entry": event.get("entry"),
                "summary": event.get("summary"),
                "hard_gate": bool(event.get("hard_gate")),
            }
        )
    return control


def extract_state(events: list[dict[str, Any]]) -> dict[str, Any]:
    deltas: list[dict[str, Any]] = []
    patches: list[dict[str, Any]] = []
    for event in events:
        delta = event.get("state_delta")
        if not delta:
            continue
        entry = {"event_id": event.get("event_id"), "delta": delta}
        deltas.append(entry)
        if str(event.get("event_type") or "") == "state" or delta.get("changes"):
            patches.append(entry)
    return {"deltas": deltas, "patches": patches}

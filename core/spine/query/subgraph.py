"""Causal subgraph builder — nodes + parent edges from spine events."""

from __future__ import annotations

from typing import Any

from core.spine.query.causal_index import CausalIndex


def build_subgraph(events: list[dict[str, Any]]) -> dict[str, Any]:
    index = CausalIndex()
    index.build(events)

    nodes_map: dict[str, dict[str, Any]] = {}
    for event in events:
        eid = event.get("event_id")
        if eid:
            nodes_map[str(eid)] = event

    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        eid = event.get("event_id")
        parent = event.get("parent_event_id")
        if not eid or not parent:
            continue
        key = (str(parent), str(eid))
        if key in seen:
            continue
        seen.add(key)
        edges.append({"from": key[0], "to": key[1], "kind": "parent"})

    return {
        "nodes": list(nodes_map.values()),
        "edges": edges,
    }


def find_root_cause_summary(
    events: list[dict[str, Any]],
    index: CausalIndex,
) -> dict[str, Any]:
    event_ids = [str(e["event_id"]) for e in events if e.get("event_id")]
    roots = index.root_event_ids(events)
    chains: list[dict[str, Any]] = []
    for eid in event_ids:
        up = index.trace_up(eid)
        if up:
            chains.append(
                {
                    "event_id": eid,
                    "root_chain": up,
                    "root_cause": up[-1],
                }
            )
    return {
        "roots": roots,
        "chains": chains,
    }

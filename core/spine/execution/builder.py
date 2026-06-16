"""Build execution DAG from spine events."""

from __future__ import annotations

from typing import Any

from core.spine.execution.index import ExecutionIndex
from core.spine.execution.semantics import classify_event_phase, semantic_edge_to_execution_kind
from core.spine.execution.types import ExecutionEdge, ExecutionGraph, ExecutionNode


def _parse_ts(event: dict[str, Any]) -> str:
    return str(event.get("timestamp") or "")


def ingest_events(index: ExecutionIndex, events: list[dict[str, Any]], trace_id: str) -> None:
    ordered = sorted(events, key=_parse_ts)
    for event in ordered:
        eid = str(event.get("event_id") or "")
        if not eid:
            continue
        index.ingest(
            ExecutionNode(
                event_id=eid,
                trace_id=str(event.get("trace_id") or trace_id),
                phase=classify_event_phase(event),
                event_type=str(event.get("event_type") or ""),
                entry=str(event.get("entry") or "") or None,
                actor=str(event.get("caller") or event.get("subsystem") or "") or None,
                timestamp=str(event.get("timestamp") or "") or None,
                summary=str(event.get("summary") or "") or None,
                payload=event.get("payload") if isinstance(event.get("payload"), dict) else None,
            )
        )


def _edges_from_semantic(events: list[dict[str, Any]]) -> list[ExecutionEdge]:
    seen: set[tuple[str, str, str]] = set()
    edges: list[ExecutionEdge] = []
    for event in events:
        to_id = str(event.get("event_id") or "")
        for row in event.get("causal_edges") or []:
            if not isinstance(row, dict):
                continue
            frm = str(row.get("from") or "")
            relation = str(row.get("relation") or "temporal")
            to = str(row.get("to") or to_id)
            if not frm or not to:
                continue
            kind = semantic_edge_to_execution_kind(relation)
            key = (frm, to, kind)
            if key in seen:
                continue
            seen.add(key)
            edges.append(ExecutionEdge(from_id=frm, to_id=to, kind=kind, relation=relation))
    return edges


def _edges_from_phase_chain(nodes: list[ExecutionNode]) -> list[ExecutionEdge]:
    """Fallback: link consecutive phases trigger→control→execution→mutation→state."""
    edges: list[ExecutionEdge] = []
    last_by_phase: dict[str, str] = {}

    phase_flow = [
        ("trigger", "control", "triggers"),
        ("control", "execution", "controls"),
        ("execution", "mutation", "executes"),
        ("mutation", "state", "mutates"),
        ("execution", "state", "observes"),
    ]

    for node in nodes:
        last_by_phase[node.phase] = node.event_id
        for src_phase, dst_phase, kind in phase_flow:
            src_id = last_by_phase.get(src_phase)
            if src_id and node.phase == dst_phase and src_id != node.event_id:
                edges.append(
                    ExecutionEdge(from_id=src_id, to_id=node.event_id, kind=kind)
                )
    return edges


def build_execution_graph(trace_id: str, events: list[dict[str, Any]]) -> ExecutionGraph:
    index = ExecutionIndex()
    ingest_events(index, events, trace_id)
    nodes = sorted(index.get_trace(trace_id), key=lambda n: n.timestamp or "")

    semantic_edges = _edges_from_semantic(events)
    if semantic_edges:
        edges = semantic_edges
    else:
        edges = _edges_from_phase_chain(nodes)

    roots: list[str] = []
    if nodes:
        child_targets = {e.to_id for e in edges}
        roots = [n.event_id for n in nodes if n.event_id not in child_targets]
        if not roots:
            roots = [nodes[0].event_id]

    return ExecutionGraph(
        trace_id=trace_id,
        nodes=nodes,
        edges=edges,
        root_events=roots,
    )

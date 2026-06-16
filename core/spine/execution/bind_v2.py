"""Explain ↔ Execution binding v2 — phase-aligned path + drift overlay."""

from __future__ import annotations

from typing import Any

from core.spine.execution.bind import bind_explanation_to_execution
from core.spine.execution.builder import build_execution_graph
from core.spine.execution.graph import execution_path_to_event_ids
from core.spine.execution.semantics import classify_event_phase
from core.spine.execution.types import ExecutionGraph

BIND_VERSION = "execution-bind-v2"


def bind_explanation_to_execution_v2(
    explanation: dict[str, Any],
    graph: ExecutionGraph,
    events: list[dict[str, Any]],
    *,
    fusion_v2: dict[str, Any] | None = None,
    drift_summary: dict[str, Any] | None = None,
    focus_event_id: str | None = None,
) -> dict[str, Any]:
    bound = bind_explanation_to_execution(
        explanation,
        graph,
        focus_event_id=focus_event_id,
    )
    if not graph.nodes:
        bound["execution_v2"] = {
            "version": BIND_VERSION,
            "path_frames": [],
            "drift_summary": drift_summary,
        }
        return bound

    by_id = {str(e.get("event_id") or ""): e for e in events if e.get("event_id")}
    node_by_id = {n.event_id: n for n in graph.nodes}
    leaf = focus_event_id or graph.nodes[-1].event_id
    path_ids = bound.get("execution_path") or execution_path_to_event_ids(graph, leaf)

    path_frames: list[dict[str, Any]] = []
    for eid in path_ids:
        ev = by_id.get(eid, {})
        node = node_by_id.get(eid)
        path_frames.append(
            {
                "event_id": eid,
                "phase": node.phase if node else classify_event_phase(ev),
                "event_type": (node.event_type if node else ev.get("event_type")) or "unknown",
                "summary": (node.summary if node else ev.get("summary")) or "",
                "drift_status": ev.get("drift_status", "OK"),
                "confidence": ev.get("confidence", 0.95),
            }
        )

    fusion_ex = (fusion_v2 or {}).get("explanation") or {}
    bound["execution_v2"] = {
        "version": BIND_VERSION,
        "path_frames": path_frames,
        "path_event_ids": path_ids,
        "drift_summary": drift_summary,
        "fusion_summary": fusion_ex.get("summary"),
        "causal_story": fusion_ex.get("causal_story"),
        "state_story": fusion_ex.get("state_story"),
        "control_story": fusion_ex.get("control_story"),
    }
    return bound


def build_frame_execution_bind(
    trace_id: str,
    events: list[dict[str, Any]],
    focus_event_id: str,
) -> dict[str, Any]:
    """Incremental bind slice for live explain stream frames."""
    graph = build_execution_graph(trace_id, events)
    path_ids = execution_path_to_event_ids(graph, focus_event_id)
    by_id = {str(e.get("event_id") or ""): e for e in events}
    node_by_id = {n.event_id: n for n in graph.nodes}
    frames = []
    for eid in path_ids:
        ev = by_id.get(eid, {})
        node = node_by_id.get(eid)
        frames.append(
            {
                "event_id": eid,
                "phase": node.phase if node else classify_event_phase(ev),
                "event_type": (node.event_type if node else ev.get("event_type")) or "unknown",
                "drift_status": ev.get("drift_status", "OK"),
            }
        )
    return {
        "version": BIND_VERSION,
        "execution_path": path_ids,
        "path_frames": frames,
    }

"""Attach execution layer to query responses + explain binding."""

from __future__ import annotations

from typing import Any

from core.spine.execution.builder import build_execution_graph
from core.spine.execution.graph import execution_path_to_event_ids
from core.spine.execution.types import ExecutionGraph


def attach_execution_layer(
    response: dict[str, Any],
    *,
    trace_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    graph = build_execution_graph(trace_id, events)
    response["execution"] = graph.to_dict()
    return response


def bind_explanation_to_execution(
    explanation: dict[str, Any],
    graph: ExecutionGraph,
    *,
    focus_event_id: str | None = None,
) -> dict[str, Any]:
    """Augment static explanation with execution path (CP-2.5 bind layer v1)."""
    if not graph.nodes:
        return explanation

    leaf = focus_event_id or graph.nodes[-1].event_id
    path_ids = execution_path_to_event_ids(graph, leaf)
    by_id = {n.event_id: n for n in graph.nodes}

    path_labels = [
        f"{by_id[eid].phase}:{by_id[eid].event_type}({eid[:8]})"
        for eid in path_ids
        if eid in by_id
    ]

    bound = dict(explanation)
    bound["execution_path"] = path_ids
    bound["execution_path_labels"] = path_labels
    if path_labels:
        bound["execution_narrative"] = " → ".join(path_labels)
    return bound


def build_execution_layer_dict(trace_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    return build_execution_graph(trace_id, events).to_dict()

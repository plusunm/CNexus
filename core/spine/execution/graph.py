"""Execution graph helpers."""

from __future__ import annotations

from core.spine.execution.types import ExecutionGraph


def execution_path_to_event_ids(graph: ExecutionGraph, leaf_event_id: str) -> list[str]:
    """Walk incoming edges from leaf toward roots."""
    incoming: dict[str, list[str]] = {}
    for edge in graph.edges:
        incoming.setdefault(edge.to_id, []).append(edge.from_id)

    path: list[str] = [leaf_event_id]
    cur = leaf_event_id
    seen: set[str] = set()
    while cur in incoming and incoming[cur]:
        parent = incoming[cur][0]
        if parent in seen:
            break
        seen.add(parent)
        path.insert(0, parent)
        cur = parent
    return path

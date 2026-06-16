"""Execution bundle assembly for identity computation."""

from __future__ import annotations

from typing import Any

from core.spine.execution.builder import build_execution_graph
from core.spine.execution.types import ExecutionGraph


def build_execution_bundle(
    trace_id: str,
    events: list[dict[str, Any]],
    *,
    control: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = execution if execution and execution.get("nodes") else build_execution_graph(trace_id, events).to_dict()
    return {
        "trace_id": trace_id,
        "graph": graph,
        "state": state or {},
        "control": control or [],
        "events": events,
    }

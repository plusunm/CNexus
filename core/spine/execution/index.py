"""Execution index — trace-scoped semantic node registry."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from core.spine.execution.types import ExecutionNode


class ExecutionIndex:
    def __init__(self) -> None:
        self.by_trace: dict[str, list[ExecutionNode]] = defaultdict(list)
        self.by_event: dict[str, ExecutionNode] = {}

    def ingest(self, node: ExecutionNode) -> None:
        if node.event_id in self.by_event:
            return
        self.by_trace[node.trace_id].append(node)
        self.by_event[node.event_id] = node

    def get_trace(self, trace_id: str) -> list[ExecutionNode]:
        return list(self.by_trace.get(trace_id, []))

    def get(self, event_id: str) -> Optional[ExecutionNode]:
        return self.by_event.get(event_id)

    def clear(self) -> None:
        self.by_trace.clear()
        self.by_event.clear()

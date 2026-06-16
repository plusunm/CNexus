"""Incremental causal builder for streaming explanation."""

from __future__ import annotations

from typing import Any


class IncrementalCausalBuilder:
    def __init__(self) -> None:
        self.graph: dict[str, list[str]] = {}

    def update(self, event: dict[str, Any]) -> dict[str, Any]:
        eid = str(event.get("event_id") or "")
        parent = event.get("parent_event_id")
        added: list[list[str]] = []
        if parent and eid:
            parent_s = str(parent)
            self.graph.setdefault(parent_s, [])
            if eid not in self.graph[parent_s]:
                self.graph[parent_s].append(eid)
                added.append([parent_s, eid])
        return {"added_edges": added, "graph_size": sum(len(v) for v in self.graph.values())}

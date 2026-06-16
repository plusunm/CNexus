"""Structural parent index over spine events (v1 — not semantic causal inference)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class CausalIndex:
    """parent_event_id → children; reverse lookup for root-cause walks."""

    def __init__(self) -> None:
        self.children_map: dict[str, list[str]] = defaultdict(list)
        self.parent_map: dict[str, str] = {}

    def build(self, events: list[dict[str, Any]]) -> None:
        self.children_map.clear()
        self.parent_map.clear()
        for event in events:
            eid = event.get("event_id")
            parent = event.get("parent_event_id")
            if not eid or not parent:
                continue
            eid_s = str(eid)
            parent_s = str(parent)
            if eid_s not in self.children_map[parent_s]:
                self.children_map[parent_s].append(eid_s)
            self.parent_map[eid_s] = parent_s

    def trace_up(self, event_id: str) -> list[str]:
        chain: list[str] = []
        cur = str(event_id)
        while cur in self.parent_map:
            parent = self.parent_map[cur]
            chain.append(parent)
            cur = parent
        return chain

    def trace_down(self, event_id: str) -> list[str]:
        return list(self.children_map.get(str(event_id), []))

    def root_event_ids(self, events: list[dict[str, Any]]) -> list[str]:
        ids = {str(e["event_id"]) for e in events if e.get("event_id")}
        roots = [eid for eid in ids if self.parent_map.get(eid) not in ids]
        if roots:
            return sorted(roots)
        return sorted(eid for e in ids if eid not in self.parent_map)

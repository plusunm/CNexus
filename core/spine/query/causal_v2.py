"""Semantic causal edges v2 — beyond parent_event_id temporal structure."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

CausalRelation = Literal["temporal", "triggered_by", "control_flow"]


class SemanticCausalIndex:
    """Index causal_edges on spine events (v2 semantic graph)."""

    def __init__(self) -> None:
        self.edges: list[dict[str, Any]] = []
        self.by_relation: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def build(self, events: list[dict[str, Any]]) -> None:
        self.edges.clear()
        self.by_relation.clear()
        self.outgoing.clear()
        self.incoming.clear()

        seen: set[tuple[str, str, str]] = set()
        for event in events:
            eid = str(event.get("event_id") or "")
            for edge in event.get("causal_edges") or []:
                if not isinstance(edge, dict):
                    continue
                frm = str(edge.get("from") or "")
                to = str(edge.get("to") or eid)
                relation = str(edge.get("relation") or "temporal")
                key = (frm, to, relation)
                if not frm or not to or key in seen:
                    continue
                seen.add(key)
                row = {"from": frm, "to": to, "relation": relation}
                self.edges.append(row)
                self.by_relation[relation].append(row)
                self.outgoing[frm].append(row)
                self.incoming[to].append(row)

            parent = event.get("parent_event_id")
            if parent and eid:
                key = (str(parent), eid, "temporal")
                if key not in seen:
                    seen.add(key)
                    row = {"from": str(parent), "to": eid, "relation": "temporal"}
                    self.edges.append(row)
                    self.by_relation["temporal"].append(row)
                    self.outgoing[str(parent)].append(row)
                    self.incoming[eid].append(row)

    def trigger_chains(self, event_id: str) -> list[str]:
        chain: list[str] = []
        cur = str(event_id)
        while True:
            triggers = [
                e["from"]
                for e in self.incoming.get(cur, [])
                if e.get("relation") == "triggered_by"
            ]
            if not triggers:
                break
            parent = str(triggers[0])
            chain.append(parent)
            cur = parent
        return chain

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_version": "v2",
            "edge_count": len(self.edges),
            "edges": self.edges,
            "by_relation": {k: len(v) for k, v in self.by_relation.items()},
        }

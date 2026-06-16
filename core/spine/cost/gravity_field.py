"""Token Cost Gravity Field v1 — retrospective cost accumulation over execution graph."""

from __future__ import annotations

from typing import Any


class TokenCostGravityField:
    """Compute per-node cost field and edge gradients from bound token events."""

    def build(self, events: list[dict[str, Any]], token_events: list[dict[str, Any]]) -> dict[str, Any]:
        graph = self._build_graph(events)
        per_event_cost = self._event_costs(token_events)

        field: dict[str, float] = {}
        for node_id in graph:
            field[node_id] = self._accumulate_cost(node_id, graph, per_event_cost)

        gradient = self._compute_gradient(graph, field)
        total_cost = sum(per_event_cost.values())

        return {
            "field": field,
            "gradient": gradient,
            "total_cost": total_cost,
            "by_phase": self._by_phase(token_events),
            "bindings": self._bindings(token_events),
        }

    def _event_costs(self, token_events: list[dict[str, Any]]) -> dict[str, float]:
        costs: dict[str, float] = {}
        for t in token_events:
            spine_id = str(t.get("spine_event_id") or t.get("event_id") or "")
            if not spine_id:
                continue
            costs[spine_id] = costs.get(spine_id, 0.0) + float(t.get("total") or 0)
        return costs

    def _build_graph(self, events: list[dict[str, Any]]) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {}
        for event in events:
            eid = str(event.get("event_id") or "")
            parent = str(event.get("parent_event_id") or "")
            if not eid:
                continue
            graph.setdefault(eid, [])
            if parent:
                graph.setdefault(parent, []).append(eid)
        return graph

    def _accumulate_cost(
        self,
        node_id: str,
        graph: dict[str, list[str]],
        per_event_cost: dict[str, float],
    ) -> float:
        direct = per_event_cost.get(node_id, 0.0)
        children = graph.get(node_id, [])
        subtree = sum(self._accumulate_cost(c, graph, per_event_cost) for c in children)
        return direct + subtree

    def _compute_gradient(
        self,
        graph: dict[str, list[str]],
        field: dict[str, float],
    ) -> dict[str, float]:
        gradient: dict[str, float] = {}
        for parent, children in graph.items():
            parent_cost = field.get(parent, 0.0)
            for child in children:
                child_cost = field.get(child, 0.0)
                gradient[child] = round(child_cost - parent_cost, 2)
        return gradient

    def _by_phase(self, token_events: list[dict[str, Any]]) -> dict[str, int]:
        phases: dict[str, int] = {}
        for t in token_events:
            phase = str(t.get("phase") or "EXEC")
            phases[phase] = phases.get(phase, 0) + int(t.get("total") or 0)
        return phases

    def _bindings(self, token_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        agg: dict[str, int] = {}
        for t in token_events:
            spine_id = str(t.get("spine_event_id") or "")
            if not spine_id:
                continue
            agg[spine_id] = agg.get(spine_id, 0) + int(t.get("total") or 0)
        return [{"spine_event_id": k, "tokens": v} for k, v in sorted(agg.items(), key=lambda x: -x[1])]

"""Causal + state + control fusion reasoner (structured, no LLM)."""

from __future__ import annotations

from typing import Any

from core.spine.explain_v2.control_index import ControlIndex
from core.spine.explain_v2.state_index import StateIndex
from core.spine.query.causal_index import CausalIndex


class CausalStateFusionEngine:
    def build(
        self,
        events: list[dict[str, Any]],
        *,
        causal_index: CausalIndex,
        state_index: StateIndex,
        control_index: ControlIndex,
    ) -> dict[str, Any]:
        causal_chain = self._build_causal_chain(events, causal_index)
        state_transitions = self._align_state(causal_chain, state_index)
        control_flow = self._map_control(events, control_index)
        return {
            "causal_chain": causal_chain,
            "state_transitions": state_transitions,
            "control_flow": control_flow,
        }

    @staticmethod
    def _build_causal_chain(events: list[dict[str, Any]], index: CausalIndex) -> list[dict[str, Any]]:
        chain: list[dict[str, Any]] = []
        for event in events:
            eid = event.get("event_id")
            if not eid:
                continue
            eid_s = str(eid)
            caused = index.trace_down(eid_s)
            chain.append(
                {
                    "event_id": eid_s,
                    "type": str(event.get("event_type") or "event"),
                    "summary": str(event.get("summary") or ""),
                    "caused": caused,
                    "parent_event_id": event.get("parent_event_id"),
                }
            )
        return chain

    @staticmethod
    def _align_state(
        causal_chain: list[dict[str, Any]],
        state_index: StateIndex,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for node in causal_chain:
            eid = str(node["event_id"])
            if eid in seen:
                continue
            before = state_index.get_before(eid)
            after = state_index.get_after(eid)
            delta = state_index.get_delta(eid)
            if not before and not after and not delta:
                continue
            seen.add(eid)
            rows.append(
                {
                    "event_id": eid,
                    "before": before,
                    "after": after,
                    "delta": delta,
                }
            )
        for row in state_index.transitions():
            eid = str(row["event_id"])
            if eid not in seen:
                rows.append(row)
        return rows

    @staticmethod
    def _map_control(events: list[dict[str, Any]], control_index: ControlIndex) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for event in events:
            eid = event.get("event_id")
            if not eid:
                continue
            meta = control_index.get(str(eid))
            if not meta:
                continue
            rows.append({"event_id": str(eid), **meta})
        return rows

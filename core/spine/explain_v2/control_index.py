"""Build control attribution index from spine events."""

from __future__ import annotations

from typing import Any


class ControlIndex:
    def __init__(self) -> None:
        self._by_event: dict[str, dict[str, Any]] = {}

    def build(self, events: list[dict[str, Any]]) -> None:
        self._by_event.clear()
        for event in events:
            eid = event.get("event_id")
            if not eid:
                continue
            decision = event.get("decision")
            if not decision and str(event.get("event_type") or "") != "control":
                continue
            entry = str(event.get("entry") or "")
            reason = str(event.get("summary") or "")
            policy = entry or "unknown_policy"
            if "legacy" in entry.lower() or "LEGACY" in reason.upper():
                policy = "legacy_api"
            self._by_event[str(eid)] = {
                "decision": decision,
                "policy": policy,
                "caller": event.get("caller"),
                "entry": entry,
                "hard_gate": bool(event.get("hard_gate")),
            }

    def get(self, event_id: str) -> dict[str, Any]:
        return dict(self._by_event.get(str(event_id), {}))

    def all_entries(self) -> list[dict[str, Any]]:
        return [{"event_id": eid, **meta} for eid, meta in self._by_event.items()]

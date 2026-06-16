"""State timeline engine — event_i → state_i projection chain (CP-2.5)."""

from __future__ import annotations

from typing import Any


class StateTimelineEngine:
    """
    Build a chronological state trajectory from spine state events.
    Not a diff-only view — each step is a full Tier-A projection snapshot.
    """

    def __init__(self) -> None:
        self.timeline: list[dict[str, Any]] = []
        self._projection: dict[str, Any] = {}

    def build(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.timeline.clear()
        self._projection = {}

        state_events = [
            e
            for e in events
            if str(e.get("event_type") or "") in ("state", "state_patch")
            or e.get("state_delta")
        ]
        state_events.sort(key=lambda e: str(e.get("timestamp") or ""))

        for event in state_events:
            before = dict(self._projection)
            raw = event.get("state_delta") or {}
            self._apply_delta(raw)
            step = {
                "event_id": event.get("event_id"),
                "timestamp": event.get("timestamp"),
                "event_type": event.get("event_type"),
                "mutation_label": raw.get("mutation_label"),
                "before": before,
                "after": dict(self._projection),
                "delta": raw.get("changes") or [],
                "change_count": raw.get("change_count", 0),
            }
            self.timeline.append(step)

        return list(self.timeline)

    def _apply_delta(self, raw: dict[str, Any]) -> None:
        changes = raw.get("changes")
        if isinstance(changes, list):
            for change in changes:
                if not isinstance(change, dict):
                    continue
                field = str(change.get("field") or "")
                if field:
                    self._projection[field] = change.get("after")
        stores = raw.get("stores")
        if isinstance(stores, dict):
            self._projection["stores"] = stores

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": "state-timeline-v1",
            "step_count": len(self.timeline),
            "timeline": self.timeline,
            "latest_projection": dict(self._projection),
        }

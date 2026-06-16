"""State transition index from spine state_delta rows."""

from __future__ import annotations

from typing import Any


def _changes_to_before_after(changes: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    delta: dict[str, Any] = {}
    for change in changes:
        field = str(change.get("field") or "unknown")
        b_val = change.get("before")
        a_val = change.get("after")
        before[field] = b_val
        after[field] = a_val
        if isinstance(b_val, (int, float)) and isinstance(a_val, (int, float)):
            delta[field] = round(a_val - b_val, 6)
        else:
            delta[field] = {"before": b_val, "after": a_val}
    return before, after, delta


class StateIndex:
    """Query-time state index — before/after derived from state spine rows."""

    def __init__(self) -> None:
        self._before: dict[str, dict[str, Any]] = {}
        self._after: dict[str, dict[str, Any]] = {}
        self._delta: dict[str, dict[str, Any]] = {}

    def build(self, events: list[dict[str, Any]]) -> None:
        self._before.clear()
        self._after.clear()
        self._delta.clear()
        for event in events:
            eid = event.get("event_id")
            if not eid:
                continue
            raw = event.get("state_delta")
            if not isinstance(raw, dict):
                continue
            changes = raw.get("changes")
            if isinstance(changes, list) and changes:
                before, after, delta = _changes_to_before_after(changes)
                self._before[str(eid)] = before
                self._after[str(eid)] = after
                self._delta[str(eid)] = delta
            elif raw.get("stores"):
                stores = raw.get("stores")
                self._after[str(eid)] = {"stores": stores}
                self._delta[str(eid)] = {"stores": stores}

    def get_before(self, event_id: str) -> dict[str, Any]:
        return dict(self._before.get(str(event_id), {}))

    def get_after(self, event_id: str) -> dict[str, Any]:
        return dict(self._after.get(str(event_id), {}))

    def get_delta(self, event_id: str) -> dict[str, Any]:
        return dict(self._delta.get(str(event_id), {}))

    def transitions(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for eid in sorted(set(self._before) | set(self._after) | set(self._delta)):
            rows.append(
                {
                    "event_id": eid,
                    "before": self.get_before(eid),
                    "after": self.get_after(eid),
                    "delta": self.get_delta(eid),
                }
            )
        return rows

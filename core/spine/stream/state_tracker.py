"""Live state projection tracker."""

from __future__ import annotations

from typing import Any


class LiveStateDiffTracker:
    def __init__(self) -> None:
        self._projection: dict[str, Any] = {}

    def update(self, event: dict[str, Any]) -> dict[str, Any]:
        before = dict(self._projection)
        raw = event.get("state_delta")
        if isinstance(raw, dict):
            changes = raw.get("changes")
            if isinstance(changes, list):
                for change in changes:
                    field = str(change.get("field") or "")
                    if field:
                        self._projection[field] = change.get("after")
            elif raw.get("stores"):
                self._projection["stores"] = raw.get("stores")
        delta = {k: self._projection[k] for k in self._projection if before.get(k) != self._projection[k]}
        return {"before": before, "after": dict(self._projection), "delta": delta}

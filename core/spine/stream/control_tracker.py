"""Control attribution stream tracker."""

from __future__ import annotations

from typing import Any, Optional


class ControlAttributionStream:
    def update(self, event: dict[str, Any]) -> Optional[dict[str, Any]]:
        decision = event.get("decision")
        if not decision and str(event.get("event_type") or "") != "control":
            return None
        entry = str(event.get("entry") or "")
        policy = entry or "unknown_policy"
        if "legacy" in entry.lower():
            policy = "legacy_api"
        return {
            "event_id": event.get("event_id"),
            "decision": decision,
            "policy": policy,
        }

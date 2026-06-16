"""Self-Healing Spine — backfill suggestions and optional tap replay."""

from __future__ import annotations

import os
from typing import Any, Optional

from core.spine.drift.types import DriftItem, DriftReport
from core.spine.integration import get_spine_writer


def self_heal_enabled() -> bool:
    return os.environ.get("SPINE_SELF_HEAL", "0").strip().lower() in ("1", "true", "yes")


class SpineHealer:
    """Suggest and optionally apply spine repairs from runtime tap truth."""

    def suggest(
        self,
        drift: DriftReport,
        tap_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        tap_by_id = {str(e.get("event_id")): e for e in tap_events if e.get("event_id")}

        for item in drift.missing:
            tap_row = tap_by_id.get(item.event_id or "") if item.event_id else None
            if tap_row is None:
                for te in tap_events:
                    if te.get("type") == item.type and not te.get("spine_written"):
                        tap_row = te
                        break
            actions.append(
                {
                    "action": "backfill_spine",
                    "event_type": item.type,
                    "event_id": item.event_id,
                    "reason": item.reason,
                    "tap_available": tap_row is not None,
                    "auto_apply": False,
                }
            )

        for item in drift.extra:
            actions.append(
                {
                    "action": "review_extra_spine",
                    "event_type": item.type,
                    "event_id": item.event_id,
                    "reason": item.reason,
                }
            )

        for item in drift.mismatch:
            actions.append(
                {
                    "action": "reconcile_mismatch",
                    "event_type": item.type,
                    "event_id": item.event_id,
                    "reason": item.reason,
                }
            )

        if drift.spine_sync_status == "drifted":
            actions.append(
                {
                    "action": "enforce_trace",
                    "reason": "spine_sync_drifted",
                    "priority": "high",
                }
            )

        return actions

    def apply_backfill(
        self,
        trace_id: str,
        missing: list[DriftItem],
        tap_events: list[dict[str, Any]],
        *,
        apply: bool = False,
    ) -> dict[str, Any]:
        writer = get_spine_writer()
        if writer is None:
            return {"ok": False, "reason": "spine_writer_unregistered", "backfilled": 0}

        tap_by_id = {str(e.get("event_id")): e for e in tap_events if e.get("event_id")}
        candidates: list[dict[str, Any]] = []

        for item in missing:
            tap_row = tap_by_id.get(item.event_id or "")
            if tap_row is None:
                for te in tap_events:
                    if te.get("type") == item.type and not te.get("spine_written"):
                        tap_row = te
                        break
            if tap_row and not tap_row.get("spine_written"):
                candidates.append({"item": item, "tap": tap_row})

        if not apply:
            return {
                "ok": True,
                "dry_run": True,
                "would_backfill": len(candidates),
                "candidates": [
                    {
                        "event_type": c["tap"].get("type"),
                        "event_id": c["tap"].get("event_id"),
                        "summary": c["tap"].get("summary"),
                    }
                    for c in candidates
                ],
            }

        from core.spine.emit import emit_spine_event

        backfilled = 0
        for cand in candidates:
            tap = cand["tap"]
            etype = str(tap.get("type") or "unknown")
            summary = str(tap.get("summary") or f"heal-backfill · {etype}")
            payload = tap.get("payload") if isinstance(tap.get("payload"), dict) else {}
            payload = {**payload, "heal_backfill": True, "source": "self_healing_spine"}
            ev = emit_spine_event(
                event_type=etype,
                summary=summary,
                trace_id=trace_id,
                payload=payload,
                action="mutate" if tap.get("impact") == "state_update" else "read",
            )
            if ev:
                backfilled += 1

        return {"ok": True, "dry_run": False, "backfilled": backfilled}

    def heal_from_drift(
        self,
        drift: DriftReport,
        tap_events: list[dict[str, Any]],
        *,
        apply: Optional[bool] = None,
    ) -> dict[str, Any]:
        suggestions = self.suggest(drift, tap_events)
        do_apply = self_heal_enabled() if apply is None else apply
        backfill_result = self.apply_backfill(
            drift.trace_id,
            drift.missing,
            tap_events,
            apply=do_apply,
        )
        return {
            "suggestions": suggestions,
            "backfill": backfill_result,
            "self_heal_enabled": self_heal_enabled(),
        }

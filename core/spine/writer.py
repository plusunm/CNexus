"""Spine projection writer — GTBS → spine_events.jsonl with causal linking."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.types import AuditTransactionEvent
from core.spine.projector import project_control_decision, project_gtbs_row
from core.spine.storage import SpineEventLog
from core.spine.types import SpineEvent, SpineEventType


class SpineWriter:
    """
    Appends projected SpineEvents and maintains per-trace parent links in-process.
    """

    def __init__(self, log: SpineEventLog) -> None:
        self._log = log
        self._last_by_trace: dict[str, str] = {}
        self._trace_by_tx: dict[str, str] = {}
        self._seq = 0

    @classmethod
    def from_base_dir(cls, base_dir: str | Path) -> "SpineWriter":
        return cls(SpineEventLog(base_dir))

    @classmethod
    def from_gtbs_log(cls, gtbs_log: GTBSTransactionLog) -> "SpineWriter":
        base_dir = gtbs_log.path.parent.parent
        return cls.from_base_dir(base_dir)

    @property
    def path(self) -> Path:
        return self._log.path

    def _link_and_append(
        self,
        event: SpineEvent,
        *,
        triggered_by: Optional[str] = None,
        control_of: Optional[str] = None,
    ) -> SpineEvent:
        parent = self._last_by_trace.get(event.trace_id)
        edges: list[dict[str, Any]] = list(event.causal_edges or [])
        if parent:
            event.parent_event_id = parent
            event.causal_links = [parent]
            edges.append({"from": parent, "to": event.event_id, "relation": "temporal"})
        if triggered_by:
            edges.append({"from": str(triggered_by), "to": event.event_id, "relation": "triggered_by"})
        if control_of:
            edges.append({"from": str(control_of), "to": event.event_id, "relation": "control_flow"})
        if edges:
            event.causal_edges = edges
        self._log.append(event)
        self._last_by_trace[event.trace_id] = event.event_id
        self._mirror_execution_tap(event)
        return event

    def _mirror_execution_tap(self, event: SpineEvent) -> None:
        """All persisted spine rows → ExecutionTap (GTBS / control / state included)."""
        from core.runtime.execution_tap import get_execution_tap

        impact = "state_update" if event.action == "mutate" else "read"
        get_execution_tap().record(
            event_type=event.event_type,
            summary=event.summary,
            trace_id=event.trace_id,
            event_id=event.event_id,
            impact=impact,
            payload=event.payload if isinstance(event.payload, dict) else None,
            spine_written=True,
        )

    def last_event_id(self, trace_id: str) -> Optional[str]:
        return self._last_by_trace.get(trace_id)

    def emit(
        self,
        *,
        trace_id: str,
        event_type: str,
        summary: str,
        subsystem: str = "runtime",
        action: str = "read",
        payload: Optional[dict[str, Any]] = None,
        triggered_by: Optional[str] = None,
        control_of: Optional[str] = None,
        **fields: Any,
    ) -> SpineEvent:
        from datetime import datetime, timezone

        self._seq += 1
        event_id = f"{event_type[:8]}-{trace_id[:12]}-{self._seq}"
        event = SpineEvent(
            event_id=event_id,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            subsystem=subsystem,
            action=action,
            summary=summary,
            payload=payload,
            decision=fields.get("decision"),
            caller=fields.get("caller"),
            entry=fields.get("entry"),
            state_delta=fields.get("state_delta"),
            write_intent=fields.get("write_intent"),
            gtbs_ref=fields.get("gtbs_ref"),
        )
        return self._link_and_append(
            event,
            triggered_by=triggered_by,
            control_of=control_of,
        )

    def project_audit_event(self, audit: AuditTransactionEvent) -> Optional[SpineEvent]:
        row = audit.to_dict()
        return self.project_gtbs_dict(row)

    def project_gtbs_dict(self, row: dict[str, Any]) -> Optional[SpineEvent]:
        self._seq += 1
        event = project_gtbs_row(row, seq=self._seq)
        if event is None:
            return None
        tx_id = str(row.get("transaction_id") or "")
        if tx_id in self._trace_by_tx:
            event.trace_id = self._trace_by_tx[tx_id]
        elif event.trace_id and not event.trace_id.startswith("trace-prop-"):
            self._trace_by_tx[tx_id] = event.trace_id
        return self._link_and_append(event)

    def project_control(
        self,
        *,
        trace_id: str,
        decision: str,
        reason: str,
        caller: str,
        entry: str,
        route_kind: str = "",
    ) -> SpineEvent:
        self._seq += 1
        event = project_control_decision(
            trace_id=trace_id,
            decision=decision,
            reason=reason,
            caller=caller,
            entry=entry,
            route_kind=route_kind,
            seq=self._seq,
        )
        return self._link_and_append(event)

    def project_state_patch(
        self,
        *,
        trace_id: str,
        patch: dict[str, Any],
        triggered_by: Optional[str] = None,
    ) -> SpineEvent:
        """Append a state patch spine row (Tier-A diff)."""
        from datetime import datetime, timezone

        self._seq += 1
        event_id = f"state-{trace_id[:12]}-{self._seq}"
        count = int(patch.get("change_count") or len(patch.get("changes") or []))
        event = SpineEvent(
            event_id=event_id,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=SpineEventType.STATE.value,
            subsystem="runtime",
            action="mutate",
            summary=f"state · tier_a patch ({count} fields)",
            state_delta=patch,
        )
        return self._link_and_append(event, triggered_by=triggered_by)

    def hydrate_trace_heads_from_disk(self) -> None:
        """Restore last event per trace and tx→trace map after restart."""
        self._last_by_trace.clear()
        self._trace_by_tx.clear()
        for row in self._log.read_all():
            trace_id = str(row.get("trace_id") or "")
            event_id = str(row.get("event_id") or "")
            if trace_id and event_id:
                self._last_by_trace[trace_id] = event_id
            wi = row.get("write_intent") or {}
            intent_id = wi.get("intent_id")
            if intent_id and trace_id and not str(trace_id).startswith("trace-prop-"):
                self._trace_by_tx[str(intent_id)] = trace_id
        self._seq = len(self._log.read_all())


def rebuild_spine_from_gtbs(base_dir: str | Path, *, clear: bool = True) -> int:
    """
    Backfill spine_events.jsonl from gtbs_transactions.jsonl.
    Returns number of spine events written.
    """
    gtbs = GTBSTransactionLog(base_dir)
    writer = SpineWriter.from_base_dir(base_dir)
    if clear:
        writer._log.clear()
    writer._last_by_trace.clear()
    writer._trace_by_tx.clear()
    writer._seq = 0

    count = 0
    for row in gtbs.read_all():
        if writer.project_gtbs_dict(row) is not None:
            count += 1
    return count

"""GTBS / control-plane → SpineEvent projection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core.spine.types import SpineAction, SpineEvent, SpineEventType, SpineSubsystem

_KIND_TO_TYPE: dict[str, SpineEventType] = {
    "capture": SpineEventType.CAPTURE,
    "recall_side_effect": SpineEventType.RECALL,
    "cdg_apply": SpineEventType.CDG,
    "ir_commit": SpineEventType.IR,
    "chat_deferred": SpineEventType.CHAT,
    "working_self": SpineEventType.WRITE_INTENT,
    "governance_cycle": SpineEventType.WRITE_INTENT,
}

_CONTROL_TO_SPINE: dict[str, str] = {
    "allow": "ALLOW",
    "warn": "WARN",
    "signal_reject": "REJECT",
}


def _iso_ts(raw: dict[str, Any]) -> str:
    ts = raw.get("ts") or raw.get("timestamp")
    if isinstance(ts, str) and ts:
        return ts
    return datetime.now(timezone.utc).isoformat()


def _kind_to_event_type(kind: str) -> str:
    return _KIND_TO_TYPE.get(kind, SpineEventType.WRITE_INTENT).value


def _phase_to_action(phase: str, mutability: str = "") -> str:
    if phase == "commit":
        return SpineAction.COMMIT.value
    if phase == "rejection":
        return SpineAction.REJECT.value
    if phase == "approval":
        return SpineAction.PROPOSE.value
    if mutability == "advisory":
        return SpineAction.READ.value
    return SpineAction.PROPOSE.value


def _summary(kind: str, phase: str, mutability: str = "") -> str:
    label = kind.replace("_", " ")
    if phase == "rejection":
        return f"{label} · rejected"
    if phase == "commit":
        return f"{label} · committed"
    if mutability == "implicit":
        return f"{label} · implicit side-effect"
    if mutability == "advisory":
        return f"{label} · advisory only"
    return f"{label} · {phase}"


def _infer_decision(payload: dict[str, Any], phase: str) -> tuple[str, bool]:
    if phase == "rejection":
        return "REJECT", True
    if payload.get("rollback"):
        return "REJECT", True
    if payload.get("shadow") or str(payload.get("gtbs_mode", "")).upper().find("SHADOW") >= 0:
        return "WARN", False
    return "ALLOW", False


def project_gtbs_row(row: dict[str, Any], *, seq: int = 0) -> Optional[SpineEvent]:
    """Project one GTBS audit row into a SpineEvent (or None if unsupported phase)."""
    phase = str(row.get("event_type") or "")
    if phase not in ("proposal", "approval", "commit", "rejection", "defer"):
        return None

    payload = dict(row.get("payload") or {})
    prov = dict(payload.get("provenance") or {})
    kind = str(payload.get("write_intent_kind") or payload.get("source") or "write_intent")
    mutability = str(payload.get("mutability") or "explicit")
    tx_id = str(row.get("transaction_id") or "unknown")
    trace_raw = str(prov.get("trace_id") or "").strip()
    if trace_raw:
        trace_id = trace_raw
    else:
        from core.runtime.trace_id import generate_trace_id

        trace_id = generate_trace_id()
    caller = str(prov.get("caller") or prov.get("channel") or "http")
    entry = str(prov.get("entry_registry") or "unknown")
    ts = _iso_ts(row)
    event_id = f"{tx_id}:{phase}:{seq}"

    decision, hard_gate = _infer_decision(payload, phase)
    if phase == "rejection" and payload.get("reason") == "UNKNOWN_ENTRY":
        hard_gate = True

    target_stores = payload.get("target_stores")
    state_delta: Optional[dict[str, Any]] = None
    if isinstance(target_stores, list) and target_stores:
        state_delta = {"stores": [str(s) for s in target_stores]}
    elif phase == "commit" and payload.get("committed_at"):
        state_delta = {"committed": True}

    write_intent = {
        "intent_id": tx_id,
        "kind": kind,
        "mutability": mutability,
        "shadow": bool(payload.get("shadow")),
        "phase": phase,
    }

    return SpineEvent(
        event_id=event_id,
        trace_id=trace_id,
        timestamp=ts,
        event_type=_kind_to_event_type(kind),
        subsystem=SpineSubsystem.GTBS.value,
        action=_phase_to_action(phase, mutability),
        summary=_summary(kind, phase, mutability),
        decision=decision,
        caller=caller,
        entry=entry,
        hard_gate=hard_gate,
        state_delta=state_delta,
        write_intent=write_intent,
        gtbs_ref={"transaction_id": tx_id, "event_type": phase},
    )


def project_control_decision(
    *,
    trace_id: str,
    decision: str,
    reason: str,
    caller: str,
    entry: str,
    route_kind: str = "",
    seq: int = 0,
) -> SpineEvent:
    """Project a control-plane decision into Spine (CP-2 control index seed)."""
    spine_dec = _CONTROL_TO_SPINE.get(decision.lower(), "WARN")
    hard_gate = spine_dec == "REJECT"
    ts = datetime.now(timezone.utc).isoformat()
    event_id = f"ctrl-{trace_id[:12]}-{seq}:{spine_dec.lower()}"

    return SpineEvent(
        event_id=event_id,
        trace_id=trace_id,
        timestamp=ts,
        event_type=SpineEventType.CONTROL.value,
        subsystem=SpineSubsystem.CONTROL_PLANE.value,
        action=SpineAction.REJECT.value if hard_gate else SpineAction.READ.value,
        summary=f"control · {spine_dec} · {reason}",
        decision=spine_dec,
        caller=caller,
        entry=entry,
        hard_gate=hard_gate,
        write_intent=None,
        state_delta=None,
    )

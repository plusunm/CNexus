"""Structured audit trail for control-plane decisions."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.control_plane.decision_engine import Decision, DecisionType
from core.runtime.trace_context import resolve_trace_id

logger = logging.getLogger("cnexus.control_decision")


def audit_decision(
    decision: Decision,
    *,
    trace_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "decision": decision.type.value,
        "reason": decision.reason,
        "route_kind": decision.route_kind,
        "registry_entry": decision.registry_entry,
        "caller": decision.caller,
        "channel": decision.channel,
    }
    effective_trace = resolve_trace_id(trace_id)
    if effective_trace:
        payload["trace_id"] = effective_trace
    if extra:
        payload.update(extra)

    message = (
        f"{decision.type.value} {decision.route_kind}"
        f" ({decision.reason}) caller={decision.caller}"
    )

    if decision.type is DecisionType.SIGNAL_REJECT:
        logger.error("[control_decision] %s | %s", message, payload)
    elif decision.type is DecisionType.WARN:
        logger.warning("[control_decision] %s | %s", message, payload)
    else:
        logger.info("[control_decision] %s | %s", message, payload)

    try:
        from core.spine.integration import maybe_project_control_decision

        maybe_project_control_decision(decision, trace_id=effective_trace)
    except Exception:
        pass

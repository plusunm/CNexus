"""Progressive capability model — operational vs full readiness (BDE-1 fix)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.runtime.boot_protocol import (
    boot_ready_details,
    boot_status,
    evaluate_operational_ready,
    evaluate_system_ready,
    get_boot_phase,
)
from core.runtime.conflict_monitor import log_capability_transition


def _audit_capability(cap: Dict[str, Any], *, legacy_status: Optional[str] = None) -> None:
    try:
        log_capability_transition(
            operational_ready=bool(cap.get("operational_ready")),
            full_ready=bool(cap.get("full_ready")),
            cognitive_status=str(cap.get("cognitive_status", "unknown")),
            boot_phase=str(cap.get("boot_phase", "")),
            reason=cap.get("reason"),
            progress=cap.get("progress"),
            status=str(cap.get("status", "")),
            legacy_status=legacy_status,
        )
    except Exception:
        pass


def build_system_capabilities(
    *,
    app_started: bool,
    runtime_present: bool,
    runtime_warming: bool,
    memory_ok: bool,
    token_valid: bool = True,
    license_valid: bool = True,
) -> Dict[str, Any]:
    """Capability vector — SSOT for UI gates (chat/upload/llm)."""
    operational_status = evaluate_operational_ready(
        app_started=app_started,
        runtime_present=runtime_present,
        runtime_warming=runtime_warming,
        memory_ok=memory_ok,
        token_valid=token_valid,
        license_valid=license_valid,
    )
    full_status = evaluate_system_ready(
        app_started=app_started,
        runtime_present=runtime_present,
        runtime_warming=runtime_warming,
        memory_ok=memory_ok,
        token_valid=token_valid,
        license_valid=license_valid,
    )

    operational = operational_status == "operational"
    full = full_status == "ready"

    if full:
        cognitive_status = "ready"
    elif operational:
        cognitive_status = "warming"
    elif app_started:
        cognitive_status = "warming"
    else:
        cognitive_status = "offline"

    capabilities = {
        "api": bool(app_started),
        "memory": operational,
        "chat": operational,
        "upload": full,
        "llm": operational,
        "full": full,
    }

    if operational:
        surface_status = "operational"
    elif app_started or runtime_present:
        surface_status = "warming"
    else:
        surface_status = "warming"

    return {
        "status": surface_status,
        "operational_ready": operational,
        "full_ready": full,
        "cognitive_status": cognitive_status,
        "capabilities": capabilities,
        "operational_status": operational_status,
        "full_status": full_status,
        "boot_phase": get_boot_phase().value,
    }


def capability_envelope(
    *,
    app_started: bool,
    runtime_present: bool,
    runtime_warming: bool,
    memory_ok: bool,
    token_valid: bool = True,
    license_valid: bool = True,
    mode: str = "capability",
) -> Dict[str, Any]:
    """Full capability payload for /v1/system/capability and enriched /ready."""
    cap = build_system_capabilities(
        app_started=app_started,
        runtime_present=runtime_present,
        runtime_warming=runtime_warming,
        memory_ok=memory_ok,
        token_valid=token_valid,
        license_valid=license_valid,
    )

    full_status = cap["full_status"]
    details = boot_ready_details(
        status="ready" if cap["full_ready"] else ("warming" if cap["operational_ready"] else full_status),
        app_started=app_started,
        runtime_present=runtime_present,
        runtime_warming=runtime_warming,
        memory_ok=memory_ok,
    )

    result = {
        **cap,
        "ready": cap["full_ready"],
        "ready_for_chat": cap["capabilities"]["chat"],
        "ready_for_upload": cap["capabilities"]["upload"],
        "reason": None if cap["full_ready"] else details.get("reason"),
        "progress": 100 if cap["full_ready"] else details.get("progress"),
        "boot": boot_status(),
        "render_mode": "capability_v1",
        "capability_mode": mode,
    }
    _audit_capability(result)
    return result


def merge_capability_fields(
    payload: Dict[str, Any],
    *,
    app_started: bool,
    runtime_present: bool,
    runtime_warming: bool,
    memory_ok: bool,
    token_valid: bool = True,
    license_valid: bool = True,
) -> Dict[str, Any]:
    """Attach capability vector to an existing ready payload (backward compatible)."""
    cap = capability_envelope(
        app_started=app_started,
        runtime_present=runtime_present,
        runtime_warming=runtime_warming,
        memory_ok=memory_ok,
        token_valid=token_valid,
        license_valid=license_valid,
        mode="merged",
    )
    merged = dict(payload)
    merged.update(
        {
            "operational_ready": cap["operational_ready"],
            "full_ready": cap["full_ready"],
            "cognitive_status": cap["cognitive_status"],
            "capabilities": cap["capabilities"],
            "ready_for_chat": cap["ready_for_chat"],
            "ready_for_upload": cap["ready_for_upload"],
        }
    )
    if merged.get("status") in ("ready_fast", "streaming"):
        merged["status"] = cap["status"] if cap["operational_ready"] else "warming"
        merged["legacy_status"] = payload.get("status")
    _audit_capability({**cap, "reason": merged.get("reason"), "progress": merged.get("progress"), "status": merged.get("status")}, legacy_status=merged.get("legacy_status"))
    return merged

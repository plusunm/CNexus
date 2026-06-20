"""CNexus system-ready signal — Boot Protocol v3 (scheduler-driven control plane)."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from api.license_guard import api_token_required, expected_api_token, license_valid
from core.runtime.boot_protocol import (
    BootPhase,
    boot_ready_details,
    boot_status,
    fast_health_payload,
    is_runtime_warming,
    set_boot_phase,
)
from core.runtime.system_capability import capability_envelope

BOOT_ID: str = uuid.uuid4().hex
_MONO_START = time.monotonic()
_APP_STARTED = False


def mark_app_started() -> None:
    global _APP_STARTED
    _APP_STARTED = True
    set_boot_phase(BootPhase.BOOT_0_API)


def system_ready_warming_payload() -> Dict[str, Any]:
    uptime_ms = int((time.monotonic() - _MONO_START) * 1000) if _APP_STARTED else 0
    boot = boot_status()
    payload = {
        "status": "warming",
        "boot_id": BOOT_ID,
        "boot_phase": boot["boot_phase"],
        "token_valid": True,
        "license_valid": True,
        "ws": "starting",
        "http": "listening" if _APP_STARTED else "starting",
        "memory": "warming",
        "uptime_ms": uptime_ms,
        "version": "0.1.0-alpha",
        "checks": {"runtime": {"name": "runtime", "ok": False, "detail": "warming"}},
        "boot": boot,
    }
    payload.update(
        boot_ready_details(
            status="warming",
            app_started=_APP_STARTED,
            runtime_present=False,
            runtime_warming=True,
            memory_ok=False,
        )
    )
    payload.update(
        {
            "operational_ready": False,
            "full_ready": False,
            "cognitive_status": "warming",
            "capabilities": {
                "api": _APP_STARTED,
                "memory": False,
                "chat": False,
                "upload": False,
                "llm": False,
                "full": False,
            },
            "ready_for_chat": False,
            "ready_for_upload": False,
        }
    )
    try:
        from api.runtime_warm_status import runtime_warm_meta

        payload["runtime_warm"] = runtime_warm_meta()
    except ImportError:
        pass
    return payload


def _auth_gates() -> tuple[bool, bool]:
    token_valid = True
    if api_token_required():
        token_valid = bool(expected_api_token())
    return token_valid, license_valid()


def _envelope_ready_payload(runtime: Any, *, mode: str = "default") -> Dict[str, Any]:
    """SSOT ready/capability payload — shared by /ready and /capability."""
    uptime_ms = int((time.monotonic() - _MONO_START) * 1000) if _APP_STARTED else 0
    token_valid, license_valid = _auth_gates()
    http_status = "listening" if _APP_STARTED else "starting"
    ws_status = "alive" if runtime is not None else "starting"

    if runtime is None:
        cap = capability_envelope(
            app_started=_APP_STARTED,
            runtime_present=False,
            runtime_warming=True,
            memory_ok=False,
            token_valid=token_valid,
            license_valid=license_valid,
            mode=mode,
        )
        return {
            **cap,
            "boot_id": BOOT_ID,
            "uptime_ms": uptime_ms,
            "version": "0.1.0-alpha",
            "ws": ws_status,
            "http": http_status,
        }

    deep = fast_health_payload(runtime)
    memory_status = deep.get("status", "not_ready")
    memory_ok = memory_status in ("ready", "degraded", "initializing")
    cap = capability_envelope(
        app_started=_APP_STARTED,
        runtime_present=True,
        runtime_warming=is_runtime_warming(),
        memory_ok=memory_ok,
        token_valid=token_valid,
        license_valid=license_valid,
        mode=mode,
    )
    return {
        **cap,
        "boot_id": BOOT_ID,
        "uptime_ms": uptime_ms,
        "version": "0.1.0-alpha",
        "ws": ws_status,
        "http": http_status,
        "memory": memory_status,
        "checks": deep.get("checks"),
    }


def system_ready_payload(runtime: Any, *, mode: str = "default") -> Dict[str, Any]:
    """Build GET /v1/system/ready — capability SSOT (stream mode returns SSE ack only)."""
    normalized = (mode or "default").strip().lower()
    if normalized == "stream":
        from core.runtime.streaming_ready import streaming_ready_ack

        return streaming_ready_ack()
    return _envelope_ready_payload(runtime, mode=mode)


def system_capability_payload(runtime: Any, *, mode: str = "default") -> Dict[str, Any]:
    """GET /v1/system/capability — SSOT capability vector for UI."""
    return _envelope_ready_payload(runtime, mode=mode)

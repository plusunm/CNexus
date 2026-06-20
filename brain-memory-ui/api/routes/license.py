"""License status and heartbeat endpoints for CNexus Runtime."""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.license_guard import (
    heartbeat_fail_to_degraded,
    heartbeat_fail_to_locked,
    license_status_payload,
    license_valid,
    machine_fingerprint,
    offline_grace_sec,
    record_heartbeat_failure,
    record_heartbeat_success,
)

router = APIRouter(tags=["license"])


class HeartbeatRequest(BaseModel):
    session_id: Optional[str] = None
    machine_id: Optional[str] = None
    client: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    nonce: str = ""
    ts: int = 0


@router.get("/system/license_status")
async def get_license_status():
  return license_status_payload()


@router.post("/session/heartbeat")
async def post_session_heartbeat(body: HeartbeatRequest):
    if body.machine_id and body.machine_id != machine_fingerprint():
        payload = record_heartbeat_failure(reason="MACHINE_MISMATCH")
        return payload

    if not license_valid():
        return record_heartbeat_failure(reason="LICENSE_INVALID")

    return record_heartbeat_success()


@router.post("/user/auth")
async def post_user_auth_stub():
    """Staging/dev re-auth stub — returns current license snapshot."""
    if not license_valid():
        return {
            "ok": False,
            "error": {"code": "LICENSE_INVALID", "message": "license invalid"},
        }
    snap = record_heartbeat_success()
    now = int(time.time())
    return {
        "ok": True,
        "server_time": now,
        "session": {
            "session_id": body_placeholder_session(),
            "heartbeat_interval_sec": 600,
            "heartbeat_timeout_sec": 5,
            "offline_grace_sec": offline_grace_sec(),
        },
        "license": {
            "license_id": "local",
            "plan": snap["edition"],
            "expire_at": snap["grace_until"],
            "machine_fingerprint": snap["machine_fingerprint"],
        },
        "feature_policy": {
            "runtime_mode": snap["runtime_mode"],
            "granted_features": snap["granted_features"],
        },
        "license_status": snap,
        "thresholds": {
            "fail_to_degraded": heartbeat_fail_to_degraded(),
            "fail_to_locked": heartbeat_fail_to_locked(),
        },
    }


def body_placeholder_session() -> str:
    return "local-session"

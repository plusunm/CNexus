"""Deployment license + API token guards with grace period and heartbeat degradation."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

PUBLIC_PATHS = frozenset({
    "/health",
    "/debug/event_loop",
    "/v1/health",
    "/v1/health/ready",
    "/v1/system/ready",
    "/v1/system/ready/stream",
    "/v1/system/capability",
    "/v1/system/conflict_log",
    "/v1/system/compute",
    "/v1/system/license_status",
    "/v1/chat/fast",
    "/v1/chat/fast/stream",
    "/v1/intent",
    "/v1/sibt/project",
    "/v1/system/linkage_debug",
    "/v1/system/warm_runtime",
    "/docs",
    "/openapi.json",
    "/redoc",
})

HEARTBEAT_PATH = "/v1/session/heartbeat"


class RuntimeMode(str, Enum):
    TRUSTED = "Trusted"
    OFFLINE_GRACE = "OfflineGrace"
    DEGRADED = "Degraded"
    LOCKED = "Locked"


@dataclass
class LicenseSessionState:
    runtime_mode: str = RuntimeMode.TRUSTED.value
    heartbeat_fail_count: int = 0
    last_heartbeat_ok_at: int = 0
    grace_until: int = 0
    issued_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LicenseSessionState":
        return cls(
            runtime_mode=str(data.get("runtime_mode", RuntimeMode.TRUSTED.value)),
            heartbeat_fail_count=int(data.get("heartbeat_fail_count", 0)),
            last_heartbeat_ok_at=int(data.get("last_heartbeat_ok_at", 0)),
            grace_until=int(data.get("grace_until", 0)),
            issued_at=int(data.get("issued_at", 0)),
        )


_SESSION = LicenseSessionState()
_FEATURE_GATE = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_feature_gate():
    global _FEATURE_GATE
    if _FEATURE_GATE is not None:
        return _FEATURE_GATE
    try:
        from security_harness.feature_gate import FeatureGate, RuntimeMode as GateMode

        gate_path = _repo_root() / "security_harness" / "feature_gate.json"
        if gate_path.is_file():
            gate = FeatureGate.from_config(gate_path)
            gate.load_edition(product_edition())
            _FEATURE_GATE = (gate, GateMode)
            return _FEATURE_GATE
    except Exception:
        pass
    return None, None


def product_edition() -> str:
    return os.environ.get("CNEXUS_EDITION", "personal").strip().lower()


def deploy_level() -> str:
    return os.environ.get("CNEXUS_DEPLOY_LEVEL", "dev").strip().lower()


def offline_grace_sec() -> int:
    return int(os.environ.get("CNEXUS_OFFLINE_GRACE_SEC", "3600"))


def heartbeat_fail_to_degraded() -> int:
    return int(os.environ.get("CNEXUS_HEARTBEAT_FAIL_TO_DEGRADED", "3"))


def heartbeat_fail_to_locked() -> int:
    return int(os.environ.get("CNEXUS_HEARTBEAT_FAIL_TO_LOCKED", "10"))


def license_required() -> bool:
    if os.environ.get("CNEXUS_LICENSE_SKIP", "").lower() in ("1", "true", "yes"):
        return False
    if product_edition() == "enterprise":
        return True
    return deploy_level() in ("enterprise", "commercial")


def machine_fingerprint() -> str:
    return f"{uuid.getnode():012x}"


def license_state_path() -> Path:
    explicit = os.environ.get("CNEXUS_LICENSE_STATE_FILE", "").strip()
    if explicit:
        return Path(explicit)
    data_root = os.environ.get("CNEXUS_DATA_DIR", "").strip()
    if data_root:
        return Path(data_root) / "license_state.json"
    license_file = os.environ.get("CNEXUS_LICENSE_FILE", "").strip()
    if license_file:
        return Path(license_file).parent / "license_state.json"
    return Path("/run/cnexus/license_state.json")


def _read_license_value() -> str:
    inline = os.environ.get("CNEXUS_LICENSE", "").strip()
    if inline:
        return inline
    path = os.environ.get("CNEXUS_LICENSE_FILE", "/run/secrets/cnexus-license").strip()
    if path and Path(path).is_file():
        return Path(path).read_text(encoding="utf-8").strip()
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        cnx = Path(local) / "CNexus" / "license.cnx"
        if cnx.is_file():
            return cnx.read_text(encoding="utf-8").strip()
    return ""


def _load_session_state() -> LicenseSessionState:
    path = license_state_path()
    if not path.is_file():
        return LicenseSessionState()
    try:
        return LicenseSessionState.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return LicenseSessionState()


def _save_session_state(state: LicenseSessionState) -> None:
    global _SESSION
    _SESSION = state
    path = license_state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    except OSError:
        pass


def get_session_state() -> LicenseSessionState:
    return _SESSION


def get_runtime_mode() -> RuntimeMode:
    now = int(time.time())
    state = _SESSION
    if state.grace_until and now > state.grace_until:
        return RuntimeMode.LOCKED
    try:
        return RuntimeMode(state.runtime_mode)
    except ValueError:
        return RuntimeMode.LOCKED


def license_valid() -> bool:
    if not license_required():
        return True
    if get_runtime_mode() == RuntimeMode.LOCKED:
        return False
    secret = os.environ.get("CNEXUS_LICENSE_SECRET", "").strip()
    token = _read_license_value()
    if not secret or not token:
        return False
    expected = issue_license(secret, machine_fingerprint())
    return hmac.compare_digest(token, expected)


def default_granted_features() -> list[str]:
    gate_bundle = _load_feature_gate()
    gate, _ = gate_bundle
    if gate is None:
        if product_edition() == "enterprise":
            return [
                "CORE_UI",
                "CORE_LOGIN",
                "CORE_LOCAL_RUNTIME",
                "CORE_ENTERPRISE_RUNTIME",
                "CORE_API_TOKEN",
                "CORE_GTBS",
                "CORE_SIBT",
            ]
        return ["CORE_UI", "CORE_LOGIN", "CORE_PERSONAL_DEMO"]
    gate.set_granted_features(gate.edition_defaults.get(product_edition(), []))
    return sorted(gate.granted_features)


def granted_features() -> list[str]:
    gate_bundle = _load_feature_gate()
    gate, gate_mode = gate_bundle
    features = default_granted_features()
    if gate is None:
        mode = get_runtime_mode()
        if mode in (RuntimeMode.LOCKED,):
            return [f for f in features if f.startswith("CORE_UI") or f == "CORE_LOGIN"]
        if mode in (RuntimeMode.DEGRADED,):
            return [f for f in features if f in {"CORE_UI", "CORE_LOGIN", "CORE_NETWORK_DIAG", "CORE_PERSONAL_DEMO"}]
        return features

    gate.set_granted_features(features)
    gate.set_runtime_mode(gate_mode(get_runtime_mode().value))
    return sorted(f for f in features if gate.allow(f))


def feature_allowed(capability_id: str) -> bool:
    return capability_id in granted_features()


def require_feature(capability_id: str) -> None:
    if feature_allowed(capability_id):
        return
    mode = get_runtime_mode()
    raise HTTPException(
        status_code=403,
        detail={
            "code": "FEATURE_BLOCKED",
            "capability": capability_id,
            "runtime_mode": mode.value,
            "message": "当前授权模式下此功能不可用，请重新验证授权。",
        },
    )


def _init_session_after_verify() -> None:
    now = int(time.time())
    state = _load_session_state()
    state.runtime_mode = RuntimeMode.TRUSTED.value
    state.heartbeat_fail_count = 0
    state.last_heartbeat_ok_at = now
    state.issued_at = now
    state.grace_until = now + offline_grace_sec()
    _save_session_state(state)


def verify_license_or_exit() -> None:
    """Call at process startup before serving traffic."""
    global _SESSION
    _SESSION = _load_session_state()

    if not license_required():
        return

    secret = os.environ.get("CNEXUS_LICENSE_SECRET", "").strip()
    if not secret:
        raise SystemExit(
            "CNEXUS_LICENSE_SECRET is required when CNEXUS_DEPLOY_LEVEL is "
            f"{deploy_level()}. Set CNEXUS_LICENSE_SKIP=1 for internal CI only."
        )

    token = _read_license_value()
    if not token:
        raise SystemExit(
            f"CNEXUS license required (level={deploy_level()}). "
            f"Set CNEXUS_LICENSE or mount CNEXUS_LICENSE_FILE. "
            f"Machine fingerprint: {machine_fingerprint()}"
        )

    expected = issue_license(secret, machine_fingerprint())
    if not hmac.compare_digest(token, expected):
        raise SystemExit(
            "Invalid CNEXUS license for this host. "
            f"Fingerprint: {machine_fingerprint()}"
        )

    now = int(time.time())
    if _SESSION.grace_until and now > _SESSION.grace_until and _SESSION.last_heartbeat_ok_at:
        raise SystemExit(
            "CNEXUS license grace period expired. Reconnect and verify authorization."
        )

    _init_session_after_verify()


def issue_license(secret: str, fingerprint: Optional[str] = None) -> str:
    """Generate a host-bound license (run offline — never ship secret in images)."""
    fp = fingerprint or machine_fingerprint()
    digest = hmac.new(secret.encode("utf-8"), fp.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"CNX1.{fp}.{digest[:32]}"


def record_heartbeat_success() -> dict[str, Any]:
    now = int(time.time())
    if not license_valid():
        return record_heartbeat_failure(reason="LICENSE_INVALID")

    state = _SESSION
    state.runtime_mode = RuntimeMode.TRUSTED.value
    state.heartbeat_fail_count = 0
    state.last_heartbeat_ok_at = now
    state.grace_until = now + offline_grace_sec()
    _save_session_state(state)
    return license_status_payload()


def record_heartbeat_failure(*, reason: str = "NETWORK") -> dict[str, Any]:
    state = _SESSION
    state.heartbeat_fail_count += 1
    fail_count = state.heartbeat_fail_count

    if fail_count >= heartbeat_fail_to_locked():
        state.runtime_mode = RuntimeMode.LOCKED.value
    elif fail_count >= heartbeat_fail_to_degraded():
        state.runtime_mode = RuntimeMode.DEGRADED.value
    elif fail_count >= 1:
        state.runtime_mode = RuntimeMode.OFFLINE_GRACE.value
    else:
        state.runtime_mode = RuntimeMode.TRUSTED.value

    _save_session_state(state)
    payload = license_status_payload()
    payload["heartbeat"] = {
        "ok": False,
        "reason": reason,
        "fail_count": fail_count,
        "recommended_mode": state.runtime_mode,
    }
    return payload


def license_status_payload() -> dict[str, Any]:
    state = _SESSION
    mode = get_runtime_mode()
    now = int(time.time())
    return {
        "ok": license_valid() and mode != RuntimeMode.LOCKED,
        "edition": product_edition(),
        "license_valid": license_valid(),
        "runtime_mode": mode.value,
        "machine_fingerprint": machine_fingerprint(),
        "grace_until": state.grace_until,
        "grace_remaining_sec": max(0, state.grace_until - now) if state.grace_until else 0,
        "heartbeat_fail_count": state.heartbeat_fail_count,
        "last_heartbeat_ok_at": state.last_heartbeat_ok_at,
        "granted_features": granted_features(),
        "user_message": _user_message_for_mode(mode, state),
    }


def _user_message_for_mode(mode: RuntimeMode, state: LicenseSessionState) -> str:
    if mode == RuntimeMode.TRUSTED:
        return "授权正常"
    if mode == RuntimeMode.OFFLINE_GRACE:
        return "网络波动，部分高风险功能已暂停。"
    if mode == RuntimeMode.DEGRADED:
        return "已进入受限模式，仅保留只读与基础功能。"
    if state.grace_until:
        remaining = max(0, state.grace_until - int(time.time()))
        if remaining:
            return f"授权缓存将在 {remaining // 60} 分钟后失效，请尽快重新验证。"
    return "授权已失效，请重新登录或激活企业 License。"


def expected_api_token() -> str:
    return os.environ.get("CNEXUS_API_TOKEN", "").strip()


def api_token_required() -> bool:
    if os.environ.get("CNEXUS_API_TOKEN_SKIP", "").lower() in ("1", "true", "yes"):
        return False
    if get_runtime_mode() in (RuntimeMode.DEGRADED, RuntimeMode.LOCKED):
        return False
    if product_edition() == "enterprise":
        return bool(expected_api_token())
    return deploy_level() in ("enterprise", "commercial") and bool(expected_api_token())


class ApiTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if path == HEARTBEAT_PATH:
            return await call_next(request)

        if not api_token_required():
            return await call_next(request)

        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        header = request.headers.get("x-cnexus-token", "").strip()
        if not header or not hmac.compare_digest(header, expected_api_token()):
            raise HTTPException(status_code=401, detail="Invalid or missing X-CNexus-Token")

        return await call_next(request)

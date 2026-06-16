"""Deployment license + API token guards (Phase 1 — enterprise local)."""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from pathlib import Path
from typing import Optional

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


def product_edition() -> str:
    return os.environ.get("CNEXUS_EDITION", "personal").strip().lower()


def deploy_level() -> str:
    return os.environ.get("CNEXUS_DEPLOY_LEVEL", "dev").strip().lower()


def license_required() -> bool:
    if os.environ.get("CNEXUS_LICENSE_SKIP", "").lower() in ("1", "true", "yes"):
        return False
    if product_edition() == "enterprise":
        return True
    return deploy_level() in ("enterprise", "commercial")


def machine_fingerprint() -> str:
    return f"{uuid.getnode():012x}"


def _read_license_value() -> str:
    inline = os.environ.get("CNEXUS_LICENSE", "").strip()
    if inline:
        return inline
    path = os.environ.get("CNEXUS_LICENSE_FILE", "/run/secrets/cnexus-license").strip()
    if path and Path(path).is_file():
        return Path(path).read_text(encoding="utf-8").strip()
    return ""


def verify_license_or_exit() -> None:
    """Call at process startup before serving traffic."""
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


def issue_license(secret: str, fingerprint: Optional[str] = None) -> str:
    """Generate a host-bound license (run offline — never ship secret in images)."""
    fp = fingerprint or machine_fingerprint()
    digest = hmac.new(secret.encode("utf-8"), fp.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"CNX1.{fp}.{digest[:32]}"


def expected_api_token() -> str:
    return os.environ.get("CNEXUS_API_TOKEN", "").strip()


def api_token_required() -> bool:
    if os.environ.get("CNEXUS_API_TOKEN_SKIP", "").lower() in ("1", "true", "yes"):
        return False
    if product_edition() == "enterprise":
        return bool(expected_api_token())
    return deploy_level() in ("enterprise", "commercial") and bool(expected_api_token())


class ApiTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not api_token_required():
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        header = request.headers.get("x-cnexus-token", "").strip()
        if not header or not hmac.compare_digest(header, expected_api_token()):
            raise HTTPException(status_code=401, detail="Invalid or missing X-CNexus-Token")

        return await call_next(request)

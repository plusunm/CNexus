"""CNexus request authentication — Ed25519 + timestamp anti-replay.

Adapted for stdlib http.server (app_v2.py). Flask-style decorator API is provided
for future frameworks; app_v2 uses verify_cnexus_auth() directly.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

# POST routes that require auth when CNEXUS_AUTH_REQUIRED=1
PROTECTED_POST_PATHS = frozenset({
    "/api/converse",
    "/api/memory/clear",
    "/v1/memory/clear",
    "/v1/memory/capture",
    "/v1/memory/rem-sleep",
    "/api/ingest/image",
    "/api/ingest/code",
    "/api/upload/code",
    "/api/upload/image",
    "/api/asset/push",
})

# Peer / P2P routes — always require auth when identity is available
STRICT_PEER_PATHS = frozenset({
    "/api/peer/sync",
    "/api/peer/audit",
    "/api/peer/audit-proof",
    "/api/peer/negotiate",
    "/api/p2p/handshake",
    "/api/asset/receive",
})

HEADER_SIGNATURE = "X-CNexus-Signature"
HEADER_PUBKEY = "X-CNexus-Pubkey"
HEADER_TIMESTAMP = "X-CNexus-Timestamp"
HEADER_NONCE = "X-CNexus-Nonce"

DEFAULT_MAX_SKEW_SECONDS = 30


def _env_truthy(name: str, default: bool = False) -> bool:
    import os
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def auth_required_enabled() -> bool:
    return _env_truthy("CNEXUS_AUTH_REQUIRED", default=False)


def max_skew_seconds() -> int:
    import os
    try:
        return int(os.environ.get("CNEXUS_AUTH_MAX_SKEW", str(DEFAULT_MAX_SKEW_SECONDS)))
    except ValueError:
        return DEFAULT_MAX_SKEW_SECONDS


def path_requires_auth(path: str) -> bool:
    normalized = (path or "/").rstrip("/") or "/"
    if normalized in STRICT_PEER_PATHS:
        return True
    if not auth_required_enabled():
        return False
    return normalized in PROTECTED_POST_PATHS


def build_auth_message(payload: dict, timestamp: str, nonce: Optional[str] = None) -> dict:
    msg = {"payload": payload or {}, "timestamp": str(timestamp)}
    if nonce:
        msg["nonce"] = str(nonce)
    return msg


def build_signed_headers(
    identity_manager,
    payload: dict,
    *,
    timestamp: Optional[float] = None,
    nonce: Optional[str] = None,
) -> Dict[str, str]:
    """Build request headers for a signed CNexus API call."""
    ts = time.time() if timestamp is None else float(timestamp)
    ts_str = str(ts)
    signed = identity_manager.sign_payload(build_auth_message(payload, ts_str, nonce))
    headers = {
        HEADER_SIGNATURE: signed["signature"],
        HEADER_PUBKEY: signed["pubkey"],
        HEADER_TIMESTAMP: ts_str,
    }
    if nonce:
        headers[HEADER_NONCE] = str(nonce)
    return headers


def _header_lookup(headers, name: str) -> Optional[str]:
    if hasattr(headers, "get"):
        return headers.get(name) or headers.get(name.lower())
    return None


def verify_cnexus_auth(
    headers,
    body_json: Optional[dict],
    identity_manager,
    *,
    max_skew: Optional[int] = None,
    require_nonce: bool = False,
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Verify X-CNexus-* headers.
    Returns (ok, error_body, http_status).
    """
    if identity_manager is None:
        return True, {}, 200

    signature = _header_lookup(headers, HEADER_SIGNATURE)
    pubkey = _header_lookup(headers, HEADER_PUBKEY)
    timestamp = _header_lookup(headers, HEADER_TIMESTAMP)
    nonce = _header_lookup(headers, HEADER_NONCE)

    if not all([signature, pubkey, timestamp]):
        return False, {"error": "Unauthorized: Missing Identity Headers"}, 401

    if require_nonce and not nonce:
        return False, {"error": "Unauthorized: Missing Nonce"}, 401

    skew_limit = max_skew if max_skew is not None else max_skew_seconds()
    try:
        if abs(time.time() - float(timestamp)) > skew_limit:
            return False, {"error": "Unauthorized: Request Expired"}, 403
    except (TypeError, ValueError):
        return False, {"error": "Unauthorized: Invalid Timestamp"}, 403

    payload = body_json if isinstance(body_json, dict) else {}
    verification_pkg = {
        "payload": build_auth_message(payload, str(timestamp), nonce),
        "signature": signature,
        "pubkey": pubkey,
    }
    if not identity_manager.verify_payload(verification_pkg, pubkey):
        return False, {"error": "Forbidden: Invalid Signature"}, 403

    return True, {}, 200


def require_cnexus_auth(
    identity_manager_factory: Callable[[], Any],
    *,
    max_skew: Optional[int] = None,
):
    """Flask-compatible decorator (optional — app_v2 uses verify_cnexus_auth)."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                from flask import jsonify, request  # type: ignore
            except ImportError as exc:
                raise RuntimeError("Flask is required for require_cnexus_auth decorator") from exc

            im = identity_manager_factory()
            body = request.get_json(silent=True) if request.is_json else {}
            ok, err, status = verify_cnexus_auth(
                request.headers,
                body,
                im,
                max_skew=max_skew,
            )
            if not ok:
                return jsonify(err), status
            return f(*args, **kwargs)

        return wrapped

    return decorator

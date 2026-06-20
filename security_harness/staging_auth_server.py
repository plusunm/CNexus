"""Staging auth server for CNexus protection verification (signed test licenses only)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


def _issue_license(secret: str, fingerprint: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), fingerprint.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"CNX1.{fingerprint}.{digest[:32]}"


def _verify_license(secret: str, token: str, fingerprint: str) -> bool:
    expected = _issue_license(secret, fingerprint)
    return hmac.compare_digest(token, expected)


class StagingAuthHandler(BaseHTTPRequestHandler):
    secret: str = ""
    api_token: str = ""

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/v1/ping":
            self._send(200, {"ok": True, "service": "cnexus-staging-auth"})
            return
        self._send(404, {"ok": False, "error": {"code": "NOT_FOUND"}})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        body = self._read_json()

        if path == "/v1/user/auth":
            self._handle_auth(body)
            return
        if path == "/v1/session/heartbeat":
            self._handle_heartbeat(body)
            return
        self._send(404, {"ok": False, "error": {"code": "NOT_FOUND"}})

    def _handle_auth(self, body: dict[str, Any]) -> None:
        secret = self.secret
        if not secret:
            self._send(500, {"ok": False, "error": {"code": "SERVER_MISCONFIG", "message": "missing secret"}})
            return

        machine = body.get("machine", {})
        fingerprint = machine.get("machine_id") or machine.get("fingerprint")
        if not fingerprint:
            self._send(400, {"ok": False, "error": {"code": "INVALID_REQUEST", "message": "machine_id required"}})
            return

        auth_type = body.get("auth_type", "license_token")
        token = body.get("license_token", "")
        if auth_type == "card_key":
            token = _issue_license(secret, fingerprint)
        elif not token or not _verify_license(secret, token, fingerprint):
            self._send(401, {"ok": False, "error": {"code": "INVALID_CREDENTIAL", "message": "bad license"}})
            return

        now = int(time.time())
        session_id = str(uuid.uuid4())
        edition = body.get("edition", "enterprise")
        features = [
            "CORE_UI",
            "CORE_LOGIN",
            "CORE_NETWORK_DIAG",
            "CORE_LOCAL_RUNTIME",
            "CORE_ENTERPRISE_RUNTIME",
            "CORE_API_TOKEN",
        ]
        if edition == "enterprise":
            features.extend(["CORE_GTBS", "CORE_SIBT"])

        self._send(
            200,
            {
                "ok": True,
                "server_time": now,
                "session": {
                    "session_id": session_id,
                    "user_id": "staging_user",
                    "heartbeat_interval_sec": 600,
                    "heartbeat_timeout_sec": 5,
                    "offline_grace_sec": 3600,
                },
                "license": {
                    "license_id": "lic_staging",
                    "plan": edition,
                    "expire_at": now + 86400,
                    "license_token": token,
                    "machine_fingerprint": fingerprint,
                },
                "feature_policy": {
                    "runtime_mode": "Trusted",
                    "granted_features": features,
                },
            },
        )

    def _handle_heartbeat(self, body: dict[str, Any]) -> None:
        session_id = body.get("session_id")
        if not session_id:
            self._send(400, {"ok": False, "error": {"code": "INVALID_REQUEST"}})
            return
        now = int(time.time())
        self._send(
            200,
            {
                "ok": True,
                "server_time": now,
                "next_interval_sec": 600,
                "runtime_mode": "Trusted",
                "feature_policy": {
                    "granted_features": body.get("runtime", {}).get("active_features", []),
                    "revoked_features": [],
                    "force_actions": [],
                },
            },
        )


def serve(host: str, port: int, *, secret: str, api_token: str = "") -> ThreadingHTTPServer:
    StagingAuthHandler.secret = secret
    StagingAuthHandler.api_token = api_token
    server = ThreadingHTTPServer((host, port), StagingAuthHandler)
    return server


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CNexus staging auth server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18711)
    args = parser.parse_args()

    secret = os.environ.get("CNEXUS_LICENSE_SECRET", "staging-secret-change-me")
    token = os.environ.get("CNEXUS_API_TOKEN", "")
    server = serve(args.host, args.port, secret=secret, api_token=token)
    print(f"staging auth listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

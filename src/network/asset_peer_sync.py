"""Push cognitive assets to trusted peers after local indexing."""

from __future__ import annotations

import base64
import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest


HttpPostFn = Callable[[str, str, dict], dict]


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


class AssetPeerSync:
    def __init__(
        self,
        asset_processor,
        peer_registry=None,
        *,
        build_signed_headers: Optional[Callable] = None,
        max_push_bytes: int = 5_242_880,
        push_queue=None,
    ):
        self.asset_processor = asset_processor
        self.peer_registry = peer_registry
        self._build_signed_headers = build_signed_headers
        self.max_push_bytes = max(1024, int(max_push_bytes))
        self.push_queue = push_queue
        self._lock = threading.Lock()
        self.last_push_results: Dict[str, Dict[str, Any]] = {}

    def trusted_peers(self) -> List[dict]:
        peers = self.peer_registry.get_all_peers() if self.peer_registry else {}
        rows = []
        for pubkey, meta in peers.items():
            host = str(meta.get("host") or "").strip()
            if not host:
                continue
            if str(meta.get("status") or "trusted") not in ("trusted", "online"):
                continue
            rows.append({"pubkey": pubkey, "host": _normalize_host(host), **meta})
        return rows

    def build_push_payload(self, asset_id: str) -> Tuple[Optional[dict], str]:
        blob, meta, status = self.asset_processor.read_raw(asset_id)
        if blob is None or meta is None:
            return None, "asset_not_found" if status == 404 else "read_failed"
        if len(blob) > self.max_push_bytes:
            return None, f"asset_too_large ({len(blob)} > {self.max_push_bytes})"

        payload = {
            "action": "ASSET_PUSH",
            "asset_id": asset_id,
            "type": meta.get("type"),
            "filename": meta.get("filename"),
            "size_bytes": meta.get("size_bytes", len(blob)),
            "content_base64": base64.b64encode(blob).decode("ascii"),
        }
        if meta.get("type") == "code":
            payload["summary"] = meta.get("summary")
        else:
            payload["desc"] = meta.get("desc")
        return payload, "ok"

    def _http_post(self, host: str, path: str, payload: dict) -> dict:
        host = _normalize_host(host)
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._build_signed_headers:
            headers.update(self._build_signed_headers(payload))
        req = urlrequest.Request(f"{host}{path}", data=body, headers=headers, method="POST")
        with urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def push_to_peer(self, host: str, pubkey: str, asset_id: str) -> dict:
        payload, reason = self.build_push_payload(asset_id)
        result: Dict[str, Any] = {
            "ok": False,
            "peer_host": _normalize_host(host),
            "peer_pubkey": pubkey,
            "asset_id": asset_id,
            "pushed_at": time.time(),
        }
        if payload is None:
            result["error"] = reason
            self._remember(pubkey or host, result)
            return result

        try:
            remote = self._http_post(host, "/api/asset/receive", payload)
            result.update(remote)
            result["ok"] = bool(remote.get("ok"))
        except urlerror.HTTPError as exc:
            result["error"] = f"http_{exc.code}"
        except Exception as exc:
            result["error"] = str(exc)

        if not result.get("ok") and self.push_queue is not None:
            enqueue = self.push_queue.enqueue(
                asset_id,
                host,
                peer_pubkey=pubkey,
                error=str(result.get("error") or "push_failed"),
            )
            result["retry_queued"] = bool(enqueue.get("queued"))

        self._remember(pubkey or host, result)
        return result

    def push_asset(self, asset_id: str) -> dict:
        peers = self.trusted_peers()
        results = []
        ok_count = 0
        for peer in peers:
            row = self.push_to_peer(peer["host"], peer["pubkey"], asset_id)
            results.append(row)
            if row.get("ok"):
                ok_count += 1
        return {
            "ok": ok_count > 0 or not peers,
            "asset_id": asset_id,
            "peer_count": len(peers),
            "pushed": ok_count,
            "results": results,
        }

    def push_asset_async(self, asset_id: str):
        def _run():
            try:
                self.push_asset(asset_id)
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True, name="cnexus-asset-push").start()

    def receive(self, data: dict, *, peer_pubkey: str = "") -> dict:
        action = str((data or {}).get("action") or "ASSET_PUSH").upper()
        if action != "ASSET_PUSH":
            return {"ok": False, "error": "unknown_action"}

        asset_id = str(data.get("asset_id") or "").strip()
        if not asset_id:
            return {"ok": False, "error": "missing_asset_id"}

        try:
            raw = base64.b64decode(str(data.get("content_base64") or ""))
        except Exception:
            return {"ok": False, "error": "invalid_content_base64"}

        meta = {
            "id": asset_id,
            "type": data.get("type"),
            "filename": data.get("filename"),
            "summary": data.get("summary"),
            "desc": data.get("desc"),
            "size_bytes": data.get("size_bytes", len(raw)),
            "source_peer": peer_pubkey,
        }
        return self.asset_processor.ingest_remote(meta, raw, source_peer=peer_pubkey)

    def _remember(self, key: str, result: dict):
        with self._lock:
            self.last_push_results[key] = dict(result)

    def recent_results(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self.last_push_results.items()}

    def status(self) -> dict:
        queue_status = self.push_queue.status() if self.push_queue is not None else {}
        return {
            "max_push_bytes": self.max_push_bytes,
            "peer_count": len(self.trusted_peers()),
            "retry_queue": queue_status,
            "recent": self.recent_results(),
        }

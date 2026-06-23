"""Gossip sync — compare AuditLog head hashes and pull incremental deltas."""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, Optional
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


class GossipSync:
    HEARTBEAT_INTERVAL_SECONDS = 30
    PEER_STALE_SECONDS = 120

    def __init__(self, audit_log, identity_manager=None, build_signed_headers=None):
        self.audit_log = audit_log
        self.identity_manager = identity_manager
        self._build_signed_headers = build_signed_headers
        self._lock = threading.Lock()
        self.last_results: Dict[str, Dict[str, Any]] = {}
        self._heartbeat_results: Dict[str, Dict[str, Any]] = {}
        self.last_heartbeat_at: Optional[float] = None
        self.heartbeat_interval_s = self.HEARTBEAT_INTERVAL_SECONDS
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop = threading.Event()
        self._peer_registry = None
        self._negotiation = None
        self._genesis = None
        self._connectivity = None
        self._network_firewall = None

    def attach_genesis(self, genesis_sync):
        self._genesis = genesis_sync

    def attach_negotiation(self, negotiation_manager):
        self._negotiation = negotiation_manager

    def local_head(self) -> str:
        return self.audit_log.last_hash if self.audit_log else "0"

    def fetch_audit_delta(self, peer_host: str, since_hash: str, *, limit: int = 0) -> Dict[str, Any]:
        """GET /api/peer/audit?since_hash=… from a trusted peer."""
        host = _normalize_host(peer_host)
        since_hash = str(since_hash or "0")
        result: Dict[str, Any] = {
            "peer_host": host,
            "since_hash": since_hash,
            "ok": False,
            "entries": [],
            "anchor_found": False,
            "has_more": False,
        }
        if not host:
            result["error"] = "missing_peer_host"
            return result

        payload = {"since_hash": since_hash}
        if limit > 0:
            payload["limit"] = int(limit)
        query_parts = [("since_hash", since_hash)]
        if limit > 0:
            query_parts.append(("limit", str(int(limit))))
        query = urlparse.urlencode(query_parts)
        headers = {"Content-Type": "application/json"}
        if self.identity_manager and self._build_signed_headers:
            headers.update(self._build_signed_headers(self.identity_manager, payload))

        req = urlrequest.Request(f"{host}/api/peer/audit?{query}", headers=headers, method="GET")
        try:
            with urlrequest.urlopen(req, timeout=8) as resp:
                remote = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urlerror.HTTPError as exc:
            result["error"] = f"http_{exc.code}"
            return result
        except Exception as exc:
            result["error"] = str(exc)
            return result

        result.update({
            "ok": bool(remote.get("ok", True)),
            "entries": remote.get("entries") or [],
            "anchor_found": bool(remote.get("anchor_found", True)),
            "remote_head": remote.get("last_hash"),
            "entry_count": remote.get("entry_count"),
            "has_more": bool(remote.get("has_more")),
        })
        return result

    def sync_with_peer(self, peer_host: str, *, peer_pubkey: str = "") -> Dict[str, Any]:
        """Pull missing audit entries from peer and merge with chain validation."""
        local_hash = self.local_head()
        result: Dict[str, Any] = {
            "peer_host": _normalize_host(peer_host),
            "peer_pubkey": peer_pubkey,
            "local_hash_before": local_hash,
            "ok": False,
            "merged_count": 0,
            "checked_at": time.time(),
        }
        if self.audit_log is None:
            result["error"] = "audit_unavailable"
            self._remember(peer_pubkey or peer_host, result)
            return result

        delta = self.fetch_audit_delta(peer_host, local_hash)
        if not delta.get("ok"):
            result["error"] = delta.get("error") or "fetch_failed"
            self._remember(peer_pubkey or peer_host, result)
            return result

        if local_hash != "0" and not delta.get("anchor_found"):
            if self._negotiation:
                neg = self._negotiation.resolve_divergence(
                    peer_host,
                    peer_pubkey=peer_pubkey,
                    remote_head=str(delta.get("remote_head") or ""),
                )
                result["negotiation"] = neg
                if neg.get("ok"):
                    result.update({
                        "ok": True,
                        "status": neg.get("status", "negotiated"),
                        "merged_count": neg.get("merged_count", 0),
                        "local_hash_after": self.local_head(),
                    })
                    self._remember(peer_pubkey or peer_host, result)
                    return result
            result["error"] = "fork_panic"
            result["message"] = "anchor hash missing on peer — negotiation failed"
            self._remember(peer_pubkey or peer_host, result)
            return result

        entries = delta.get("entries") or []
        if not entries:
            remote_head = str(delta.get("remote_head") or "")
            if remote_head and remote_head != local_hash:
                if self._negotiation:
                    neg = self._negotiation.resolve_divergence(
                        peer_host,
                        peer_pubkey=peer_pubkey,
                        remote_head=remote_head,
                    )
                    result["negotiation"] = neg
                    if neg.get("ok"):
                        result.update({
                            "ok": True,
                            "status": neg.get("status", "negotiated"),
                            "merged_count": neg.get("merged_count", 0),
                            "local_hash_after": self.local_head(),
                        })
                        self._remember(peer_pubkey or peer_host, result)
                        return result
                result["error"] = "fork_panic"
                result["message"] = "hashes diverged — negotiation failed"
                self._remember(peer_pubkey or peer_host, result)
                return result
            result.update({"ok": True, "status": "already_aligned", "merged_count": 0})
            self._remember(peer_pubkey or peer_host, result)
            return result

        ok, msg, count = self.audit_log.merge_entries(entries, self.identity_manager)
        if not ok:
            result["error"] = "merge_failed"
            result["message"] = msg
            self._remember(peer_pubkey or peer_host, result)
            return result

        result.update({
            "ok": True,
            "status": "merged",
            "merged_count": count,
            "local_hash_after": self.local_head(),
            "message": msg,
        })
        self._remember(peer_pubkey or peer_host, result)
        return result

    def check_sync(self, peer_host: str, *, peer_pubkey: str = "") -> Dict[str, Any]:
        """POST /api/peer/sync on neighbor, compare head hash, pull delta if behind."""
        host = _normalize_host(peer_host)
        result: Dict[str, Any] = {
            "peer_host": host,
            "peer_pubkey": peer_pubkey,
            "local_hash": self.local_head(),
            "ok": False,
            "aligned": False,
            "checked_at": time.time(),
        }
        if not host:
            result["error"] = "missing_peer_host"
            return result

        payload = {"last_hash": self.local_head(), "action": "gossip_check"}
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.identity_manager and self._build_signed_headers:
            headers.update(self._build_signed_headers(self.identity_manager, payload))

        req = urlrequest.Request(f"{host}/api/peer/sync", data=body, headers=headers, method="POST")
        try:
            with urlrequest.urlopen(req, timeout=8) as resp:
                remote = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urlerror.HTTPError as exc:
            result["error"] = f"http_{exc.code}"
            self._remember(peer_pubkey or host, result)
            return result
        except Exception as exc:
            result["error"] = str(exc)
            self._remember(peer_pubkey or host, result)
            return result

        remote_hash = str(remote.get("last_hash") or "")
        local_hash = self.local_head()
        local_entries = self.audit_log.entry_count() if self.audit_log else 0
        remote_entries = int(remote.get("audit_entries") or 0)
        aligned = remote_hash == local_hash

        result.update({
            "ok": bool(remote.get("ok", True)),
            "remote_hash": remote_hash,
            "aligned": aligned,
            "remote_pubkey": remote.get("node_pubkey"),
            "remote_audit_entries": remote_entries,
            "local_audit_entries": local_entries,
        })

        if not aligned:
            if remote_entries > local_entries:
                merge = self.sync_with_peer(host, peer_pubkey=peer_pubkey)
                result["merge"] = merge
                result["aligned"] = merge.get("ok") and self.local_head() == remote_hash
                result["local_hash"] = self.local_head()
            else:
                if self._negotiation:
                    neg = self._negotiation.resolve_divergence(
                        host,
                        peer_pubkey=peer_pubkey,
                        remote_head=remote_hash,
                        remote_entries=remote_entries,
                    )
                    result["negotiation"] = neg
                    if neg.get("ok"):
                        result["aligned"] = self.local_head() == remote_hash
                        result["local_hash"] = self.local_head()
                        result["error"] = None
                    else:
                        result["error"] = neg.get("error") or "negotiation_failed"
                        result["message"] = neg.get("message") or "consensus could not resolve fork"
                else:
                    result["error"] = "fork_panic"
                    result["message"] = (
                        "audit head mismatch with peer — not behind; manual intervention required"
                    )

        self._remember(peer_pubkey or host, result)
        return result

    def _remember(self, key: str, result: dict):
        with self._lock:
            self.last_results[key] = dict(result)

    def schedule_check(self, peer_host: str, *, peer_pubkey: str = "", genesis: bool = False):
        """Fire-and-forget gossip check (non-blocking). Optionally run genesis handshake."""

        def _run():
            if genesis and self._genesis:
                self._genesis.schedule_genesis_handshake(peer_host, peer_pubkey=peer_pubkey)
            else:
                self.check_sync(peer_host, peer_pubkey=peer_pubkey)

        threading.Thread(target=_run, daemon=True, name="cnexus-gossip-sync").start()

    def schedule_genesis_bootstrap(self):
        if self._genesis:
            self._genesis.schedule_bootstrap(self._peer_registry)

    def recent_results(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self.last_results.items()}

    def heartbeat_results(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._heartbeat_results.items()}

    def attach_peer_registry(self, peer_registry):
        self._peer_registry = peer_registry

    def attach_connectivity(self, connectivity_manager, network_firewall=None):
        self._connectivity = connectivity_manager
        self._network_firewall = network_firewall

    def _resolve_peer_host(self, pubkey: str, host: str) -> str:
        if self._connectivity is not None:
            resolved = self._connectivity.resolve_host(pubkey)
            if resolved:
                return resolved
        return _normalize_host(host)

    def ping_peer(self, peer_host: str) -> Dict[str, Any]:
        """Lightweight latency probe via /v1/health."""
        host = _normalize_host(peer_host)
        started = time.time()
        if not host:
            return {"ok": False, "error": "missing_peer_host", "latency_ms": None}
        req = urlrequest.Request(f"{host}/v1/health", method="GET")
        try:
            with urlrequest.urlopen(req, timeout=5) as resp:
                resp.read()
            latency_ms = int((time.time() - started) * 1000)
            return {"ok": True, "latency_ms": latency_ms, "checked_at": time.time()}
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "latency_ms": None,
                "checked_at": time.time(),
            }

    def heartbeat_peer(self, pubkey: str, peer_host: str) -> Dict[str, Any]:
        result = self.ping_peer(peer_host)
        result["pubkey"] = pubkey
        result["host"] = _normalize_host(peer_host)
        registry = self._peer_registry
        if registry is not None:
            if result.get("ok"):
                registry.touch_peer(pubkey)
                registry.set_peer_status(pubkey, "online")
            else:
                registry.set_peer_status(pubkey, "offline")
        return result

    def run_heartbeat(self) -> Dict[str, Dict[str, Any]]:
        registry = self._peer_registry
        peers = registry.get_all_peers() if registry else {}
        if self._network_firewall is not None:
            peers = self._network_firewall.filter_peers(peers)
        results: Dict[str, Dict[str, Any]] = {}
        for pubkey, meta in peers.items():
            host = self._resolve_peer_host(pubkey, str(meta.get("host") or ""))
            if not host and self._connectivity is not None:
                connect = self._connectivity.connect_to(pubkey)
                host = str(connect.get("url") or "")
            row = self.heartbeat_peer(pubkey, host)
            results[pubkey] = row
            if row.get("ok"):
                self.check_sync(host, peer_pubkey=pubkey)
            elif self._connectivity is not None:
                self._connectivity.on_connection_lost(pubkey)
        with self._lock:
            self._heartbeat_results = results
            self.last_heartbeat_at = time.time()
        return results

    def start_heartbeat_loop(self, peer_registry=None, *, interval: Optional[float] = None):
        if peer_registry is not None:
            self.attach_peer_registry(peer_registry)
        if interval is not None:
            self.heartbeat_interval_s = float(interval)
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()

        def _loop():
            while not self._heartbeat_stop.wait(self.heartbeat_interval_s):
                try:
                    self.run_heartbeat()
                except Exception:
                    pass

        self._heartbeat_thread = threading.Thread(
            target=_loop,
            daemon=True,
            name="cnexus-peer-heartbeat",
        )
        self._heartbeat_thread.start()

    def stop_heartbeat_loop(self):
        self._heartbeat_stop.set()

    def get_health_status(self) -> Dict[str, Any]:
        with self._lock:
            gossip = {k: dict(v) for k, v in self.last_results.items()}
            heartbeat = {k: dict(v) for k, v in self._heartbeat_results.items()}
        online = sum(1 for row in heartbeat.values() if row.get("ok"))
        aligned = sum(1 for row in gossip.values() if row.get("aligned"))
        forks = sum(1 for row in gossip.values() if row.get("error") == "fork_panic")
        genesis_status = self._genesis.status() if self._genesis else {}
        return {
            "last_heartbeat_at": self.last_heartbeat_at,
            "heartbeat_interval_s": self.heartbeat_interval_s,
            "peer_count": len(heartbeat),
            "online_count": online,
            "aligned_count": aligned,
            "fork_panic_count": forks,
            "genesis": genesis_status,
            "gossip_recent": gossip,
            "heartbeat_recent": heartbeat,
        }

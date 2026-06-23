"""Genesis handshake — full AuditLog replication on peer connect / boot."""

from __future__ import annotations

import json
import os
import random
import threading
import time
from typing import Any, Callable, Dict, Optional
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def compute_resilience_score(
    *,
    peer_rows: list,
    local_integrity_ok: bool = True,
    genesis_full_sync: int = 0,
) -> Dict[str, Any]:
    """
    Network resilience = fully replicated nodes / total nodes in the mesh.
    Local node counts when audit integrity is OK.
    """
    online_peers = [row for row in peer_rows if row.get("status") == "online"]
    aligned_peers = [row for row in online_peers if row.get("aligned")]
    total_nodes = 1 + len(peer_rows)
    full_sync_nodes = (1 if local_integrity_ok else 0) + len(aligned_peers)
    if genesis_full_sync > full_sync_nodes:
        full_sync_nodes = genesis_full_sync
    score = full_sync_nodes / total_nodes if total_nodes else 1.0
    label = "critical"
    if score >= 0.9:
        label = "fortress"
    elif score >= 0.67:
        label = "strong"
    elif score >= 0.34:
        label = "recovering"
    return {
        "score": round(score, 3),
        "full_sync_nodes": full_sync_nodes,
        "total_nodes": total_nodes,
        "online_nodes": len(online_peers),
        "aligned_nodes": len(aligned_peers),
        "local_integrity_ok": local_integrity_ok,
        "label": label,
    }


class GenesisSync:
    """Boot-time and peer-connect full AuditLog mirror with jittered anti-storm sync."""

    def __init__(
        self,
        gossip_sync,
        *,
        chunk_size: Optional[int] = None,
        jitter_min: Optional[float] = None,
        jitter_max: Optional[float] = None,
        enabled: Optional[bool] = None,
        on_aligned: Optional[Callable[[dict], None]] = None,
    ):
        self.gossip = gossip_sync
        self.on_aligned = on_aligned
        self.chunk_size = chunk_size if chunk_size is not None else _env_int("CNEXUS_GENESIS_CHUNK", 200)
        self.jitter_min = jitter_min if jitter_min is not None else _env_float("CNEXUS_GENESIS_JITTER_MIN", 1.0)
        self.jitter_max = jitter_max if jitter_max is not None else _env_float("CNEXUS_GENESIS_JITTER_MAX", 5.0)
        self.enabled = enabled if enabled is not None else _env_truthy("CNEXUS_GENESIS_ENABLE", True)
        self._lock = threading.Lock()
        self._genesis_results: Dict[str, Dict[str, Any]] = {}
        self._last_bootstrap_at: Optional[float] = None
        self._bootstrap_started = False

    def fetch_peer_head(self, peer_host: str, *, peer_pubkey: str = "") -> Dict[str, Any]:
        gossip = self.gossip
        host = _normalize_host(peer_host)
        result: Dict[str, Any] = {
            "peer_host": host,
            "peer_pubkey": peer_pubkey,
            "ok": False,
            "checked_at": time.time(),
        }
        if not host or gossip is None:
            result["error"] = "gossip_unavailable"
            return result

        payload = {"action": "GENESIS_HANDSHAKE", "last_hash": gossip.local_head()}
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if gossip.identity_manager and gossip._build_signed_headers:
            headers.update(gossip._build_signed_headers(gossip.identity_manager, payload))

        req = urlrequest.Request(f"{host}/api/peer/sync", data=body, headers=headers, method="POST")
        try:
            with urlrequest.urlopen(req, timeout=10) as resp:
                remote = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urlerror.HTTPError as exc:
            result["error"] = f"http_{exc.code}"
            return result
        except Exception as exc:
            result["error"] = str(exc)
            return result

        result.update({
            "ok": bool(remote.get("ok", True)),
            "remote_head": str(remote.get("last_hash") or ""),
            "remote_audit_entries": int(remote.get("audit_entries") or 0),
            "remote_pubkey": remote.get("node_pubkey"),
            "integrity_ok": remote.get("integrity_ok", True),
        })
        return result

    def request_full_log(self, peer_host: str, *, peer_pubkey: str = "", remote_head: str = "") -> Dict[str, Any]:
        gossip = self.gossip
        result: Dict[str, Any] = {
            "peer_host": _normalize_host(peer_host),
            "peer_pubkey": peer_pubkey,
            "ok": False,
            "merged_total": 0,
            "chunks": 0,
            "checked_at": time.time(),
            "phase": "genesis_full_log",
        }
        if gossip is None or gossip.audit_log is None:
            result["error"] = "audit_unavailable"
            return result

        remote_head = str(remote_head or "")
        local_before = gossip.local_head()
        since_hash = "0" if gossip.audit_log.entry_count() == 0 else local_before
        merged_total = 0
        chunks = 0
        max_chunks = max(10, _env_int("CNEXUS_GENESIS_MAX_CHUNKS", 500))

        while chunks < max_chunks:
            delta = gossip.fetch_audit_delta(peer_host, since_hash, limit=self.chunk_size)
            if not delta.get("ok"):
                result["error"] = delta.get("error") or "fetch_failed"
                result["merged_total"] = merged_total
                result["chunks"] = chunks
                return result

            if since_hash != "0" and not delta.get("anchor_found"):
                if gossip._negotiation:
                    neg = gossip._negotiation.resolve_divergence(
                        peer_host,
                        peer_pubkey=peer_pubkey,
                        remote_head=str(delta.get("remote_head") or remote_head),
                    )
                    result["negotiation"] = neg
                    if neg.get("ok"):
                        result.update({
                            "ok": True,
                            "status": "genesis_negotiated",
                            "merged_total": neg.get("merged_count", 0),
                            "local_head_after": gossip.local_head(),
                        })
                        return result
                result["error"] = "genesis_anchor_missing"
                return result

            entries = delta.get("entries") or []
            if not entries:
                break

            ok, msg, count = gossip.audit_log.merge_entries(entries, gossip.identity_manager)
            chunks += 1
            if not ok:
                result["error"] = "merge_failed"
                result["message"] = msg
                result["merged_total"] = merged_total
                result["chunks"] = chunks
                return result

            merged_total += count
            since_hash = gossip.local_head()
            remote_head = str(delta.get("remote_head") or remote_head)
            if since_hash == remote_head:
                break
            if not delta.get("has_more", len(entries) >= self.chunk_size):
                if since_hash == gossip.local_head() and remote_head and since_hash == remote_head:
                    break
                if len(entries) < self.chunk_size:
                    break

        aligned = bool(remote_head and gossip.local_head() == remote_head)
        result.update({
            "ok": True,
            "status": "genesis_complete" if aligned else "genesis_partial",
            "merged_total": merged_total,
            "chunks": chunks,
            "local_head_before": local_before,
            "local_head_after": gossip.local_head(),
            "remote_head": remote_head,
            "aligned": aligned,
        })
        return result

    def genesis_handshake(self, peer_host: str, *, peer_pubkey: str = "") -> Dict[str, Any]:
        gossip = self.gossip
        result: Dict[str, Any] = {
            "peer_host": _normalize_host(peer_host),
            "peer_pubkey": peer_pubkey,
            "ok": False,
            "phase": "genesis_handshake",
            "checked_at": time.time(),
        }
        if not self.enabled:
            result["error"] = "genesis_disabled"
            return result
        if gossip is None:
            result["error"] = "gossip_unavailable"
            return result

        local_head = gossip.local_head()
        local_entries = gossip.audit_log.entry_count() if gossip.audit_log else 0
        head = self.fetch_peer_head(peer_host, peer_pubkey=peer_pubkey)
        result["head_probe"] = head
        if not head.get("ok"):
            result["error"] = head.get("error") or "head_probe_failed"
            self._remember(peer_pubkey or peer_host, result)
            return result

        remote_head = str(head.get("remote_head") or "")
        remote_entries = int(head.get("remote_audit_entries") or 0)
        result.update({
            "local_head": local_head,
            "remote_head": remote_head,
            "local_entries": local_entries,
            "remote_entries": remote_entries,
        })

        if local_head == remote_head:
            result.update({"ok": True, "status": "already_full_sync", "aligned": True})
            self._remember(peer_pubkey or peer_host, result)
            return result

        if remote_entries > local_entries or local_entries == 0:
            full = self.request_full_log(
                peer_host,
                peer_pubkey=peer_pubkey,
                remote_head=remote_head,
            )
            result["full_log"] = full
            result["ok"] = bool(full.get("ok"))
            result["aligned"] = bool(full.get("aligned"))
            result["status"] = full.get("status", "genesis_failed")
            if not full.get("ok"):
                result["error"] = full.get("error")
        elif gossip._negotiation:
            neg = gossip._negotiation.resolve_divergence(
                peer_host,
                peer_pubkey=peer_pubkey,
                remote_head=remote_head,
                remote_entries=remote_entries,
            )
            result["negotiation"] = neg
            result["ok"] = bool(neg.get("ok"))
            result["aligned"] = gossip.local_head() == remote_head
            result["status"] = "genesis_negotiated" if neg.get("ok") else "genesis_fork"
            if not neg.get("ok"):
                result["error"] = neg.get("error") or "negotiation_failed"
        else:
            result["error"] = "genesis_fork_no_negotiation"
            result["status"] = "genesis_fork"

        self._remember(peer_pubkey or peer_host, result)
        if hasattr(gossip, "_remember"):
            gossip._remember(peer_pubkey or peer_host, {
                "peer_host": result["peer_host"],
                "peer_pubkey": peer_pubkey,
                "local_hash": gossip.local_head(),
                "remote_hash": remote_head,
                "aligned": result.get("aligned"),
                "ok": result.get("ok"),
                "checked_at": result["checked_at"],
                "genesis": True,
                "status": result.get("status"),
            })
        if self.on_aligned and result.get("ok"):
            try:
                self.on_aligned(result)
            except Exception:
                pass
        return result

    def schedule_genesis_handshake(self, peer_host: str, *, peer_pubkey: str = ""):
        delay = random.uniform(self.jitter_min, self.jitter_max)

        def _run():
            time.sleep(delay)
            try:
                self.genesis_handshake(peer_host, peer_pubkey=peer_pubkey)
            except Exception:
                pass

        threading.Thread(
            target=_run,
            daemon=True,
            name=f"cnexus-genesis-{peer_pubkey[:8] if peer_pubkey else 'peer'}",
        ).start()

    def schedule_bootstrap(self, peer_registry=None):
        if not self.enabled:
            return
        registry = peer_registry or getattr(self.gossip, "_peer_registry", None)
        peers = registry.get_all_peers() if registry else {}
        if not peers:
            return
        with self._lock:
            if self._bootstrap_started:
                return
            self._bootstrap_started = True
            self._last_bootstrap_at = time.time()

        for pubkey, meta in peers.items():
            host = str(meta.get("host") or "")
            if host:
                self.schedule_genesis_handshake(host, peer_pubkey=pubkey)

    def _remember(self, key: str, result: dict):
        with self._lock:
            self._genesis_results[key] = dict(result)

    def recent_results(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._genesis_results.items()}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            results = dict(self._genesis_results)
            bootstrap_at = self._last_bootstrap_at
        full_sync = sum(1 for row in results.values() if row.get("aligned") or row.get("status") == "already_full_sync")
        return {
            "enabled": self.enabled,
            "chunk_size": self.chunk_size,
            "jitter_s": [self.jitter_min, self.jitter_max],
            "last_bootstrap_at": bootstrap_at,
            "peer_results": results,
            "full_sync_peers": full_sync,
        }

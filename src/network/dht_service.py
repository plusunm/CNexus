"""Kademlia-style DHT for decentralized peer discovery (HTTP RPC transport)."""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest


K_BUCKET_SIZE = 20
ID_BITS = 160


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def peer_id(pubkey: str) -> str:
    return hashlib.sha256(str(pubkey or "").encode("utf-8")).hexdigest()[:ID_BITS // 4]


def xor_distance(id_a: str, id_b: str) -> int:
    a = int(str(id_a or "0"), 16)
    b = int(str(id_b or "0"), 16)
    return a ^ b


def bucket_index(local_id: str, node_id: str) -> int:
    dist = xor_distance(local_id, node_id)
    if dist == 0:
        return 0
    return min(159, dist.bit_length() - 1)


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


class DHTService:
    """Simplified Kademlia routing table + FIND_NODE / STORE over CNexus HTTP."""

    def __init__(
        self,
        local_pubkey: str,
        *,
        peer_registry=None,
        bootstrap_hosts: Optional[List[str]] = None,
        http_post: Optional[Callable[[str, dict], dict]] = None,
        enabled: Optional[bool] = None,
    ):
        self.local_pubkey = str(local_pubkey or "")
        self.local_id = peer_id(self.local_pubkey) if self.local_pubkey else ""
        self.peer_registry = peer_registry
        self.bootstrap_hosts = bootstrap_hosts or self._parse_bootstrap()
        self._http_post = http_post
        self.enabled = enabled if enabled is not None else _env_truthy("CNEXUS_DHT_ENABLE", True)
        self._lock = threading.Lock()
        self._buckets: Dict[int, Dict[str, dict]] = {}
        self._store: Dict[str, dict] = {}
        self.last_lookup: Dict[str, Any] = {}

    @staticmethod
    def _parse_bootstrap() -> List[str]:
        raw = os.environ.get("CNEXUS_DHT_BOOTSTRAP", "")
        return [_normalize_host(part) for part in str(raw or "").split(",") if part.strip()]

    def _touch_node(self, node_pubkey: str, host: str, *, endpoints: Optional[List[str]] = None):
        if not node_pubkey or node_pubkey == self.local_pubkey:
            return
        node_id = peer_id(node_pubkey)
        record = {
            "pubkey": node_pubkey,
            "id": node_id,
            "host": _normalize_host(host),
            "endpoints": endpoints or [_normalize_host(host)],
            "last_seen": time.time(),
        }
        idx = bucket_index(self.local_id, node_id)
        with self._lock:
            bucket = self._buckets.setdefault(idx, {})
            bucket[node_pubkey] = record
            if len(bucket) > K_BUCKET_SIZE:
                oldest = min(bucket.items(), key=lambda item: item[1].get("last_seen", 0))[0]
                bucket.pop(oldest, None)

    def seed_from_registry(self):
        if not self.peer_registry:
            return 0
        count = 0
        for pubkey, meta in self.peer_registry.get_all_peers().items():
            host = str(meta.get("host") or "")
            if host:
                self._touch_node(pubkey, host, endpoints=meta.get("endpoints"))
                count += 1
        return count

    def announce(self, host: str, *, endpoints: Optional[List[str]] = None):
        if not self.local_pubkey:
            return
        eps = list(endpoints or [_normalize_host(host)])
        self._store[self.local_id] = {
            "pubkey": self.local_pubkey,
            "host": _normalize_host(host),
            "endpoints": eps,
            "announced_at": time.time(),
        }
        self._touch_node(self.local_pubkey, host, endpoints=eps)

    def closest_nodes(self, target_id: str, *, limit: int = K_BUCKET_SIZE) -> List[dict]:
        target_id = str(target_id or "")
        rows: List[dict] = []
        with self._lock:
            for bucket in self._buckets.values():
                rows.extend(dict(row) for row in bucket.values())
        rows.sort(key=lambda row: xor_distance(target_id, row.get("id") or ""))
        return rows[: max(1, limit)]

    def find_node(self, target_pubkey: str, *, max_hops: int = 3) -> Optional[dict]:
        if not self.enabled:
            return None
        target_id = peer_id(target_pubkey)
        with self._lock:
            for bucket in self._buckets.values():
                if target_pubkey in bucket:
                    self.last_lookup = {"ok": True, "source": "local_bucket", "pubkey": target_pubkey}
                    return dict(bucket[target_pubkey])

        stored = self._store.get(target_id)
        if stored and stored.get("pubkey") == target_pubkey:
            self.last_lookup = {"ok": True, "source": "local_store", "pubkey": target_pubkey}
            return dict(stored)

        candidates = self.closest_nodes(target_id)
        for row in candidates:
            if row.get("pubkey") == target_pubkey:
                self.last_lookup = {"ok": True, "source": "closest", "pubkey": target_pubkey}
                return row

        if self._http_post:
            for row in candidates[: max_hops]:
                host = str(row.get("host") or "")
                if not host:
                    continue
                try:
                    remote = self._http_post(
                        host,
                        {
                            "action": "FIND_NODE",
                            "target_id": target_id,
                            "target_pubkey": target_pubkey,
                            "requester": self.local_pubkey,
                        },
                    )
                    for contact in remote.get("nodes") or []:
                        self._touch_node(
                            str(contact.get("pubkey") or ""),
                            str(contact.get("host") or ""),
                            endpoints=contact.get("endpoints"),
                        )
                        if str(contact.get("pubkey") or "") == target_pubkey:
                            self.last_lookup = {"ok": True, "source": "dht_rpc", "pubkey": target_pubkey}
                            return dict(contact)
                except Exception:
                    continue

        self.last_lookup = {"ok": False, "pubkey": target_pubkey}
        return None

    def handle_rpc(self, payload: dict) -> dict:
        action = str((payload or {}).get("action") or "").upper()
        if action == "PING":
            return {"ok": True, "action": "PONG", "id": self.local_id, "pubkey": self.local_pubkey}
        if action == "FIND_NODE":
            target_id = str(payload.get("target_id") or peer_id(str(payload.get("target_pubkey") or "")))
            nodes = self.closest_nodes(target_id)
            return {"ok": True, "action": "FIND_NODE", "nodes": nodes, "id": self.local_id}
        if action == "STORE":
            key = str(payload.get("key") or "")
            value = dict(payload.get("value") or {})
            if key and value.get("pubkey"):
                self._store[key] = value
                self._touch_node(
                    str(value.get("pubkey")),
                    str(value.get("host") or ""),
                    endpoints=value.get("endpoints"),
                )
            return {"ok": True, "action": "STORE", "stored": bool(key)}
        if action == "FIND_VALUE":
            key = str(payload.get("key") or "")
            value = self._store.get(key)
            if value:
                return {"ok": True, "action": "FIND_VALUE", "value": value}
            target_id = key
            return {"ok": True, "action": "FIND_VALUE", "nodes": self.closest_nodes(target_id)}
        return {"ok": False, "error": "unknown_dht_action"}

    def bootstrap(self) -> dict:
        if not self.enabled:
            return {"ok": False, "error": "dht_disabled"}
        touched = self.seed_from_registry()
        contacted = 0
        for host in self.bootstrap_hosts:
            if not host:
                continue
            if self._http_post:
                try:
                    resp = self._http_post(host, {"action": "PING", "pubkey": self.local_pubkey})
                    if resp.get("ok"):
                        contacted += 1
                        self._http_post(
                            host,
                            {
                                "action": "FIND_NODE",
                                "target_id": self.local_id,
                                "requester": self.local_pubkey,
                            },
                        )
                except Exception:
                    continue
        return {"ok": True, "registry_seeded": touched, "bootstrap_contacted": contacted}

    def status(self) -> dict:
        with self._lock:
            bucket_sizes = {str(k): len(v) for k, v in self._buckets.items()}
            node_count = sum(len(v) for v in self._buckets.values())
        return {
            "enabled": self.enabled,
            "local_id": self.local_id,
            "node_count": node_count,
            "bucket_sizes": bucket_sizes,
            "bootstrap_hosts": self.bootstrap_hosts,
            "stored_values": len(self._store),
            "last_lookup": dict(self.last_lookup),
        }

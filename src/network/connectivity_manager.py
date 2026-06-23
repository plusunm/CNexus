"""Connectivity manager — ICE-like candidate gathering, path selection, relay fallback."""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest


StunGatherFn = Callable[[], Optional[Dict[str, object]]]


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


class PathKind(str, Enum):
    DIRECT = "direct"
    SRFLX = "srflx"
    RELAY = "relay"
    UNKNOWN = "unknown"


class ConnectionPath:
    def __init__(
        self,
        peer_id: str,
        url: str,
        *,
        kind: PathKind = PathKind.UNKNOWN,
        priority: int = 0,
        nat_hint: str = "",
    ):
        self.peer_id = peer_id
        self.url = _normalize_host(url)
        self.kind = kind
        self.priority = priority
        self.nat_hint = nat_hint
        self.latency_ms: Optional[float] = None
        self.ok = False
        self.last_check = 0.0

    def is_direct(self) -> bool:
        return self.kind == PathKind.DIRECT

    def is_stun_punchable(self) -> bool:
        return self.kind == PathKind.SRFLX

    def is_relay(self) -> bool:
        return self.kind == PathKind.RELAY

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "url": self.url,
            "kind": self.kind.value,
            "priority": self.priority,
            "nat_hint": self.nat_hint,
            "latency_ms": self.latency_ms,
            "ok": self.ok,
            "last_check": self.last_check,
        }


class ConnectivityManager:
    """
    State machine for autonomous addressing and multi-path connectivity.
    Layer 1: physical topology (below Gossip/Genesis handshake).
    """

    def __init__(
        self,
        *,
        local_pubkey: str = "",
        local_port: int = 7864,
        bind_host: str = "127.0.0.1",
        public_url: str = "",
        dht_service=None,
        peer_registry=None,
        network_firewall=None,
        relay_url: str = "",
        stun_gather_fn: Optional[StunGatherFn] = None,
        enabled: Optional[bool] = None,
    ):
        self.local_pubkey = str(local_pubkey or "")
        self.local_port = int(local_port)
        self.bind_host = str(bind_host or "127.0.0.1")
        self.public_url = _normalize_host(public_url)
        self.dht = dht_service
        self.peer_registry = peer_registry
        self.firewall = network_firewall
        self.relay_url = _normalize_host(relay_url or os.environ.get("CNEXUS_RELAY_URL", ""))
        self._stun_gather = stun_gather_fn
        self.enabled = enabled if enabled is not None else _env_truthy("CNEXUS_CONNECTIVITY_ENABLE", True)
        self._lock = threading.Lock()
        self._local_candidates: List[dict] = []
        self._paths: Dict[str, List[ConnectionPath]] = {}
        self._nat_type = "unknown"
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_stop = threading.Event()
        self.last_connect_report: Dict[str, Any] = {}

    def _local_host_candidate(self) -> dict:
        if self.bind_host in ("0.0.0.0", "::"):
            host_ip = "127.0.0.1"
        else:
            host_ip = self.bind_host
        url = self.public_url or f"http://{host_ip}:{self.local_port}"
        return {"type": "host", "url": url, "priority": 100}

    def gather_candidates(self, *, refresh_stun: bool = True) -> List[dict]:
        candidates = [self._local_host_candidate()]
        if self.public_url:
            candidates.append({"type": "host", "url": self.public_url, "priority": 110})

        if refresh_stun and self._stun_gather:
            srflx = self._stun_gather()
            if srflx and srflx.get("ok"):
                ip = str(srflx.get("ip") or "")
                candidates.append({
                    "type": "srflx",
                    "url": f"http://{ip}:{self.local_port}",
                    "ip": ip,
                    "port": self.local_port,
                    "priority": 80,
                    "nat_hint": srflx.get("nat_hint", "srflx"),
                })
                self._nat_type = "cone" if srflx.get("ok") else "symmetric"
            else:
                self._nat_type = "symmetric_or_blocked"

        if self.relay_url:
            candidates.append({"type": "relay", "url": self.relay_url, "priority": 30})

        with self._lock:
            self._local_candidates = list(candidates)
        return candidates

    def _probe_url(self, url: str, *, timeout: float = 4.0) -> tuple[bool, Optional[float]]:
        url = _normalize_host(url)
        if not url:
            return False, None
        health = f"{url}/v1/health"
        start = time.time()
        try:
            req = urlrequest.Request(health, method="GET")
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                ok = int(getattr(resp, "status", 200) or 200) < 500
            return ok, (time.time() - start) * 1000.0
        except (urlerror.URLError, urlerror.HTTPError, TimeoutError, OSError):
            return False, None

    def _paths_for_peer(self, peer_id: str, node: Optional[dict]) -> List[ConnectionPath]:
        peer_id = str(peer_id or "")
        paths: List[ConnectionPath] = []
        if node:
            endpoints = list(node.get("endpoints") or [])
            host = str(node.get("host") or "")
            if host:
                endpoints.insert(0, host)
            seen = set()
            for raw in endpoints:
                url = _normalize_host(str(raw or ""))
                if not url or url in seen:
                    continue
                seen.add(url)
                paths.append(ConnectionPath(peer_id, url, kind=PathKind.DIRECT, priority=90))
        if self.peer_registry:
            meta = self.peer_registry.get_peer(peer_id) or {}
            host = str(meta.get("host") or "")
            if host:
                url = _normalize_host(host)
                if url not in {p.url for p in paths}:
                    paths.append(ConnectionPath(peer_id, url, kind=PathKind.DIRECT, priority=85))
        if self.relay_url:
            paths.append(ConnectionPath(peer_id, self.relay_url, kind=PathKind.RELAY, priority=20))
        paths.sort(key=lambda p: p.priority, reverse=True)
        return paths

    def ice_negotiation(self, peer_id: str, node: Optional[dict] = None) -> List[ConnectionPath]:
        paths = self._paths_for_peer(peer_id, node)
        for path in paths:
            ok, latency = self._probe_url(path.url)
            path.ok = ok
            path.latency_ms = latency
            path.last_check = time.time()
            if ok and path.kind == PathKind.SRFLX:
                path.nat_hint = "punchable"
        with self._lock:
            self._paths[peer_id] = paths
        return paths

    def connect_to(self, peer_id: str) -> dict:
        if not self.enabled:
            return {"ok": False, "error": "connectivity_disabled"}
        peer_id = str(peer_id or "").strip()
        if not peer_id:
            return {"ok": False, "error": "missing_peer_id"}

        status = "trusted"
        if self.peer_registry:
            meta = self.peer_registry.get_peer(peer_id) or {}
            status = str(meta.get("status") or "discovered")
        if self.firewall:
            allowed, reason = self.firewall.allow_connection(peer_id, status=status)
            if not allowed:
                report = {"ok": False, "error": reason, "peer_id": peer_id, "phase": "firewall"}
                self.last_connect_report = report
                return report

        node = self.dht.find_node(peer_id) if self.dht else None
        paths = self.ice_negotiation(peer_id, node)
        chosen: Optional[ConnectionPath] = None
        for path in paths:
            if path.ok and path.is_direct():
                chosen = path
                break
        if chosen is None:
            for path in paths:
                if path.ok and path.is_stun_punchable():
                    chosen = path
                    break
        if chosen is None:
            for path in paths:
                if path.ok and path.is_relay():
                    chosen = path
                    break
        if chosen is None:
            for path in paths:
                if path.ok:
                    chosen = path
                    break

        report: Dict[str, Any] = {
            "ok": bool(chosen),
            "peer_id": peer_id,
            "dht_hit": bool(node),
            "paths": [p.to_dict() for p in paths],
            "nat_type": self._nat_type,
            "at": time.time(),
        }
        if chosen:
            report["url"] = chosen.url
            report["path_kind"] = chosen.kind.value
            if self.peer_registry:
                self.peer_registry.save_peer(peer_id, chosen.url, status=status if status != "unknown" else "discovered")
                endpoints = list((self.peer_registry.get_peer(peer_id) or {}).get("endpoints") or [])
                if chosen.url not in endpoints:
                    endpoints.append(chosen.url)
                self.peer_registry.update_peer(
                    peer_id,
                    endpoints=endpoints,
                    nat_type=self._nat_type,
                    path_kind=chosen.kind.value,
                )
        else:
            report["error"] = "no_viable_path"

        self.last_connect_report = report
        return report

    def on_connection_lost(self, peer_id: str) -> dict:
        peer_id = str(peer_id or "")
        with self._lock:
            paths = list(self._paths.get(peer_id) or [])
        for path in paths:
            path.ok = False
        return self.connect_to(peer_id)

    def resolve_host(self, peer_id: str) -> str:
        with self._lock:
            paths = self._paths.get(peer_id) or []
        for path in paths:
            if path.ok:
                return path.url
        if self.peer_registry:
            meta = self.peer_registry.get_peer(peer_id) or {}
            return _normalize_host(str(meta.get("host") or ""))
        return ""

    def start_worker(self, interval: float = 120.0):
        if not self.enabled:
            return
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._worker_stop.clear()

        def _loop():
            while not self._worker_stop.wait(max(30.0, interval)):
                try:
                    self.gather_candidates(refresh_stun=True)
                    if self.dht:
                        self.dht.bootstrap()
                except Exception:
                    pass

        self._worker_thread = threading.Thread(
            target=_loop,
            daemon=True,
            name="cnexus-connectivity",
        )
        self._worker_thread.start()

    def status(self) -> dict:
        with self._lock:
            candidates = list(self._local_candidates)
            path_count = sum(len(v) for v in self._paths.values())
        return {
            "enabled": self.enabled,
            "local_pubkey": self.local_pubkey[:16] + "…" if self.local_pubkey else "",
            "bind_host": self.bind_host,
            "public_url": self.public_url,
            "nat_type": self._nat_type,
            "relay_url": self.relay_url or None,
            "candidates": candidates,
            "active_paths": path_count,
            "last_connect": dict(self.last_connect_report),
        }

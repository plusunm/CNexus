"""CNexus Mission Control — runtime metrics and network topology snapshots."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional


def collect_system_resources() -> Dict[str, Any]:
    """CPU/RAM snapshot. Uses psutil when installed, else graceful fallback."""
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        return {
            "available": True,
            "cpu_percent": round(psutil.cpu_percent(interval=None), 1),
            "memory_percent": round(vm.percent, 1),
            "memory_used_mb": round(vm.used / (1024 * 1024), 1),
            "memory_total_mb": round(vm.total / (1024 * 1024), 1),
        }
    except Exception:
        return {
            "available": False,
            "cpu_percent": None,
            "memory_percent": None,
            "memory_used_mb": None,
            "memory_total_mb": None,
        }


def _short_hash(value: str, length: int = 12) -> str:
    text = str(value or "")
    if len(text) <= length:
        return text
    return text[:length] + "…"


def enrich_peers(
    peers: Dict[str, Dict[str, Any]],
    gossip_results: Dict[str, Dict[str, Any]],
    heartbeat_results: Dict[str, Dict[str, Any]],
    *,
    stale_seconds: float = 120.0,
    now: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Merge registry, gossip, and heartbeat into dashboard peer rows."""
    now = time.time() if now is None else now
    rows: List[Dict[str, Any]] = []
    for pubkey, meta in peers.items():
        host = str(meta.get("host") or "")
        gossip = gossip_results.get(pubkey) or gossip_results.get(host) or {}
        ping = heartbeat_results.get(pubkey) or {}
        last_seen = float(meta.get("last_seen") or 0)
        age = now - last_seen if last_seen else None
        ping_ok = bool(ping.get("ok"))
        stale = age is None or age > stale_seconds
        online = ping_ok and not stale
        aligned = bool(gossip.get("aligned"))
        fork = str(gossip.get("error") or "") == "fork_panic"
        rows.append({
            "pubkey": pubkey,
            "pubkey_short": _short_hash(pubkey, 16),
            "host": host,
            "status": "online" if online else ("fork" if fork else "offline"),
            "registry_status": meta.get("status", "unknown"),
            "last_seen": last_seen,
            "last_seen_ago_s": round(age, 1) if age is not None else None,
            "latency_ms": ping.get("latency_ms"),
            "ping_ok": ping_ok,
            "aligned": aligned,
            "fork_panic": fork,
            "local_hash": gossip.get("local_hash"),
            "remote_hash": gossip.get("remote_hash"),
            "remote_audit_entries": gossip.get("remote_audit_entries"),
            "merge_status": (gossip.get("merge") or {}).get("status"),
            "gossip_error": gossip.get("error"),
            "checked_at": gossip.get("checked_at"),
        })
    rows.sort(key=lambda row: (row["status"] != "online", row.get("latency_ms") or 99999))
    return rows


def build_topology(
    local_pubkey: str,
    peer_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Nodes + edges for ECharts force graph."""
    local_id = local_pubkey or "local"
    nodes = [{
        "id": local_id,
        "name": "本节点",
        "category": 0,
        "symbolSize": 56,
        "pubkey_short": _short_hash(local_pubkey, 16) if local_pubkey else "local",
    }]
    edges = []
    for index, peer in enumerate(peer_rows):
        peer_id = peer.get("pubkey") or f"peer-{index}"
        category = 1
        if peer.get("fork_panic"):
            category = 3
        elif peer.get("aligned"):
            category = 2
        elif peer.get("status") == "online":
            category = 1
        else:
            category = 4
        nodes.append({
            "id": peer_id,
            "name": peer.get("host") or peer_id[:12],
            "category": category,
            "symbolSize": 40,
            "pubkey_short": peer.get("pubkey_short"),
            "status": peer.get("status"),
        })
        edge_color = "#22c55e"
        if peer.get("fork_panic"):
            edge_color = "#ef4444"
        elif not peer.get("aligned"):
            edge_color = "#f59e0b"
        elif peer.get("status") != "online":
            edge_color = "#64748b"
        edges.append({
            "source": local_id,
            "target": peer_id,
            "value": peer.get("latency_ms") or 1,
            "lineStyle": {"color": edge_color, "width": 2 if peer.get("fork_panic") else 1.5},
            "label": {"show": True, "formatter": "对齐" if peer.get("aligned") else ("分叉" if peer.get("fork_panic") else "待同步")},
        })
    return {
        "nodes": nodes,
        "edges": edges,
        "categories": [
            {"name": "本节点"},
            {"name": "邻居"},
            {"name": "已对齐"},
            {"name": "分叉警告"},
            {"name": "离线"},
        ],
    }


def build_sync_log(gossip_results: Dict[str, Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    rows = []
    for key, item in gossip_results.items():
        neg = item.get("negotiation") or {}
        rows.append({
            "peer": key,
            "at": item.get("checked_at"),
            "aligned": item.get("aligned"),
            "error": item.get("error"),
            "message": item.get("message"),
            "local_hash": _short_hash(item.get("local_hash") or "", 10),
            "remote_hash": _short_hash(item.get("remote_hash") or "", 10),
            "merge": (item.get("merge") or {}).get("status"),
            "negotiation_status": neg.get("status"),
            "negotiation_error": neg.get("error"),
            "merged_count": item.get("merged_count") or neg.get("merged_count"),
            "trust_score": neg.get("trust_score"),
        })
    rows.sort(key=lambda row: float(row.get("at") or 0), reverse=True)
    return rows[:limit]


def build_resilience(peer_rows: List[Dict[str, Any]], audit: Dict[str, Any], gossip_health: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Network resilience score: full-replication nodes / total mesh nodes."""
    integrity_ok = (audit.get("integrity") or {}).get("ok", True)
    online_peers = [row for row in peer_rows if row.get("status") == "online"]
    aligned_peers = [row for row in online_peers if row.get("aligned")]
    total_nodes = 1 + len(peer_rows)
    full_sync_nodes = (1 if integrity_ok else 0) + len(aligned_peers)
    genesis = (gossip_health or {}).get("genesis") or {}
    genesis_full = int(genesis.get("full_sync_peers") or 0)
    if genesis_full > full_sync_nodes:
        full_sync_nodes = genesis_full
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
        "local_integrity_ok": integrity_ok,
        "label": label,
        "genesis_enabled": bool(genesis.get("enabled", True)),
        "last_bootstrap_at": genesis.get("last_bootstrap_at"),
    }


def build_dashboard_status(
    *,
    node_id: str,
    uptime_seconds: float,
    resources: Dict[str, Any],
    identity: Dict[str, Any],
    audit: Dict[str, Any],
    peers_registry: Dict[str, Dict[str, Any]],
    gossip_health: Dict[str, Any],
    engine: Dict[str, Any],
    rem_status: Optional[Dict[str, Any]] = None,
    consensus_status: Optional[Dict[str, Any]] = None,
    replay_status: Optional[Dict[str, Any]] = None,
    awakening_status: Optional[Dict[str, Any]] = None,
    reflection_status: Optional[Dict[str, Any]] = None,
    port: int = 7864,
) -> Dict[str, Any]:
    peer_rows = gossip_health.get("peers") or []
    aligned_count = sum(1 for row in peer_rows if row.get("aligned"))
    online_count = sum(1 for row in peer_rows if row.get("status") == "online")
    fork_count = sum(1 for row in peer_rows if row.get("fork_panic"))
    rem = rem_status or {}
    consensus = consensus_status or {}
    resilience = build_resilience(peer_rows, audit, gossip_health)
    return {
        "ok": True,
        "schema_version": "2.0-mission-control",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node": {
            "id": node_id,
            "pubkey": identity.get("pubkey"),
            "pubkey_short": _short_hash(identity.get("pubkey") or "", 16),
            "uptime_seconds": round(uptime_seconds, 1),
            "uptime_label": _format_uptime(uptime_seconds),
            "port": port,
            "host": f"http://127.0.0.1:{port}",
            "resources": resources,
            "memory_blocks": engine.get("memory_count", 0),
            "trace_count": engine.get("trace_count", 0),
            "iteration": engine.get("current_iteration", 0),
        },
        "chain": {
            "last_hash": audit.get("last_hash_full") or audit.get("last_hash"),
            "last_hash_short": audit.get("last_hash"),
            "entry_count": audit.get("entries", 0),
            "integrity_ok": (audit.get("integrity") or {}).get("ok", True),
        },
        "peers": peer_rows,
        "peer_summary": {
            "total": len(peer_rows),
            "online": online_count,
            "aligned": aligned_count,
            "fork_panic": fork_count,
        },
        "network": gossip_health,
        "topology": build_topology(identity.get("pubkey") or node_id, peer_rows),
        "sync_log": gossip_health.get("sync_log") or [],
        "rem": {
            "enabled": rem.get("enabled", False),
            "running": rem.get("running", False),
            "rem_due": rem.get("rem_due", False),
            "last_rem_at": rem.get("last_rem_at"),
            "last_rem_label": rem.get("last_rem_label"),
            "threshold": rem.get("threshold"),
            "idle_seconds": rem.get("idle_seconds"),
            "total_pruned": rem.get("total_pruned", 0),
            "total_facts": rem.get("total_facts", 0),
            "semantic_facts": rem.get("semantic_facts", 0),
            "last_report": rem.get("last_rem_report"),
        },
        "consensus": {
            "enabled": bool((consensus.get("negotiation") or {}).get("mode")),
            "mode": (consensus.get("negotiation") or {}).get("mode"),
            "min_trust": (consensus.get("negotiation") or {}).get("min_trust"),
            "quorum_ratio": (consensus.get("negotiation") or {}).get("quorum_ratio"),
            "reputation_peers": consensus.get("reputation_peers", 0),
            "recent": (consensus.get("negotiation") or {}).get("recent") or {},
            "reputation": (consensus.get("negotiation") or {}).get("reputation") or {},
        },
        "resilience": resilience,
        "replay": replay_status or {},
        "awakening": awakening_status or {},
        "reflection": reflection_status or {},
    }


def _format_uptime(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def gossip_health_from_sync(
    gossip_sync,
    peer_registry,
    *,
    stale_seconds: float = 120.0,
) -> Dict[str, Any]:
    """Aggregate GossipSync heartbeat + recent check results for dashboard."""
    peers = peer_registry.get_all_peers() if peer_registry else {}
    gossip_results = gossip_sync.recent_results() if gossip_sync else {}
    heartbeat_results = gossip_sync.heartbeat_results() if gossip_sync else {}
    peer_rows = enrich_peers(peers, gossip_results, heartbeat_results, stale_seconds=stale_seconds)
    return {
        "heartbeat_interval_s": getattr(gossip_sync, "heartbeat_interval_s", None),
        "last_heartbeat_at": getattr(gossip_sync, "last_heartbeat_at", None),
        "stale_peer_seconds": stale_seconds,
        "peers": peer_rows,
        "gossip_recent": gossip_results,
        "heartbeat_recent": heartbeat_results,
        "sync_log": build_sync_log(gossip_results),
    }

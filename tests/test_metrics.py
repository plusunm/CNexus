#!/usr/bin/env python3
"""Mission Control metrics unit tests."""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from api.metrics import (  # noqa: E402
    build_dashboard_status,
    build_topology,
    enrich_peers,
    gossip_health_from_sync,
)


class _FakeRegistry:
    def get_all_peers(self):
        return {
            "aa" * 32: {"host": "http://127.0.0.1:9001", "last_seen": time.time(), "status": "trusted"},
        }


class _FakeGossip:
    heartbeat_interval_s = 30
    last_heartbeat_at = time.time()

    def recent_results(self):
        return {
            "aa" * 32: {
                "aligned": True,
                "local_hash": "abc",
                "remote_hash": "abc",
                "checked_at": time.time(),
            }
        }

    def heartbeat_results(self):
        return {
            "aa" * 32: {"ok": True, "latency_ms": 12, "checked_at": time.time()},
        }


def main():
    peers = _FakeRegistry().get_all_peers()
    rows = enrich_peers(peers, _FakeGossip().recent_results(), _FakeGossip().heartbeat_results())
    assert len(rows) == 1
    assert rows[0]["status"] == "online"
    assert rows[0]["aligned"] is True

    topo = build_topology("local-pubkey", rows)
    assert len(topo["nodes"]) == 2
    assert len(topo["edges"]) == 1

    health = gossip_health_from_sync(_FakeGossip(), _FakeRegistry())
    assert health["peers"][0]["latency_ms"] == 12

    dash = build_dashboard_status(
        node_id="local",
        uptime_seconds=120,
        resources={"available": False},
        identity={"pubkey": "local-pubkey"},
        audit={"last_hash": "abc…", "entries": 3, "integrity": {"ok": True}},
        peers_registry=peers,
        gossip_health=health,
        engine={"memory_count": 1, "trace_count": 2, "current_iteration": 3},
    )
    assert dash["ok"] is True
    assert dash["peer_summary"]["online"] == 1
    print("METRICS TEST PASSED")


if __name__ == "__main__":
    main()

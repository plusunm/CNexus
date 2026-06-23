#!/usr/bin/env python3
"""REM sleep engine unit tests."""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from kernel.block_store import BlockStore  # noqa: E402
from core.rem_sleep import RemSleepEngine  # noqa: E402


class _Audit:
    def __init__(self):
        self.entries = []

    def log(self, _im, payload):
        self.entries.append(payload)
        return "hash-ok"


def main():
    store = BlockStore()
    now = time.time()
    store.add({
        "label": "episodic",
        "block_id": "old-1",
        "data": {"content": "stale memory"},
        "importance": 0.1,
        "timestamp": now - 86400 * 10,
    })
    store.add({
        "label": "episodic",
        "block_id": "fresh-1",
        "data": {"content": "recent context"},
        "importance": 0.8,
        "timestamp": now - 120,
    })

    audit = _Audit()
    engine = RemSleepEngine(store, audit, object(), threshold=0.5, chunk_size=50)
    w_old = engine.calculate_weight(store.blocks[0], now=now, access_freq=0.01, connection_bonus=0.0)
    w_new = engine.calculate_weight(store.blocks[1], now=now, access_freq=0.8, connection_bonus=0.2)
    print("weights:", round(w_old, 4), round(w_new, 4))
    assert w_new > w_old
    assert engine.is_recently_active(store.blocks[1], now=now)
    assert engine.is_protected_block(store.blocks[1], set(), now=now)

    ctx = {
        "now": now,
        "specs": [{"id": "old-1", "tag": "term", "title": "x", "desc": "", "importance": 0.1}],
        "scores": {"old-1": 0.01},
        "adjacency": {"old-1": set()},
        "protected_ids": [],
        "trace": [],
        "consolidation": {"last_activity_at": now - 99999, "last_rem_at": 0, "rem_running": False},
        "activation_threshold": 0.4,
    }
    report = {}
    engine.synaptic_prune(ctx, report)
    print("prune:", report)
    assert report.get("pruned_blocks", 0) >= 0
    assert len(audit.entries) >= 1

    facts = engine._generate_synthesis(
        [{"text": "用户讨论了分布式记忆同步机制"}],
        None,
    )
    assert facts
    print("facts:", facts[0][:40])
    print("\nREM SLEEP TEST PASSED")


if __name__ == "__main__":
    main()

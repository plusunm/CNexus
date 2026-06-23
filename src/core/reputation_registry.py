"""Peer reputation / trust scores for consensus negotiation."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional


class ReputationRegistry:
    DEFAULT_TRUST = 0.5
    MIN_TRUST = 0.05
    MAX_TRUST = 1.0

    def __init__(self, storage_path: str | Path = "data/reputation.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.peers: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.storage_path.exists():
            return {}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _persist(self):
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(self.peers, handle, ensure_ascii=False, indent=2)

    def get_trust(self, pubkey: str) -> float:
        pubkey = str(pubkey or "").strip()
        if not pubkey:
            return self.DEFAULT_TRUST
        row = self.peers.get(pubkey) or {}
        if row.get("blacklisted"):
            return 0.0
        return float(row.get("trust_score", self.DEFAULT_TRUST))

    def record_success(self, pubkey: str, *, delta: float = 0.05):
        self._bump(pubkey, delta, event="sync_success")

    def record_failure(self, pubkey: str, *, delta: float = 0.15, reason: str = ""):
        self._bump(pubkey, -abs(delta), event="sync_failure", reason=reason)

    def record_fraud(self, pubkey: str, *, reason: str = "invalid_evidence"):
        pubkey = str(pubkey or "").strip()
        if not pubkey:
            return
        with self._lock:
            row = dict(self.peers.get(pubkey) or {})
            row["trust_score"] = max(self.MIN_TRUST, float(row.get("trust_score", self.DEFAULT_TRUST)) - 0.35)
            row["blacklisted"] = row["trust_score"] < 0.15
            row["last_event"] = reason
            row["updated_at"] = time.time()
            self.peers[pubkey] = row
            self._persist()

    def _bump(self, pubkey: str, delta: float, *, event: str, reason: str = ""):
        pubkey = str(pubkey or "").strip()
        if not pubkey:
            return
        with self._lock:
            row = dict(self.peers.get(pubkey) or {})
            score = float(row.get("trust_score", self.DEFAULT_TRUST)) + float(delta)
            row["trust_score"] = max(self.MIN_TRUST, min(self.MAX_TRUST, score))
            row["blacklisted"] = False
            row["last_event"] = event
            if reason:
                row["last_reason"] = reason
            row["updated_at"] = time.time()
            self.peers[pubkey] = row
            self._persist()

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self.peers.items()}

    def trusted_peers(self, min_trust: float) -> Dict[str, float]:
        return {
            k: float(v.get("trust_score", self.DEFAULT_TRUST))
            for k, v in self.get_all().items()
            if not v.get("blacklisted") and float(v.get("trust_score", self.DEFAULT_TRUST)) >= min_trust
        }

    def export_state(self) -> Dict[str, Dict[str, Any]]:
        return self.get_all()

    def import_state(self, peers: Dict[str, Dict[str, Any]]):
        if not isinstance(peers, dict):
            return
        with self._lock:
            self.peers = {str(k): dict(v) for k, v in peers.items() if k}
            self._persist()

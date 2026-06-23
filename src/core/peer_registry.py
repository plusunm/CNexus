"""Trusted peer address book (local JSON)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional


class PeerRegistry:
    def __init__(self, storage_path: str | Path = "data/peers.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.peers: Dict[str, Dict[str, Any]] = self._load_peers()

    def _load_peers(self) -> Dict[str, Dict[str, Any]]:
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

    def save_peer(self, pubkey: str, host: str, *, status: str = "trusted") -> dict:
        pubkey = str(pubkey or "").strip()
        if not pubkey:
            raise ValueError("pubkey required")
        with self._lock:
            existing = dict(self.peers.get(pubkey) or {})
        record = {
            "host": str(host or "").strip(),
            "last_seen": time.time(),
            "status": status,
            "endpoints": list(existing.get("endpoints") or []),
            "nat_type": existing.get("nat_type"),
            "path_kind": existing.get("path_kind"),
        }
        if record["host"] and record["host"] not in record["endpoints"]:
            record["endpoints"].insert(0, record["host"])
        with self._lock:
            self.peers[pubkey] = record
            self._persist()
        return record

    def update_peer(self, pubkey: str, **fields) -> Optional[dict]:
        pubkey = str(pubkey or "").strip()
        if not pubkey:
            return None
        with self._lock:
            if pubkey not in self.peers:
                return None
            row = dict(self.peers[pubkey])
            row.update({k: v for k, v in fields.items() if v is not None})
            row["last_seen"] = time.time()
            self.peers[pubkey] = row
            self._persist()
            return dict(row)

    def touch_peer(self, pubkey: str):
        pubkey = str(pubkey or "").strip()
        if not pubkey or pubkey not in self.peers:
            return
        with self._lock:
            self.peers[pubkey]["last_seen"] = time.time()
            self._persist()

    def set_peer_status(self, pubkey: str, status: str):
        pubkey = str(pubkey or "").strip()
        if not pubkey or pubkey not in self.peers:
            return
        with self._lock:
            self.peers[pubkey]["status"] = status
            self._persist()

    def get_peer(self, pubkey: str) -> Optional[dict]:
        return dict(self.peers.get(str(pubkey or "").strip()) or {}) or None

    def get_all_peers(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self.peers.items()}

    def remove_peer(self, pubkey: str) -> bool:
        pubkey = str(pubkey or "").strip()
        with self._lock:
            if pubkey not in self.peers:
                return False
            del self.peers[pubkey]
            self._persist()
            return True

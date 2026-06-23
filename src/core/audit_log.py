"""Append-only hash-chained audit log with Ed25519 signatures."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class AuditLog:
    """Tamper-evident append-only log — each entry links to the previous hash."""

    def __init__(self, log_path: str | Path = "data/audit.log"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.last_hash = self._get_last_hash()

    @staticmethod
    def _canonical_json(data: dict) -> str:
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def _get_last_hash(self) -> str:
        if not self.log_path.exists():
            return "0"
        last_line = ""
        with open(self.log_path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if not last_line:
            return "0"
        return json.loads(last_line)["hash"]

    def _calculate_hash(self, prev_hash: str, data_payload: dict, signature: str) -> str:
        content = f"{prev_hash}{self._canonical_json(data_payload)}{signature}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def log(self, identity_manager, data: dict) -> Optional[str]:
        """Sign data and append a hash-linked audit entry. Returns entry hash."""
        if identity_manager is None:
            return None
        with self._lock:
            signed_package = identity_manager.sign_payload(data)
            current_hash = self._calculate_hash(
                self.last_hash,
                signed_package["payload"],
                signed_package["signature"],
            )
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": signed_package["payload"],
                "signature": signed_package["signature"],
                "pubkey": signed_package["pubkey"],
                "algorithm": signed_package.get("algorithm", "Ed25519"),
                "prev_hash": self.last_hash,
                "hash": current_hash,
            }
            with open(self.log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self.last_hash = current_hash
            return current_hash

    def verify_integrity(self, identity_manager=None) -> Tuple[bool, str]:
        """Verify hash chain and optional Ed25519 signatures."""
        if not self.log_path.exists():
            return True, "empty audit log"
        prev_hash = "0"
        with open(self.log_path, "r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    return False, f"invalid json at line {line_no}"

                if entry.get("prev_hash") != prev_hash:
                    return False, f"chain break at line {line_no} ({entry.get('timestamp')})"

                calculated = self._calculate_hash(
                    entry["prev_hash"],
                    entry["data"],
                    entry["signature"],
                )
                if entry.get("hash") != calculated:
                    return False, f"payload tampered at line {line_no} ({entry.get('timestamp')})"

                if identity_manager is not None:
                    envelope = {
                        "payload": entry["data"],
                        "signature": entry["signature"],
                        "pubkey": entry.get("pubkey"),
                    }
                    if not identity_manager.verify_payload(envelope, entry.get("pubkey")):
                        return False, f"signature invalid at line {line_no} ({entry.get('timestamp')})"

                prev_hash = entry["hash"]
        return True, "integrity verified"

    def entry_count(self) -> int:
        if not self.log_path.exists():
            return 0
        count = 0
        with open(self.log_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    count += 1
        return count

    def _read_all_entries(self) -> list:
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                entries.append(json.loads(stripped))
        return entries

    def iter_entries(self) -> list:
        """Public read-only iterator over all audit entries."""
        return self._read_all_entries()

    def get_entries_since(self, since_hash: str) -> Tuple[list, bool]:
        """
        Return audit entries after since_hash.
        Second value is anchor_found (False when since_hash is missing — fork / panic).
        """
        since_hash = str(since_hash or "0")
        all_entries = self._read_all_entries()
        if since_hash == "0":
            return all_entries, True
        if not all_entries:
            return [], False

        entries = []
        found = False
        for entry in all_entries:
            if found:
                entries.append(entry)
            if entry.get("hash") == since_hash:
                found = True
        return entries, found

    def get_entries_chunk(
        self, since_hash: str, *, limit: int = 200
    ) -> Tuple[list, bool, bool]:
        """Return a bounded slice of entries after since_hash."""
        entries, found = self.get_entries_since(since_hash)
        limit = max(1, int(limit or 200))
        has_more = len(entries) > limit
        return entries[:limit], found, has_more

    def _validate_entry(self, entry: dict, expected_prev_hash: str, identity_manager=None) -> Tuple[bool, str]:
        if entry.get("prev_hash") != expected_prev_hash:
            return False, (
                f"chain_break: expected prev {expected_prev_hash}, got {entry.get('prev_hash')}"
            )
        calculated = self._calculate_hash(
            entry["prev_hash"],
            entry["data"],
            entry["signature"],
        )
        if entry.get("hash") != calculated:
            return False, "hash_mismatch"
        if identity_manager is not None:
            envelope = {
                "payload": entry["data"],
                "signature": entry["signature"],
                "pubkey": entry.get("pubkey"),
            }
            if not identity_manager.verify_payload(envelope, entry.get("pubkey")):
                return False, "signature_invalid"
        return True, "ok"

    def merge_entries(self, entries: list, identity_manager=None) -> Tuple[bool, str, int]:
        """
        Validate then append peer entries atomically (validate-all-first).
        Returns (ok, message, merged_count).
        """
        if not entries:
            return True, "nothing_to_merge", 0

        temp_last = self.last_hash
        for index, entry in enumerate(entries):
            ok, msg = self._validate_entry(entry, temp_last, identity_manager)
            if not ok:
                return False, f"{msg} at index {index}", 0
            temp_last = entry["hash"]

        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as handle:
                for entry in entries:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self.last_hash = temp_last
        return True, "merged", len(entries)

    def get_proof_hashes(self) -> list:
        return [str(e.get("hash") or "") for e in self._read_all_entries() if e.get("hash")]

    def find_common_ancestor(self, peer_proof_hashes: list) -> str:
        """Deepest hash present in both local chain and peer proof."""
        peer_set = {str(h) for h in (peer_proof_hashes or []) if h}
        ancestor = "0"
        for entry in self._read_all_entries():
            entry_hash = str(entry.get("hash") or "")
            if entry_hash and entry_hash in peer_set:
                ancestor = entry_hash
        return ancestor

    def tail_entries_since(self, since_hash: str) -> list:
        entries, _found = self.get_entries_since(since_hash)
        return entries

    def reorg_from_ancestor(
        self,
        ancestor_hash: str,
        entries: list,
        identity_manager=None,
    ) -> Tuple[bool, str, int]:
        """Replace local chain tail after ancestor with validated peer entries."""
        ancestor_hash = str(ancestor_hash or "0")
        all_entries = self._read_all_entries()
        kept: list = []
        if ancestor_hash != "0":
            found = False
            for entry in all_entries:
                kept.append(entry)
                if entry.get("hash") == ancestor_hash:
                    found = True
                    break
            if not found:
                return False, "ancestor_not_found", 0

        temp_last = ancestor_hash if ancestor_hash != "0" else "0"
        for index, entry in enumerate(entries):
            ok, msg = self._validate_entry(entry, temp_last, identity_manager)
            if not ok:
                return False, f"{msg} at index {index}", 0
            temp_last = entry["hash"]

        with self._lock:
            with open(self.log_path, "w", encoding="utf-8") as handle:
                for entry in kept:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
                for entry in entries:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self.last_hash = temp_last
        return True, "reorg_complete", len(entries)

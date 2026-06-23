"""Consensus negotiation — fork resolution via evidence exchange and trust voting."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest


def _env_mode() -> str:
    raw = (os.environ.get("CNEXUS_CONSENSUS_MODE") or "optimistic").strip().lower()
    return raw if raw in ("optimistic", "conservative") else "optimistic"


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


class NegotiationManager:
    """
    Diplomatic fork resolution:
    Proposal → evidence validation → trust-weighted vote → commit (reorg/merge).
    """

    def __init__(
        self,
        audit_log,
        identity_manager=None,
        reputation_registry=None,
        *,
        build_signed_headers: Optional[Callable] = None,
        mode: Optional[str] = None,
        min_trust: Optional[float] = None,
        quorum_ratio: Optional[float] = None,
    ):
        self.audit_log = audit_log
        self.identity_manager = identity_manager
        self.reputation = reputation_registry
        self._build_signed_headers = build_signed_headers
        self.mode = mode or _env_mode()
        self.min_trust = min_trust if min_trust is not None else _env_float("CNEXUS_CONSENSUS_MIN_TRUST", 0.45)
        self.quorum_ratio = quorum_ratio if quorum_ratio is not None else _env_float("CNEXUS_CONSENSUS_QUORUM", 0.67)
        self._lock = threading.Lock()
        self._votes: Dict[str, Dict[str, Any]] = {}
        self.last_results: Dict[str, Dict[str, Any]] = {}

    def local_head(self) -> str:
        return self.audit_log.last_hash if self.audit_log else "0"

    def build_proposal(self) -> dict:
        proof = self.audit_log.get_proof_hashes() if self.audit_log else []
        return {
            "action": "NEGOTIATE_INIT",
            "local_head": self.local_head(),
            "proof_hashes": proof[-64:],
            "entry_count": self.audit_log.entry_count() if self.audit_log else 0,
            "pubkey": self.identity_manager.public_key_hex() if self.identity_manager else "",
            "mode": self.mode,
            "timestamp": time.time(),
        }

    def _validate_evidence_entries(self, entries: list) -> Tuple[bool, str]:
        if not self.audit_log or not entries:
            return False, "empty_evidence"
        temp_last = None
        for index, entry in enumerate(entries):
            if index == 0:
                temp_last = entry.get("prev_hash")
            ok, msg = self.audit_log._validate_entry(entry, temp_last, self.identity_manager)
            if not ok:
                return False, msg
            temp_last = entry.get("hash")
        return True, "ok"

    def _trust_allows_commit(self, peer_pubkey: str, vote_weight: float = 1.0) -> bool:
        if self.mode == "optimistic":
            return True
        trust = self.reputation.get_trust(peer_pubkey) if self.reputation else 0.5
        if trust < self.min_trust:
            return False
        if vote_weight >= self.quorum_ratio:
            return True
        trusted = self.reputation.trusted_peers(self.min_trust) if self.reputation else {}
        if not trusted:
            return trust >= self.min_trust
        weighted = sum(trusted.values())
        return (trust * vote_weight) / max(weighted, 0.01) >= self.quorum_ratio or trust >= self.quorum_ratio

    def handle_negotiate(self, data: dict, headers_peer: str = "") -> dict:
        """API handler: process INIT / VOTE / COMMIT from a peer."""
        action = str((data or {}).get("action") or "NEGOTIATE_INIT").upper()
        peer_pubkey = str(
            (data or {}).get("pubkey") or headers_peer or ""
        ).strip()

        if action == "NEGOTIATE_INIT":
            return self._handle_init(data, peer_pubkey)
        if action == "NEGOTIATE_VOTE":
            return self._handle_vote(data, peer_pubkey)
        if action == "NEGOTIATE_COMMIT":
            return self._handle_commit(data, peer_pubkey)
        return {"ok": False, "error": "unknown_action"}

    def _handle_init(self, data: dict, peer_pubkey: str) -> dict:
        peer_proof = data.get("proof_hashes") or []
        peer_head = str(data.get("local_head") or "")
        ancestor = self.audit_log.find_common_ancestor(peer_proof) if self.audit_log else "0"
        local_head = self.local_head()
        aligned = peer_head == local_head

        local_tail = self.audit_log.tail_entries_since(ancestor) if self.audit_log else []
        vote = "accept" if aligned else "pending"
        response = {
            "ok": True,
            "action": "NEGOTIATE_VOTE",
            "status": "aligned" if aligned else "diverged",
            "common_ancestor": ancestor,
            "local_head": local_head,
            "remote_head": peer_head,
            "local_tail_count": len(local_tail),
            "vote": vote,
            "pubkey": self.identity_manager.public_key_hex() if self.identity_manager else "",
        }
        if not aligned and local_tail:
            response["proof_hashes"] = self.audit_log.get_proof_hashes()[-32:]
        return response

    def _handle_vote(self, data: dict, peer_pubkey: str) -> dict:
        entries = data.get("entries") or []
        ancestor = str(data.get("common_ancestor") or "0")
        remote_head = str(data.get("remote_head") or data.get("local_head") or "")

        if entries:
            valid, msg = self._validate_evidence_entries(entries)
            if not valid:
                if self.reputation and peer_pubkey:
                    self.reputation.record_fraud(peer_pubkey, reason=msg)
                return {"ok": False, "action": "NEGOTIATE_VOTE", "vote": "reject", "error": msg}

        local_head = self.local_head()
        if remote_head and remote_head == local_head:
            if self.reputation and peer_pubkey:
                self.reputation.record_success(peer_pubkey)
            return {"ok": True, "action": "NEGOTIATE_VOTE", "vote": "accept", "status": "aligned"}

        trust = self.reputation.get_trust(peer_pubkey) if self.reputation else 0.5
        accept = self._trust_allows_commit(peer_pubkey, vote_weight=trust)
        vote = "accept" if accept else "reject"

        with self._lock:
            self._votes[peer_pubkey or remote_head] = {
                "vote": vote,
                "trust": trust,
                "ancestor": ancestor,
                "at": time.time(),
            }

        return {
            "ok": True,
            "action": "NEGOTIATE_VOTE",
            "vote": vote,
            "trust_score": trust,
            "common_ancestor": ancestor,
            "local_head": local_head,
            "can_commit": accept,
        }

    def _handle_commit(self, data: dict, peer_pubkey: str) -> dict:
        entries = data.get("entries") or []
        ancestor = str(data.get("common_ancestor") or "0")
        if not entries:
            return {"ok": False, "error": "missing_entries"}

        valid, msg = self._validate_evidence_entries(entries)
        if not valid:
            if self.reputation and peer_pubkey:
                self.reputation.record_fraud(peer_pubkey, reason=msg)
            return {"ok": False, "error": msg}

        if not self._trust_allows_commit(peer_pubkey):
            return {"ok": False, "error": "insufficient_trust", "mode": self.mode}

        local_tail = self.audit_log.tail_entries_since(ancestor) if self.audit_log else []
        if len(entries) >= len(local_tail):
            ok, msg, count = self.audit_log.reorg_from_ancestor(
                ancestor, entries, self.identity_manager
            )
        else:
            ok, msg, count = self.audit_log.merge_entries(entries, self.identity_manager)

        if ok:
            if self.reputation and peer_pubkey:
                self.reputation.record_success(peer_pubkey, delta=0.08)
            return {
                "ok": True,
                "action": "NEGOTIATE_COMMIT",
                "status": "committed",
                "merged_count": count,
                "local_head": self.local_head(),
                "message": msg,
            }
        if self.reputation and peer_pubkey:
            self.reputation.record_failure(peer_pubkey, reason=msg)
        return {"ok": False, "error": msg}

    def _http_post(self, host: str, path: str, payload: dict) -> dict:
        host = _normalize_host(host)
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.identity_manager and self._build_signed_headers:
            headers.update(self._build_signed_headers(self.identity_manager, payload))
        req = urlrequest.Request(f"{host}{path}", data=body, headers=headers, method="POST")
        with urlrequest.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def _http_get_audit_proof(self, host: str) -> dict:
        host = _normalize_host(host)
        payload = {"action": "proof"}
        query = urlparse.urlencode({"action": "proof"})
        headers = {"Content-Type": "application/json"}
        if self.identity_manager and self._build_signed_headers:
            headers.update(self._build_signed_headers(self.identity_manager, payload))
        req = urlrequest.Request(f"{host}/api/peer/audit-proof?{query}", headers=headers, method="GET")
        with urlrequest.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def _http_get_audit_delta(self, host: str, since_hash: str) -> dict:
        host = _normalize_host(host)
        since_hash = str(since_hash or "0")
        payload = {"since_hash": since_hash}
        query = urlparse.urlencode({"since_hash": since_hash})
        headers = {"Content-Type": "application/json"}
        if self.identity_manager and self._build_signed_headers:
            headers.update(self._build_signed_headers(self.identity_manager, payload))
        req = urlrequest.Request(f"{host}/api/peer/audit?{query}", headers=headers, method="GET")
        with urlrequest.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def resolve_divergence(
        self,
        peer_host: str,
        *,
        peer_pubkey: str = "",
        remote_head: str = "",
        remote_entries: int = 0,
    ) -> Dict[str, Any]:
        """Active negotiation when gossip detects fork or missing anchor."""
        result: Dict[str, Any] = {
            "ok": False,
            "phase": "negotiation",
            "peer_host": _normalize_host(peer_host),
            "peer_pubkey": peer_pubkey,
            "checked_at": time.time(),
        }
        if self.audit_log is None:
            result["error"] = "audit_unavailable"
            self._remember(peer_pubkey or peer_host, result)
            return result

        local_head = self.local_head()
        if remote_head and remote_head == local_head:
            result.update({"ok": True, "status": "aligned"})
            self._remember(peer_pubkey or peer_host, result)
            return result

        try:
            proposal = self.build_proposal()
            proposal["remote_head"] = remote_head
            vote_resp = self._http_post(peer_host, "/api/peer/negotiate", proposal)

            peer_proof = vote_resp.get("proof_hashes") or []
            if not peer_proof:
                proof_resp = self._http_get_audit_proof(peer_host)
                peer_proof = proof_resp.get("hashes") or []

            ancestor = self.audit_log.find_common_ancestor(peer_proof)
            if vote_resp.get("common_ancestor"):
                ancestor = str(vote_resp.get("common_ancestor"))

            delta = self._http_get_audit_delta(peer_host, ancestor)
            entries = delta.get("entries") or []
            result["common_ancestor"] = ancestor
            result["evidence_count"] = len(entries)

            if not entries and remote_head and remote_head != local_head:
                result["error"] = "negotiation_no_evidence"
                if self.reputation and peer_pubkey:
                    self.reputation.record_failure(peer_pubkey, reason="no_evidence")
                self._remember(peer_pubkey or peer_host, result)
                return result

            valid, msg = self._validate_evidence_entries(entries) if entries else (True, "ok")
            if not valid:
                result["error"] = "invalid_evidence"
                result["message"] = msg
                if self.reputation and peer_pubkey:
                    self.reputation.record_fraud(peer_pubkey, reason=msg)
                self._remember(peer_pubkey or peer_host, result)
                return result

            trust = self.reputation.get_trust(peer_pubkey) if self.reputation else 0.5
            local_tail = self.audit_log.tail_entries_since(ancestor)
            prefer_remote = len(entries) > len(local_tail) or (
                remote_entries > self.audit_log.entry_count()
            )

            if not prefer_remote and entries:
                prefer_remote = trust >= self.min_trust

            if not self._trust_allows_commit(peer_pubkey, vote_weight=trust):
                result["error"] = "negotiation_rejected"
                result["message"] = f"trust {trust:.2f} below policy ({self.mode})"
                self._remember(peer_pubkey or peer_host, result)
                return result

            if prefer_remote and entries:
                ok, msg, count = self.audit_log.reorg_from_ancestor(
                    ancestor, entries, self.identity_manager
                )
                if not ok:
                    ok, msg, count = self.audit_log.merge_entries(entries, self.identity_manager)
            elif entries:
                ok, msg, count = self.audit_log.merge_entries(entries, self.identity_manager)
            else:
                ok, msg, count = True, "nothing_to_apply", 0

            if ok:
                commit_payload = {
                    "action": "NEGOTIATE_COMMIT",
                    "common_ancestor": ancestor,
                    "entries": entries,
                    "remote_head": remote_head,
                    "pubkey": self.identity_manager.public_key_hex() if self.identity_manager else "",
                }
                try:
                    self._http_post(peer_host, "/api/peer/negotiate", commit_payload)
                except Exception:
                    pass
                if self.reputation and peer_pubkey:
                    self.reputation.record_success(peer_pubkey, delta=0.06)
                result.update({
                    "ok": True,
                    "status": "negotiated_commit",
                    "merged_count": count,
                    "local_head_after": self.local_head(),
                    "message": msg,
                    "trust_score": trust,
                })
            else:
                result["error"] = "commit_failed"
                result["message"] = msg
                if self.reputation and peer_pubkey:
                    self.reputation.record_failure(peer_pubkey, reason=msg)
        except urlerror.HTTPError as exc:
            result["error"] = f"http_{exc.code}"
        except Exception as exc:
            result["error"] = str(exc)

        self._remember(peer_pubkey or peer_host, result)
        return result

    def _remember(self, key: str, result: dict):
        with self._lock:
            self.last_results[key] = dict(result)

    def recent_results(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self.last_results.items()}

    def status(self) -> dict:
        return {
            "mode": self.mode,
            "min_trust": self.min_trust,
            "quorum_ratio": self.quorum_ratio,
            "recent": self.recent_results(),
            "reputation": self.reputation.get_all() if self.reputation else {},
        }

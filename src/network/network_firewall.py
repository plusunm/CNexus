"""Network-layer trust firewall — block malicious peers before gossip/consensus."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional


class NetworkFirewall:
    """
    Physical-layer gate: drop blacklisted / low-trust peers from routing and DHT.
    Complements Consensus Negotiation (logical layer).
    """

    def __init__(
        self,
        reputation_registry=None,
        *,
        min_trust_discovered: float = 0.25,
        min_trust_known: float = 0.15,
        audit_fn: Optional[Callable[[str, dict], Any]] = None,
    ):
        self.reputation = reputation_registry
        self.min_trust_discovered = min_trust_discovered
        self.min_trust_known = min_trust_known
        self.audit_fn = audit_fn
        self._local_bans: Dict[str, Dict[str, Any]] = {}
        self.last_actions: List[dict] = []

    def is_banned(self, peer_id: str) -> bool:
        peer_id = str(peer_id or "").strip()
        if not peer_id:
            return True
        if peer_id in self._local_bans:
            return True
        if self.reputation:
            row = (self.reputation.get_all() or {}).get(peer_id) or {}
            if row.get("blacklisted"):
                return True
        return False

    def trust_score(self, peer_id: str) -> float:
        if self.reputation is None:
            return 0.5
        return float(self.reputation.get_trust(peer_id))

    def allow_connection(self, peer_id: str, *, status: str = "trusted") -> tuple[bool, str]:
        peer_id = str(peer_id or "").strip()
        if not peer_id:
            return False, "missing_peer_id"
        if self.is_banned(peer_id):
            return False, "peer_banned"
        score = self.trust_score(peer_id)
        threshold = self.min_trust_discovered if status in ("discovered", "unknown") else self.min_trust_known
        if score < threshold:
            return False, f"trust_below_{threshold}"
        return True, "ok"

    def ban_peer(self, peer_id: str, *, reason: str = "firewall_ban", source: str = "local") -> dict:
        peer_id = str(peer_id or "").strip()
        if not peer_id:
            return {"ok": False, "error": "missing_peer_id"}
        self._local_bans[peer_id] = {
            "reason": reason,
            "source": source,
            "at": time.time(),
        }
        if self.reputation:
            self.reputation.record_fraud(peer_id, reason=reason)
        if self.audit_fn:
            try:
                self.audit_fn(
                    "network.firewall.ban",
                    {"peer_pubkey": peer_id[:64], "reason": reason, "source": source},
                )
            except Exception:
                pass
        action = {"ok": True, "peer_id": peer_id, "reason": reason, "at": time.time()}
        self.last_actions.append(action)
        self.last_actions = self.last_actions[-50:]
        return action

    def unban_peer(self, peer_id: str) -> dict:
        peer_id = str(peer_id or "").strip()
        self._local_bans.pop(peer_id, None)
        return {"ok": True, "peer_id": peer_id}

    def filter_peers(self, peers: Dict[str, dict]) -> Dict[str, dict]:
        allowed: Dict[str, dict] = {}
        for pubkey, meta in (peers or {}).items():
            status = str(meta.get("status") or "trusted")
            ok, _reason = self.allow_connection(pubkey, status=status)
            if ok:
                allowed[pubkey] = dict(meta)
        return allowed

    def status(self) -> dict:
        return {
            "min_trust_discovered": self.min_trust_discovered,
            "min_trust_known": self.min_trust_known,
            "local_bans": len(self._local_bans),
            "recent_actions": list(self.last_actions[-10:]),
        }

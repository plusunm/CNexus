"""
GTBS v1.1 Shadow Mode (P1 FREEZE)

Epistemic Instrumentation Layer Only — pure divergence sensor.

INVARIANTS (non-negotiable):
- No control influence
- No runtime / storage / CDG mutation
- No audit write-back
- No alerting or policy feedback
- mismatch is information only (Non-Coherence Rule)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core.governance.semantic_safety.envelope import stamp_observational_safe

GTBS_SHADOW_VERSION = "1.1.1"
GTBS_SHADOW_MODE = "SHADOW_ONLY"

# Governable projection keys → continuity store labels (observational mapping only).
GOVERNABLE_KEY_TO_STORE: dict[str, str] = {
    "memory": "storage",
    "narrative": "narrative",
    "beliefs": "belief",
    "working_self": "working_self",
    "self_model": "self_model",
    "interaction": "reality",
    "flags": "cognitive",
    "plasticity_modifier": "cognitive",
}

CONTINUITY_STORES = (
    "reality",
    "storage",
    "narrative",
    "belief",
    "self_model",
    "working_self",
    "cognitive",
)


class RuntimeGatekeeper:
    """
    Pure Shadow Epistemic Observer (Divergence Sensor).

    Measures divergence between intended change (proposal/context) and
    actual state transition (pre_state → post_state).

    Does NOT: govern, enforce, decide, validate, block, or feed back.
    """

    GTBS_VERSION = GTBS_SHADOW_VERSION
    GTBS_MODE = GTBS_SHADOW_MODE

    def __init__(self) -> None:
        self._shadow_mode = True

    @property
    def is_shadow_mode(self) -> bool:
        return self._shadow_mode

    def observe_runtime_event(
        self,
        pre_state: Optional[dict[str, Any]],
        post_state: Optional[dict[str, Any]],
        context: Optional[dict[str, Any]] = None,
        proposal: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Pure observation — NO SIDE EFFECTS.

        Returns an epistemic divergence snapshot (non-actionable).
        """
        pre = pre_state or {}
        post = post_state or {}

        pre_keys = set(pre.keys())
        post_keys = set(post.keys())
        added_keys = sorted(post_keys - pre_keys)
        removed_keys = sorted(pre_keys - post_keys)
        stable_keys = sorted(pre_keys & post_keys)

        state_diff = {
            "added_keys": added_keys,
            "removed_keys": removed_keys,
            "stable_keys": stable_keys,
            "divergence_score": len(added_keys) + len(removed_keys),
        }
        store_divergence = self._store_divergence(pre, post, state_diff)
        proposal_overlay = self._proposal_overlay(proposal)
        proposal_vs_reality = self._proposal_vs_reality(proposal, state_diff, store_divergence)

        return stamp_observational_safe(
            {
                "type": "gtbs_shadow_observation",
                "gtbs_version": self.GTBS_VERSION,
                "mode": self.GTBS_MODE,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "has_proposal": proposal is not None,
                "proposal": proposal,
                "context": dict(context or {}),
                "state_diff": state_diff,
                "store_divergence": store_divergence,
                "proposal_overlay": proposal_overlay,
                "proposal_vs_reality": proposal_vs_reality,
                "non_actionable": True,
            }
        )

    @staticmethod
    def _proposal_overlay(proposal: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Non-binding overlay: declared intent vs structural diff (informational only)."""
        if not proposal:
            return {"aligned": None, "declared_stores": [], "note": "no proposal"}

        declared = proposal.get("target_stores")
        if declared is None and "deltas" in proposal:
            declared = [
                d.get("target_store")
                for d in proposal.get("deltas", [])
                if isinstance(d, dict) and d.get("target_store")
            ]

        return {
            "aligned": None,
            "declared_stores": list(declared or []),
            "note": "overlay is non-binding; mismatch is not an error",
        }

    @staticmethod
    def _store_divergence(
        pre: dict[str, Any],
        post: dict[str, Any],
        state_diff: dict[str, Any],
    ) -> dict[str, Any]:
        """Per-store divergence scores (heuristic projection diff — not canonical Σ)."""
        scores: dict[str, float] = {s: 0.0 for s in CONTINUITY_STORES}
        changed_keys = set(state_diff.get("added_keys", []) + state_diff.get("removed_keys", []))

        for key in changed_keys:
            store = GOVERNABLE_KEY_TO_STORE.get(key, "cognitive")
            scores[store] = scores.get(store, 0.0) + 1.0

        for key in state_diff.get("stable_keys", []):
            store = GOVERNABLE_KEY_TO_STORE.get(key)
            if not store:
                continue
            if pre.get(key) != post.get(key):
                scores[store] = scores.get(store, 0.0) + 0.5

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {
            "by_store": {k: round(v, 4) for k, v in scores.items()},
            "top_store": ranked[0][0] if ranked and ranked[0][1] > 0 else None,
            "total": round(sum(scores.values()), 4),
        }

    @staticmethod
    def _proposal_vs_reality(
        proposal: Optional[dict[str, Any]],
        state_diff: dict[str, Any],
        store_divergence: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Proposal vs reality divergence (informational only — Axiom A5)."""
        if not proposal:
            return {
                "key_jaccard": None,
                "proposal_reality_divergence": None,
                "cross_store_consistency": None,
                "missed_proposals": [],
                "unexpected_changes": [],
                "note": "no proposal",
            }

        proposed_keys = proposal.get("proposed_keys")
        if proposed_keys is None and "deltas" in proposal:
            proposed_keys = [
                k
                for d in proposal.get("deltas", [])
                if isinstance(d, dict)
                for k in (d.get("payload") or {}).keys()
            ]
        proposed = set(proposed_keys or [])
        actual = set(state_diff.get("added_keys", []) + state_diff.get("removed_keys", []))

        if not proposed and not actual:
            return {
                "key_jaccard": 1.0,
                "proposal_reality_divergence": 0.0,
                "cross_store_consistency": 1.0,
                "missed_proposals": [],
                "unexpected_changes": [],
                "note": "empty proposal and empty diff",
            }

        union = proposed | actual
        intersection = proposed & actual
        key_jaccard = len(intersection) / len(union) if union else 1.0

        declared_stores = set(proposal.get("target_stores") or [])
        changed_stores = {
            s
            for s, v in (store_divergence or {}).get("by_store", {}).items()
            if v > 0
        }
        if declared_stores and changed_stores:
            store_union = declared_stores | changed_stores
            store_inter = declared_stores & changed_stores
            cross_store_consistency = len(store_inter) / len(store_union)
        elif not declared_stores:
            cross_store_consistency = 1.0 if not changed_stores else 0.5
        else:
            cross_store_consistency = 0.0 if changed_stores else 1.0

        return {
            "key_jaccard": round(key_jaccard, 4),
            "proposal_reality_divergence": round(1.0 - key_jaccard, 4),
            "cross_store_consistency": round(cross_store_consistency, 4),
            "missed_proposals": sorted(proposed - actual),
            "unexpected_changes": sorted(actual - proposed),
            "declared_stores": list(proposal.get("target_stores") or []),
            "changed_stores": sorted(changed_stores),
        }

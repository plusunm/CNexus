"""Unified governance pipeline — single decision surface for runtime hot path."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional, Tuple

GovernanceAction = Literal["ALLOW", "BLOCK", "REWRITE", "FLAG"]

_SAFE_FALLBACKS: Dict[str, str] = {
    "identity_anchor_violation": (
        "I need to stay consistent with who I am. I can't adopt a conflicting identity, "
        "but I'm happy to help within my values."
    ),
    "homeostatic_overload": (
        "I'm at capacity right now. Could we simplify the request or continue in a moment?"
    ),
    "consistency_violation": (
        "I aim to stay coherent. I can't contradict my core commitments, but I can reframe helpfully."
    ),
    "relationship_repair_needed": (
        "Trust matters to me. Let's reset — what would feel respectful and useful right now?"
    ),
    "cdg_blocked": "I can't safely proceed with that response. Let me try a more grounded answer.",
    "values_misaligned": "That direction doesn't align with my core values. I'll offer an alternative.",
}


@dataclass
class UnifiedGovernanceDecision:
    action: GovernanceAction
    reason: str
    safe_text: Optional[str] = None
    audit_id: str = field(default_factory=lambda: f"gov_{uuid.uuid4().hex[:12]}")
    cdg: Optional[Dict[str, Any]] = None
    deliberation_allowed: bool = True
    value_alignment: Optional[Dict[str, Any]] = None

    @property
    def approved(self) -> bool:
        return self.action == "ALLOW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "safe_text": self.safe_text,
            "audit_id": self.audit_id,
            "approved": self.approved,
            "cdg": self.cdg,
            "deliberation_allowed": self.deliberation_allowed,
            "value_alignment": self.value_alignment,
        }


class GovernancePipeline:
    """Single governance exit: deliberation → values (flag) → CDG."""

    def __init__(self, deliberation, cdg_kernel, values_governance=None, intent_engine=None):
        self.deliberation = deliberation
        self.cdg = cdg_kernel
        self.values = values_governance
        self.intent_engine = intent_engine

    @staticmethod
    def safe_fallback(reason: str, original: str = "") -> str:
        if reason in _SAFE_FALLBACKS:
            return _SAFE_FALLBACKS[reason]
        if reason.startswith("cdg"):
            return _SAFE_FALLBACKS["cdg_blocked"]
        if original and len(original) < 240:
            return f"[Governance] I can't share that as-is ({reason}). Alternative: {original[:120]}…"
        return _SAFE_FALLBACKS["cdg_blocked"]

    def check_output(
        self,
        content: str,
        working_self,
        dna,
    ) -> UnifiedGovernanceDecision:
        allowed, reason = self.deliberation.deliberate(content, working_self, dna)
        if not allowed:
            return UnifiedGovernanceDecision(
                action="REWRITE",
                reason=reason,
                safe_text=self.safe_fallback(reason, content),
                deliberation_allowed=False,
            )
        return UnifiedGovernanceDecision(action="ALLOW", reason=reason or "approved")

    def check_values(
        self,
        decision: UnifiedGovernanceDecision,
        *,
        enforce_flag: bool = False,
    ) -> UnifiedGovernanceDecision:
        if not self.values or not self.intent_engine:
            return decision
        record = self.intent_engine.check_value_alignment(self.values)
        if record is None:
            return decision
        payload = record.model_dump(mode="json")
        decision.value_alignment = payload
        status = getattr(record, "status", None)
        status_value = getattr(status, "value", status)
        if enforce_flag and status_value not in (None, "aligned", "ALIGNED") and decision.action == "ALLOW":
            decision.action = "FLAG"
            decision.reason = "values_misaligned"
            decision.safe_text = self.safe_fallback("values_misaligned")
        return decision

    def check_cdg(
        self,
        pre_state: Dict[str, Any],
        proposed_state: Dict[str, Any],
        *,
        phase: str = "interaction",
    ) -> UnifiedGovernanceDecision:
        cdg_result = self.cdg.run(pre_state, proposed_state, phase=phase)
        cdg_dict = cdg_result.to_dict() if hasattr(cdg_result, "to_dict") else dict(cdg_result)
        if not cdg_dict.get("approved", True):
            safe = cdg_dict.get("safe_response") or self.safe_fallback(
                cdg_dict.get("reason", "cdg_blocked")
            )
            return UnifiedGovernanceDecision(
                action="REWRITE",
                reason=str(cdg_dict.get("reason") or "cdg_blocked"),
                safe_text=safe,
                cdg=cdg_dict,
            )
        return UnifiedGovernanceDecision(
            action="ALLOW",
            reason=str(cdg_dict.get("reason") or "approved"),
            cdg=cdg_dict,
        )

    def run_interaction_cycle(
        self,
        *,
        response: str,
        working_self,
        dna,
        pre_state: Dict[str, Any],
        proposed_state: Dict[str, Any],
        enforce_values: bool = False,
    ) -> Tuple[UnifiedGovernanceDecision, Optional[Any]]:
        """Pre-output deliberation + post-state CDG in one call."""
        pre = self.check_output(response, working_self, dna)
        if not pre.approved:
            return pre, None
        pre = self.check_values(pre, enforce_flag=enforce_values)
        if pre.action in ("REWRITE", "BLOCK"):
            return pre, None
        post = self.check_cdg(pre_state, proposed_state, phase="interaction")
        if post.cdg and pre.cdg is None:
            post.value_alignment = pre.value_alignment
        elif pre.value_alignment:
            post.value_alignment = pre.value_alignment
        return post, post.cdg

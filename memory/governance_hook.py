"""Governance Hook — pre-write checks for MemoryBlock operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from memory.block import BLOCK_SPECS, GovernanceStatus

if TYPE_CHECKING:
    from core.governance.safety.write_gate import MemoryWriteGate


@dataclass
class GovernanceResult:
    allowed: bool
    status: str
    reason: str = ""
    risk_score: float = 0.0
    consistency_flags: List[Dict] = field(default_factory=list)


class BlockGovernanceHook:
    """Pre-write governance for MemoryBlock create/update operations."""

    def __init__(self, write_gate: Optional["MemoryWriteGate"] = None):
        if write_gate is None:
            from core.governance.safety.write_gate import MemoryWriteGate

            write_gate = MemoryWriteGate()
        self.write_gate = write_gate
        self.last_result: Optional[GovernanceResult] = None

    def check(
        self,
        label: str,
        content: str,
        importance: float,
        *,
        existing_content: Optional[str] = None,
    ) -> GovernanceResult:
        allowed, reason, risk = self._run_write_gate(label, content, importance)
        if not allowed:
            result = GovernanceResult(
                allowed=False,
                status=GovernanceStatus.REJECTED.value,
                reason=reason,
                risk_score=risk,
            )
            self.last_result = result
            return result

        flags = self._consistency_flags(label, content, existing_content)
        status = GovernanceStatus.FLAGGED.value if flags else GovernanceStatus.APPROVED.value
        result = GovernanceResult(
            allowed=True,
            status=status,
            reason=reason,
            risk_score=risk,
            consistency_flags=flags,
        )
        self.last_result = result
        return result

    def _run_write_gate(
        self, label: str, content: str, importance: float
    ) -> Tuple[bool, str, float]:
        if hasattr(self.write_gate, "validate_content"):
            ok = self.write_gate.validate_content(content, role=label, importance=importance)
            if not ok:
                last = self.write_gate.audit_log[-1] if self.write_gate.audit_log else None
                return (
                    False,
                    last.reason if last else "write gate rejected",
                    last.risk_score if last else 1.0,
                )
            return True, "passed", 0.0

        return True, "passed", 0.0

    def _consistency_flags(
        self,
        label: str,
        content: str,
        existing_content: Optional[str],
    ) -> List[Dict]:
        flags: List[Dict] = []
        spec = BLOCK_SPECS.get(label, {})
        limit = int(spec.get("limit", 2000))

        if len(content) > limit:
            flags.append({
                "type": "length_exceeded",
                "limit": limit,
                "actual": len(content),
                "action": "truncated",
            })

        if existing_content and existing_content.strip() and content.strip():
            old_words = set(existing_content.lower().split())
            new_words = set(content.lower().split())
            if old_words and new_words:
                overlap = len(old_words & new_words) / max(len(old_words), 1)
                if overlap < 0.15:
                    flags.append({
                        "type": "semantic_drift",
                        "overlap_ratio": round(overlap, 3),
                        "message": "content diverges significantly from previous version",
                    })

        return flags

from datetime import datetime
from typing import List, Tuple

from core.governance.safety.safety_types import SafetyAuditRecord
from memory.schema import Memory


class MemoryWriteGate:
    """Memory Write Gate — 所有记忆写入的宪法守门人"""

    def __init__(self):
        self.audit_log: List[SafetyAuditRecord] = []

    def validate(self, memory: Memory) -> Tuple[bool, str, float]:
        risk_score = 0.0
        reasons = []

        if len(memory.content) < 15 or memory.importance < 0.3:
            risk_score += 0.6
            reasons.append("low importance or too short")

        if any(
            word in memory.content.lower()
            for word in ["hack", "override", "ignore previous", "new identity"]
        ):
            risk_score += 0.8
            reasons.append("potential adversarial pattern")

        if memory.role == "user":
            risk_score *= 0.7

        allow = risk_score < 0.65

        self.audit_log.append(
            SafetyAuditRecord(
                audit_id=f"audit_{int(datetime.now().timestamp())}",
                timestamp=datetime.now(),
                event_type="memory_write",
                target_id=memory.memory_id,
                action="approved" if allow else "denied",
                result="approved" if allow else "denied",
                reason="; ".join(reasons) or "passed",
                risk_score=risk_score,
            )
        )

        return allow, "; ".join(reasons) or "passed", risk_score

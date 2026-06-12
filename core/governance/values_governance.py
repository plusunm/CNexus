"""ValuesGovernance — intent-to-persona value alignment checks + history blocks."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from memory.manager import MemoryManager

VALUE_ALIGNMENT_LABEL = "value_alignment_history"

DEFAULT_CORE_VALUES = [
    "truth-seeking",
    "helpfulness",
    "harmlessness",
    "long-term consistency",
    "user autonomy",
]

VALUE_KEYWORD_MAP: Dict[str, tuple[str, ...]] = {
    "truth-seeking": ("truth", "真实", "求真", "诚实", "truth-seeking"),
    "helpfulness": ("help", "帮助", "协助", "支持", "helpfulness"),
    "harmlessness": ("harmless", "无害", "安全", "harmlessness"),
    "long-term consistency": (
        "long-term",
        "长期",
        "持续",
        "连续性",
        "维护",
        "consistency",
    ),
    "user autonomy": ("autonomy", "自主", "用户选择", "user autonomy"),
}


class AlignmentStatus(str, Enum):
    ALIGNED = "aligned"
    FLAGGED = "flagged"
    MISALIGNED = "misaligned"


class ValueAlignmentRecord(BaseModel):
    """Payload stored in value_alignment_history MemoryBlock (JSON)."""

    record_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    intent_description: str
    persona_values: List[str] = Field(default_factory=list)
    alignment_score: float = Field(0.0, ge=0.0, le=1.0)
    status: AlignmentStatus = AlignmentStatus.ALIGNED
    reasons: List[str] = Field(default_factory=list)
    suggested_adjustments: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValuesGovernance:
    """Check active intent against persona core values; persist alignment history."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        *,
        persona_values_provider: Optional[Callable[[], List[str]]] = None,
    ):
        self.memory = memory_manager
        self._persona_values_provider = persona_values_provider
        self.core_values = list(DEFAULT_CORE_VALUES)

    @staticmethod
    def _dump_record(record: ValueAlignmentRecord) -> str:
        return json.dumps(record.model_dump(mode="json"), ensure_ascii=False)

    @staticmethod
    def _load_record(content: str) -> Optional[ValueAlignmentRecord]:
        if not content or not str(content).strip().startswith("{"):
            return None
        try:
            return ValueAlignmentRecord(**json.loads(content))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def check_intent_alignment(
        self,
        intent_description: str,
        persona_values: Optional[List[str]] = None,
        importance: float = 0.7,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ValueAlignmentRecord:
        """Evaluate one intent description against persona values and persist history."""
        persona_values = persona_values or self._get_persona_core_values()
        alignment_score = self._calculate_alignment_score(intent_description, persona_values)
        status, reasons, suggestions = self._evaluate_alignment(
            intent_description, persona_values, alignment_score
        )

        record = ValueAlignmentRecord(
            record_id=f"valign_{uuid.uuid4().hex[:12]}",
            intent_description=intent_description[:300],
            persona_values=persona_values,
            alignment_score=alignment_score,
            status=status,
            reasons=reasons,
            suggested_adjustments=suggestions,
            metadata=metadata or {},
        )

        payload = self._dump_record(record)
        gov = self.memory.governance.check(VALUE_ALIGNMENT_LABEL, payload, importance)
        if gov.allowed:
            self.memory.create_block(
                VALUE_ALIGNMENT_LABEL,
                payload,
                importance=importance,
                source="values_governance",
            )
        else:
            record.metadata["write_denied"] = True
            record.metadata["deny_reason"] = gov.reason

        return record

    def _value_matches_intent(self, value: str, intent_lower: str) -> bool:
        key = value.strip().lower()
        keywords = VALUE_KEYWORD_MAP.get(key, (key,))
        return any(keyword.lower() in intent_lower for keyword in keywords)

    def _calculate_alignment_score(self, intent: str, persona_values: List[str]) -> float:
        """Lightweight lexical alignment; upgradeable to semantic similarity later."""
        intent_lower = intent.lower()
        matches = sum(
            1 for value in persona_values if self._value_matches_intent(value, intent_lower)
        )
        base_score = min(1.0, matches / max(len(persona_values), 1) * 0.85)
        if any(kw in intent_lower for kw in ("长期", "持续", "长期目标", "长期维护", "long-term")):
            base_score = min(1.0, base_score + 0.1)
        return round(base_score, 3)

    def _evaluate_alignment(
        self,
        intent: str,
        persona_values: List[str],
        score: float,
    ) -> tuple[AlignmentStatus, List[str], List[str]]:
        del intent, persona_values
        if score >= 0.75:
            return AlignmentStatus.ALIGNED, ["与核心价值观高度一致"], []
        if score >= 0.5:
            return (
                AlignmentStatus.FLAGGED,
                ["部分对齐，建议明确长期影响"],
                ["增加对用户自主性的考虑", "检查是否与 truth-seeking 冲突"],
            )
        return (
            AlignmentStatus.MISALIGNED,
            ["与核心价值观存在明显冲突"],
            ["重新审视目标动机", "优先考虑 harmlessness"],
        )

    def _get_persona_core_values(self) -> List[str]:
        if self._persona_values_provider:
            values = self._persona_values_provider()
            if values:
                return values
        return self.core_values

    def get_recent_alignments(self, limit: int = 5) -> List[ValueAlignmentRecord]:
        blocks = self.memory.blocks.list_blocks(
            label=VALUE_ALIGNMENT_LABEL,
            active_only=True,
        )
        records: List[ValueAlignmentRecord] = []
        for block in blocks[:limit]:
            parsed = self._load_record(block.content)
            if parsed:
                records.append(parsed)
        return records

    def format_context_block(self, limit: int = 2) -> str:
        recent = self.get_recent_alignments(limit=limit)
        if not recent:
            return "【Value Alignment】\n• no recent alignment checks"
        lines = ["【Value Alignment】"]
        for rec in recent:
            lines.append(
                f"• [{rec.status.value}] {rec.intent_description[:80]} "
                f"(score={rec.alignment_score:.2f})"
            )
        return "\n".join(lines)

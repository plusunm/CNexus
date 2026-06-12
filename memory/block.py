"""Structured MemoryBlock — L1 typed cognitive state units."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class BlockCategory(str, Enum):
    CORE = "core"
    PROFILE = "profile"
    ARCHIVAL = "archival"


class GovernanceStatus(str, Enum):
    APPROVED = "approved"
    FLAGGED = "flagged"
    PENDING = "pending"
    REJECTED = "rejected"


# Singleton labels: at most one active block per label.
CORE_LABELS = frozenset({"persona", "emotion", "intent", "working_memory"})
PROFILE_LABELS = frozenset({"user_profile"})
ARCHIVAL_LABELS = frozenset({"archival_facts", "reflective_trace", "value_alignment_history"})
SINGLETON_LABELS = CORE_LABELS | PROFILE_LABELS

BLOCK_SPECS: Dict[str, Dict] = {
    "persona": {
        "description": "人格 + 叙事自我",
        "limit": 2000,
        "importance": 0.95,
        "always_in_context": True,
        "category": BlockCategory.CORE,
        "governance_priority": "high",
        "decay_rate": 0.0,
        "auto_protected": True,
    },
    "emotion": {
        "description": "当前情感状态",
        "limit": 800,
        "importance": 0.70,
        "always_in_context": True,
        "category": BlockCategory.CORE,
        "governance_priority": "medium",
        "decay_rate": 0.01,
        "auto_protected": False,
    },
    "intent": {
        "description": "当前目标与动机",
        "limit": 1200,
        "importance": 0.90,
        "always_in_context": True,
        "category": BlockCategory.CORE,
        "governance_priority": "high",
        "decay_rate": 0.005,
        "auto_protected": True,
    },
    "working_memory": {
        "description": "当前任务关键信息",
        "limit": 1500,
        "importance": 0.75,
        "always_in_context": True,
        "category": BlockCategory.CORE,
        "governance_priority": "medium",
        "decay_rate": 0.02,
        "auto_protected": False,
    },
    "user_profile": {
        "description": "用户长期偏好",
        "limit": 3000,
        "importance": 0.85,
        "always_in_context": False,
        "category": BlockCategory.PROFILE,
        "governance_priority": "high",
        "decay_rate": 0.008,
        "auto_protected": False,
    },
    "archival_facts": {
        "description": "长期事实与经验",
        "limit": 8000,
        "importance": 0.55,
        "always_in_context": False,
        "category": BlockCategory.ARCHIVAL,
        "governance_priority": "medium",
        "decay_rate": 0.03,
        "auto_protected": False,
    },
    "reflective_trace": {
        "description": "Reflexion 风格交互反思记录（episodic reflective buffer）",
        "limit": 4000,
        "importance": 0.72,
        "always_in_context": False,
        "category": BlockCategory.ARCHIVAL,
        "governance_priority": "medium",
        "decay_rate": 0.02,
        "auto_protected": False,
    },
    "value_alignment_history": {
        "description": "Intent 与核心价值观对齐检查历史",
        "limit": 4000,
        "importance": 0.68,
        "always_in_context": False,
        "category": BlockCategory.ARCHIVAL,
        "governance_priority": "high",
        "decay_rate": 0.015,
        "auto_protected": False,
    },
}

AUTO_PROTECTED_LABELS = frozenset(
    label for label, spec in BLOCK_SPECS.items() if spec.get("auto_protected")
)

LABEL_PRIORITY: Dict[str, float] = {
    "persona": 1.0,
    "intent": 0.95,
    "user_profile": 0.90,
    "emotion": 0.85,
    "working_memory": 0.80,
    "archival_facts": 0.50,
    "reflective_trace": 0.45,
    "value_alignment_history": 0.42,
}


class MemoryBlock(BaseModel):
    block_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    description: str = ""
    content: str
    limit: int = 2000
    importance: float = Field(0.5, ge=0.0, le=1.0)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_accessed_at: datetime = Field(default_factory=datetime.now)
    version: int = 1
    active: bool = True

    decay_factor: float = Field(1.0, ge=0.0, le=1.0)
    decay_rate: float = Field(0.01, ge=0.0, le=1.0)
    protected: bool = False

    consistency_flags: List[Dict] = Field(default_factory=list)
    governance_status: str = GovernanceStatus.APPROVED.value

    tags: List[str] = Field(default_factory=list)
    source: str = "interaction"
    category: str = BlockCategory.CORE.value
    embedding: Optional[List[float]] = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_label(
        cls,
        label: str,
        content: str,
        *,
        description: str = "",
        importance: Optional[float] = None,
        source: str = "interaction",
        tags: Optional[List[str]] = None,
        governance_status: str = GovernanceStatus.APPROVED.value,
        consistency_flags: Optional[List[Dict]] = None,
    ) -> "MemoryBlock":
        spec = BLOCK_SPECS.get(label, {})
        raw_cat = spec.get("category", BlockCategory.ARCHIVAL)
        category = raw_cat.value if isinstance(raw_cat, BlockCategory) else str(raw_cat)
        auto_protected = bool(spec.get("auto_protected", False))
        return cls(
            label=label,
            description=description or spec.get("description", ""),
            content=content,
            limit=int(spec.get("limit", 2000)),
            importance=float(importance if importance is not None else spec.get("importance", 0.5)),
            category=category,
            source=source,
            tags=tags or [],
            governance_status=governance_status,
            consistency_flags=consistency_flags or [],
            decay_rate=float(spec.get("decay_rate", 0.01)),
            protected=auto_protected,
        )

    def model_dump_for_storage(self) -> dict:
        data = self.model_dump()
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["last_accessed_at"] = self.last_accessed_at.isoformat()
        return data

    @classmethod
    def from_storage(cls, data: dict) -> "MemoryBlock":
        payload = dict(data)
        for key in ("created_at", "updated_at", "last_accessed_at"):
            if isinstance(payload.get(key), str):
                payload[key] = datetime.fromisoformat(payload[key])
        if "last_accessed_at" not in payload and "updated_at" in payload:
            payload["last_accessed_at"] = payload["updated_at"]
        if "decay_factor" not in payload:
            payload["decay_factor"] = 1.0
        if "decay_rate" not in payload:
            spec = BLOCK_SPECS.get(payload.get("label", ""), {})
            payload["decay_rate"] = float(spec.get("decay_rate", 0.01))
        if "protected" not in payload:
            spec = BLOCK_SPECS.get(payload.get("label", ""), {})
            payload["protected"] = bool(spec.get("auto_protected", False))
        return cls(**payload)

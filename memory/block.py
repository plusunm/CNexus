"""CNexus L1 Memory Infrastructure — Memory Block definitions.

EpisodicMemoryBlock explicit typing + attention_state hybrid strategy (Option 2).
Keeps Pydantic MemoryBlock API for storage, governance, and lifecycle compatibility.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BlockCategory(str, Enum):
    CORE = "core"
    PROFILE = "profile"
    EPISODIC = "episodic"
    ARCHIVAL = "archival"


class GovernanceStatus(str, Enum):
    APPROVED = "approved"
    FLAGGED = "flagged"
    PENDING = "pending"
    REJECTED = "rejected"


class BlockType(str, Enum):
    """Mid-term typed block registry — values are canonical storage labels."""

    PERSONA = "persona"
    EMOTION = "emotion"
    INTENT = "intent"
    WORKING_MEMORY = "working_memory"
    USER_PROFILE = "user_profile"
    BELIEF_STORE = "belief_store"
    NARRATIVE = "narrative"
    ATTENTION_STATE = "attention_state"
    EPISODIC_EVENT = "episodic_event"
    DIALOGUE_TRACE = "episodic_dialogue"
    DECISION_TRACE = "episodic_decision"
    ARCHIVAL_FACTS = "archival_facts"
    REFLECTIVE_TRACE = "reflective_trace"
    VALUE_ALIGNMENT_HISTORY = "value_alignment_history"

    @classmethod
    def normalize_label(cls, label: str) -> str:
        aliases = {
            "dialogue_trace": cls.DIALOGUE_TRACE.value,
            "decision_trace": cls.DECISION_TRACE.value,
            "event_graph": cls.EPISODIC_EVENT.value,
            "belief": cls.BELIEF_STORE.value,
            BlockType.ATTENTION_STATE.name.lower(): cls.ATTENTION_STATE.value,
        }
        if label in {member.value for member in cls}:
            return label
        return aliases.get(label, label)


BLOCK_LABEL_ALIASES: Dict[str, str] = {
    "dialogue_trace": "episodic_dialogue",
    "decision_trace": "episodic_decision",
    "event_graph": "episodic_event",
}


def normalize_block_label(label: str) -> str:
    return BlockType.normalize_label(BLOCK_LABEL_ALIASES.get(label, label))


CORE_LABELS = frozenset({"persona", "emotion", "intent", "working_memory"})
PROFILE_LABELS = frozenset({"user_profile"})
EPISODIC_LABELS = frozenset({"episodic_event", "episodic_dialogue", "episodic_decision"})
ATTENTION_LABELS = frozenset({"attention_state"})
ARCHIVAL_LABELS = frozenset(
    {"archival_facts", "reflective_trace", "value_alignment_history", "belief_store"}
)
SINGLETON_LABELS = (
    CORE_LABELS | PROFILE_LABELS | ATTENTION_LABELS | EPISODIC_LABELS | frozenset({"belief_store"})
)

EPISODIC_TYPE_TO_LABEL = {
    "event": "episodic_event",
    "dialogue": "episodic_dialogue",
    "decision": "episodic_decision",
}

EPISODIC_ENTRY_SCHEMAS: Dict[str, List[str]] = {
    "event": ["event_id", "timestamp", "type", "payload", "linked_decisions"],
    "dialogue": ["turn_id", "speaker", "content_summary", "emotion_delta", "linked_events"],
    "decision": ["decision_id", "context_snapshot", "chosen_action", "outcome", "reflection_id"],
}

BLOCK_SPECS: Dict[str, Dict[str, Any]] = {
    "persona": {
        "description": "人格 + 叙事自我",
        "limit": 2000,
        "importance": 0.95,
        "always_in_context": True,
        "category": BlockCategory.CORE,
        "governance_priority": "high",
        "decay_rate": 0.0,
        "auto_protected": True,
        "default_priority": 1,
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
        "default_priority": 2,
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
        "default_priority": 3,
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
        "default_priority": 1,
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
        "default_priority": 2,
    },
    "episodic_event": {
        "description": "显式事件记忆块 (Lance+Kuzu backed)",
        "limit": 5000,
        "importance": 0.55,
        "always_in_context": False,
        "category": BlockCategory.EPISODIC,
        "governance_priority": "medium",
        "decay_rate": 0.03,
        "auto_protected": False,
        "default_priority": 6,
        "episodic_type": "event",
    },
    "episodic_dialogue": {
        "description": "显式对话轨迹块",
        "limit": 8000,
        "importance": 0.52,
        "always_in_context": False,
        "category": BlockCategory.EPISODIC,
        "governance_priority": "medium",
        "decay_rate": 0.025,
        "auto_protected": False,
        "default_priority": 6,
        "episodic_type": "dialogue",
    },
    "episodic_decision": {
        "description": "显式决策轨迹块",
        "limit": 4000,
        "importance": 0.54,
        "always_in_context": False,
        "category": BlockCategory.EPISODIC,
        "governance_priority": "medium",
        "decay_rate": 0.025,
        "auto_protected": False,
        "default_priority": 6,
        "episodic_type": "decision",
    },
    "attention_state": {
        "description": "注意力状态 (hybrid: dynamic field + persisted snapshot)",
        "limit": 600,
        "importance": 0.78,
        "always_in_context": True,
        "category": BlockCategory.CORE,
        "governance_priority": "medium",
        "decay_rate": 0.0,
        "auto_protected": False,
        "default_priority": 4,
        "hybrid": True,
        "managed_by": "DynamicAttentionField",
        "schema": {
            "focus_level": "float",
            "current_targets": "list",
            "focus_scores": "dict",
            "decay_rate": "float",
            "last_shift_timestamp": "iso8601",
        },
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
        "default_priority": 7,
    },
    "reflective_trace": {
        "description": "Reflexion 风格交互反思记录",
        "limit": 4000,
        "importance": 0.72,
        "always_in_context": False,
        "category": BlockCategory.ARCHIVAL,
        "governance_priority": "medium",
        "decay_rate": 0.02,
        "auto_protected": False,
        "default_priority": 7,
    },
    "belief_store": {
        "description": "信念存储 (BeliefEngine cross-ref)",
        "limit": 10000,
        "importance": 0.60,
        "always_in_context": False,
        "category": BlockCategory.ARCHIVAL,
        "governance_priority": "high",
        "decay_rate": 0.01,
        "auto_protected": False,
        "default_priority": 7,
    },
    "narrative": {
        "description": "叙事自我摘要 (NarrativeBuilder cross-ref)",
        "limit": 6000,
        "importance": 0.72,
        "always_in_context": False,
        "category": BlockCategory.ARCHIVAL,
        "governance_priority": "medium",
        "decay_rate": 0.015,
        "auto_protected": False,
        "default_priority": 6,
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
        "default_priority": 8,
    },
}

AUTO_PROTECTED_LABELS = frozenset(
    label for label, spec in BLOCK_SPECS.items() if spec.get("auto_protected")
)

LABEL_PRIORITY: Dict[str, float] = {
    "persona": 1.0,
    "intent": 0.95,
    "user_profile": 0.90,
    "attention_state": 0.90,
    "emotion": 0.85,
    "working_memory": 0.80,
    "episodic_event": 0.70,
    "episodic_decision": 0.60,
    "episodic_dialogue": 0.60,
    "archival_facts": 0.50,
    "belief_store": 0.48,
    "narrative": 0.46,
    "reflective_trace": 0.45,
    "value_alignment_history": 0.42,
}

# v0.1 HierarchicalRecall rank table (float scores, BlockType-aligned).
RECALL_PRIORITY_RANK: Dict[str, float] = {
    BlockType.PERSONA.value: 1.0,
    BlockType.ATTENTION_STATE.value: 0.90,
    BlockType.EMOTION.value: 0.85,
    BlockType.USER_PROFILE.value: 0.80,
    BlockType.INTENT.value: 0.78,
    BlockType.WORKING_MEMORY.value: 0.77,
    BlockType.EPISODIC_EVENT.value: 0.75,
    BlockType.DIALOGUE_TRACE.value: 0.70,
    BlockType.DECISION_TRACE.value: 0.65,
    BlockType.BELIEF_STORE.value: 0.60,
    BlockType.NARRATIVE.value: 0.55,
    BlockType.ARCHIVAL_FACTS.value: 0.50,
    BlockType.REFLECTIVE_TRACE.value: 0.45,
    BlockType.VALUE_ALIGNMENT_HISTORY.value: 0.40,
}


def label_recall_priority(label: str) -> float:
    """Return recall priority for a block label (alias-normalized)."""
    canonical = normalize_block_label(label)
    rank_score = RECALL_PRIORITY_RANK.get(canonical, 0.0)
    base = LABEL_PRIORITY.get(canonical, 0.5)
    return max(base, rank_score) if rank_score > 0 else base


class MemoryBlock(BaseModel):
    block_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    description: str = ""
    content: str = ""
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
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provenance_hash: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    def touch(self) -> None:
        self.last_accessed_at = datetime.now()
        self.updated_at = self.last_accessed_at

    def decay_weight(self, hours_since_last: float) -> float:
        if hours_since_last <= 0:
            return 1.0
        return max(0.1, (1 - self.decay_rate) ** hours_since_last)

    def decay(self, hours_since_last: float) -> float:
        """Alias for decay_weight — used by MemoryBlockStore lifecycle helpers."""
        return self.decay_weight(hours_since_last)

    @property
    def priority(self) -> int:
        spec = BLOCK_SPECS.get(self.label, {})
        return int(spec.get("default_priority", 5))

    @property
    def last_access(self) -> datetime:
        return self.last_accessed_at

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump_for_storage()

    def update_content(self, new_content: Union[str, Dict[str, Any]], *, reason: str = "runtime_update") -> None:
        if isinstance(new_content, dict):
            serialized = json.dumps(new_content, ensure_ascii=False)
        else:
            serialized = str(new_content)
        self.content = serialized[: self.limit]
        self.version += 1
        self.updated_at = datetime.now()
        self.metadata["last_update_reason"] = reason
        self.touch()

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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "MemoryBlock":
        spec = BLOCK_SPECS.get(label, {})
        raw_cat = spec.get("category", BlockCategory.ARCHIVAL)
        category = raw_cat.value if isinstance(raw_cat, BlockCategory) else str(raw_cat)
        auto_protected = bool(spec.get("auto_protected", False))
        block_cls = _resolve_block_class(label)
        extra: Dict[str, Any] = {}
        if issubclass(block_cls, EpisodicMemoryBlock):
            extra["episodic_type"] = str(spec.get("episodic_type", "event"))
        return block_cls(
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
            metadata=metadata or {},
            **extra,
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
        if "metadata" not in payload:
            payload["metadata"] = {}
        label = str(payload.get("label", ""))
        block_cls = _resolve_block_class(label)
        if block_cls is not MemoryBlock and issubclass(block_cls, MemoryBlock):
            if issubclass(block_cls, EpisodicMemoryBlock) and "episodic_type" not in payload:
                spec = BLOCK_SPECS.get(label, {})
                payload["episodic_type"] = str(spec.get("episodic_type", "event"))
            return block_cls(**payload)
        return cls(**payload)


class EpisodicMemoryBlock(MemoryBlock):
    episodic_type: str = "event"
    embedding_ref: Optional[str] = None
    graph_node_id: Optional[str] = None

    def parse_payload(self) -> List[Dict[str, Any]]:
        if not self.content:
            return []
        try:
            parsed = json.loads(self.content)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            entries = parsed.get("entries")
            return entries if isinstance(entries, list) else [parsed]
        return []

    def serialize_payload(self, entries: List[Dict[str, Any]]) -> str:
        return json.dumps({"entries": entries}, ensure_ascii=False)

    def add_structured_entry(self, entry: Dict[str, Any]) -> None:
        normalized = self.normalize_entry(entry)
        entries = self.parse_payload()
        entries.append(
            {
                **normalized,
                "entry_id": str(uuid.uuid4()),
                "timestamp": utc_now().isoformat(),
            }
        )
        trimmed = entries[-200:]
        self.content = self.serialize_payload(trimmed)[: self.limit]
        self.version += 1
        self.updated_at = datetime.now()
        self.metadata["last_update_reason"] = "episodic_entry"
        self.touch()

    def normalize_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Map loose capture payloads onto typed episodic schema fields."""
        normalized = dict(entry)
        if self.episodic_type == "event":
            normalized.setdefault(
                "event_id",
                entry.get("entry_id") or entry.get("episodic_id") or str(uuid.uuid4()),
            )
            normalized.setdefault("timestamp", entry.get("timestamp") or utc_now().isoformat())
            normalized.setdefault("type", entry.get("layer", "event"))
            normalized.setdefault("payload", entry.get("content") or entry.get("payload"))
        elif self.episodic_type == "dialogue":
            normalized.setdefault("turn_id", entry.get("entry_id") or entry.get("episodic_id"))
            normalized.setdefault("speaker", entry.get("role", "user"))
            normalized.setdefault(
                "content_summary",
                str(entry.get("content") or entry.get("utterance") or "")[:500],
            )
        elif self.episodic_type == "decision":
            normalized.setdefault("decision_id", entry.get("reflection_id") or entry.get("entry_id"))
            normalized.setdefault("context_snapshot", entry.get("context_snapshot") or entry.get("context"))
            normalized.setdefault("chosen_action", entry.get("chosen_action") or entry.get("content"))
            normalized.setdefault("outcome", entry.get("outcome") or entry.get("reflection"))
        return normalized

    def validate_entry(self, entry: Dict[str, Any]) -> List[str]:
        optional = {"linked_decisions", "linked_events", "emotion_delta", "embedding"}
        required = EPISODIC_ENTRY_SCHEMAS.get(self.episodic_type, [])
        errors: List[str] = []
        normalized = self.normalize_entry(entry)
        for field in required:
            if field in optional:
                continue
            if normalized.get(field) in (None, "", []):
                errors.append(f"missing {field}")
        return errors

    def get_recent(self, n: int = 5) -> List[Dict[str, Any]]:
        entries = self.parse_payload()
        return sorted(entries, key=lambda x: x.get("timestamp", ""), reverse=True)[:n]

    @property
    def timestamp(self) -> datetime:
        recent = self.get_recent(1)
        if recent and recent[0].get("timestamp"):
            try:
                return datetime.fromisoformat(str(recent[0]["timestamp"]).replace("Z", "+00:00"))
            except ValueError:
                pass
        return self.updated_at

    @property
    def payload(self) -> List[Dict[str, Any]]:
        return self.parse_payload()

    @property
    def related_blocks(self) -> List[str]:
        return list(self.metadata.get("related_blocks") or [])

    def link_blocks(self, block_ids: List[str]) -> None:
        merged = sorted(set(self.related_blocks + [str(item) for item in block_ids if item]))
        self.metadata["related_blocks"] = merged
        self.touch()

    def set_graph_edge(self, edge: Optional[Dict[str, Any]]) -> None:
        self.metadata["graph_edge"] = edge
        self.touch()


class AttentionStateBlock(MemoryBlock):
    focus_level: float = 0.5
    decay_rate: float = 0.0

    def read_snapshot(self) -> Dict[str, Any]:
        if self.metadata.get("focus_scores") is not None:
            return {
                "focus_scores": self.metadata.get("focus_scores", {}),
                "top_focus": self.metadata.get("top_focus", []),
                "last_sync_turn": self.metadata.get("last_sync_turn", 0),
                "total_attention_mass": self.metadata.get("total_attention_mass", 1.0),
                "focus_level": float(self.metadata.get("focus_level", self.focus_level)),
                "current_targets": list(self.metadata.get("current_targets") or []),
                "decay_rate": float(self.metadata.get("decay_rate", self.decay_rate)),
                "last_shift_timestamp": self.metadata.get("last_shift_timestamp"),
            }
        if not self.content:
            return {}
        try:
            return json.loads(self.content)
        except json.JSONDecodeError:
            return {}

    def validate(self) -> List[str]:
        snap = self.read_snapshot()
        errors: List[str] = []
        if not snap.get("focus_scores"):
            errors.append("missing focus_scores")
        if snap.get("focus_level") is None:
            errors.append("missing focus_level")
        return errors

    def to_context_string(self) -> str:
        snap = self.read_snapshot()
        if not snap:
            return "【Attention State】\n• focus: balanced"
        targets = snap.get("top_focus") or snap.get("current_targets") or []
        level = float(snap.get("focus_level", 0.5))
        target_text = ", ".join(str(t) for t in targets[:4]) or "none"
        return (
            "【Attention State】\n"
            f"• focus_level={level:.2f}\n"
            f"• current_targets={target_text}\n"
            f"• last_shift={snap.get('last_shift_timestamp', 'unknown')}"
        )

    def edit_via_tool(self, updates: Dict[str, Any], *, reason: str = "tool_edit") -> None:
        snap = self.read_snapshot()
        focus_scores = dict(snap.get("focus_scores") or {})
        top_focus = list(snap.get("top_focus") or [])
        if "focus_scores" in updates and isinstance(updates["focus_scores"], dict):
            focus_scores.update(updates["focus_scores"])
        if "current_targets" in updates:
            top_focus = list(updates["current_targets"])
        turn = int(updates.get("last_sync_turn", snap.get("last_sync_turn", 0)))
        self.sync_from_dynamic(focus_scores, top_focus, turn, reason=reason)
        if "focus_level" in updates:
            self.metadata["focus_level"] = float(updates["focus_level"])
            self.focus_level = float(updates["focus_level"])

    def sync_from_dynamic(
        self,
        focus_scores: Dict[str, float],
        top_focus: List[str],
        turn: int,
        *,
        reason: str = "attention_sync_from_dynamic_field",
    ) -> None:
        focus_level = max(focus_scores.values()) if focus_scores else 0.5
        snapshot = {
            "focus_scores": focus_scores,
            "top_focus": top_focus,
            "current_targets": top_focus,
            "last_sync_turn": turn,
            "total_attention_mass": sum(focus_scores.values()) or 1.0,
            "focus_level": focus_level,
            "decay_rate": self.decay_rate,
            "last_shift_timestamp": utc_now().isoformat(),
        }
        self.content = json.dumps(snapshot, ensure_ascii=False)[: self.limit]
        self.metadata.update(snapshot)
        self.metadata["last_update_reason"] = reason
        self.focus_level = float(focus_level)
        self.version += 1
        self.updated_at = datetime.now()
        self.touch()

    def update_from_field(
        self,
        field_data: Dict[str, Any],
        *,
        last_updated_by: str = "DynamicAttentionField",
        turn: Optional[int] = None,
    ) -> None:
        """Mid-term API — sync DynamicAttentionField payload into persisted snapshot."""
        snap = self.read_snapshot()
        focus_scores = dict(field_data.get("focus_scores") or snap.get("focus_scores") or {})
        top_focus = list(
            field_data.get("top_focus")
            or field_data.get("current_targets")
            or snap.get("top_focus")
            or []
        )
        dynamic_field = dict(field_data.get("dynamic_field") or {})
        if dynamic_field.get("recent_topics") and not top_focus:
            top_focus = [str(item).replace(" ", "_") for item in dynamic_field["recent_topics"]]
        if field_data.get("focus") and not top_focus:
            top_focus = [part.strip() for part in str(field_data["focus"]).split("+") if part.strip()]
        sync_turn = int(
            turn
            if turn is not None
            else field_data.get("last_sync_turn", snap.get("last_sync_turn", 0))
        )
        self.sync_from_dynamic(
            focus_scores,
            top_focus,
            sync_turn,
            reason=f"sync_from_{last_updated_by}",
        )
        if dynamic_field:
            merged = dict(self.metadata.get("dynamic_field") or {})
            merged.update(dynamic_field)
            self.metadata["dynamic_field"] = merged
        if field_data.get("priority") is not None:
            self.metadata["recall_priority"] = int(field_data["priority"])
        if field_data.get("focus"):
            self.metadata["focus"] = str(field_data["focus"])
        self.metadata["last_updated_by"] = last_updated_by

    @property
    def focus(self) -> str:
        if self.metadata.get("focus"):
            return str(self.metadata["focus"])
        snap = self.read_snapshot()
        targets = snap.get("top_focus") or snap.get("current_targets") or []
        topics = (self.metadata.get("dynamic_field") or {}).get("recent_topics") or []
        if topics:
            return " + ".join(str(item) for item in topics[:3])
        return " + ".join(str(item) for item in targets[:3]) or "balanced"

    @property
    def dynamic_field(self) -> Dict[str, Any]:
        return dict(self.metadata.get("dynamic_field") or {})

    @property
    def recall_priority(self) -> int:
        return int(self.metadata.get("recall_priority", self.priority))


class PersonaBlock(MemoryBlock):
    label: str = "persona"


class EmotionBlock(MemoryBlock):
    label: str = "emotion"


class IntentBlock(MemoryBlock):
    label: str = "intent"


class WorkingMemoryBlock(MemoryBlock):
    label: str = "working_memory"


class UserProfileBlock(MemoryBlock):
    label: str = "user_profile"


class EpisodicEventBlock(EpisodicMemoryBlock):
    label: str = "episodic_event"
    episodic_type: str = "event"

    @property
    def event_type(self) -> str:
        recent = self.get_recent(1)
        if recent:
            return str(recent[0].get("type") or self.metadata.get("event_type") or "event")
        return str(self.metadata.get("event_type") or "event")


class DialogueTraceBlock(EpisodicMemoryBlock):
    label: str = "episodic_dialogue"
    episodic_type: str = "dialogue"

    @property
    def session_id(self) -> str:
        return str(self.metadata.get("session_id") or "")

    @property
    def turns(self) -> List[Dict[str, Any]]:
        return self.parse_payload()

    @property
    def summary(self) -> str:
        if self.metadata.get("summary"):
            return str(self.metadata["summary"])
        recent = self.get_recent(3)
        return " | ".join(str(item.get("content_summary", "")) for item in recent if item)


class DecisionTraceBlock(EpisodicMemoryBlock):
    label: str = "episodic_decision"
    episodic_type: str = "decision"

    @property
    def decision_id(self) -> str:
        recent = self.get_recent(1)
        if recent and recent[0].get("decision_id"):
            return str(recent[0]["decision_id"])
        return str(self.metadata.get("decision_id") or "")

    @property
    def intent(self) -> str:
        return str(self.metadata.get("intent") or "")

    @property
    def reasoning(self) -> str:
        return str(self.metadata.get("reasoning") or self.metadata.get("cot") or "")

    @property
    def outcome(self) -> str:
        recent = self.get_recent(1)
        if recent and recent[0].get("outcome"):
            return str(recent[0]["outcome"])
        return str(self.metadata.get("outcome") or "")

    @property
    def linked_reflection(self) -> Optional[str]:
        recent = self.get_recent(1)
        if recent and recent[0].get("reflection_id"):
            return str(recent[0]["reflection_id"])
        value = self.metadata.get("linked_reflection")
        return str(value) if value else None


_BLOCK_CLASS_MAP: Dict[str, Type[MemoryBlock]] = {
    "persona": PersonaBlock,
    "emotion": EmotionBlock,
    "intent": IntentBlock,
    "working_memory": WorkingMemoryBlock,
    "user_profile": UserProfileBlock,
    "episodic_event": EpisodicEventBlock,
    "episodic_dialogue": DialogueTraceBlock,
    "episodic_decision": DecisionTraceBlock,
    "attention_state": AttentionStateBlock,
}


def _resolve_block_class(label: str) -> Type[MemoryBlock]:
    if label in _BLOCK_CLASS_MAP:
        return _BLOCK_CLASS_MAP[label]
    return MemoryBlock


def create_episodic_block(
    episodic_type: str,
    initial_payload: Optional[Dict[str, Any]] = None,
) -> EpisodicMemoryBlock:
    label = EPISODIC_TYPE_TO_LABEL.get(episodic_type, "episodic_event")
    spec = BLOCK_SPECS[label]
    block = EpisodicMemoryBlock(
        label=label,
        episodic_type=episodic_type,
        description=str(spec.get("description", "")),
        content="",
        limit=int(spec["limit"]),
        importance=float(spec["importance"]),
        category=BlockCategory.EPISODIC.value,
        decay_rate=float(spec.get("decay_rate", 0.03)),
    )
    typed_cls = _resolve_block_class(label)
    if typed_cls is not EpisodicMemoryBlock:
        block = typed_cls(**block.model_dump())
    if initial_payload:
        block.add_structured_entry(initial_payload)
    return block


def create_block_from_spec(
    label: str,
    initial_content: Optional[Union[str, Dict[str, Any]]] = None,
    **kwargs: Any,
) -> MemoryBlock:
    label = normalize_block_label(label)
    spec = BLOCK_SPECS.get(label)
    if not spec:
        content = initial_content if isinstance(initial_content, str) else json.dumps(
            initial_content or {}, ensure_ascii=False
        )
        return MemoryBlock(label=label, content=content, **kwargs)

    if label in EPISODIC_LABELS:
        episodic_type = str(spec.get("episodic_type", "event"))
        payload = initial_content if isinstance(initial_content, dict) else None
        return create_episodic_block(episodic_type, payload)

    if label == "attention_state":
        content = json.dumps(initial_content or {}, ensure_ascii=False)
        return AttentionStateBlock.from_label(label, content, **kwargs)

    content = initial_content if isinstance(initial_content, str) else json.dumps(
        initial_content or {}, ensure_ascii=False
    )
    return MemoryBlock.from_label(label, content, **kwargs)

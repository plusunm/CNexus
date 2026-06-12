"""EmotionEngine — persistent affective continuity via emotion MemoryBlock."""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from memory.block import BLOCK_SPECS, MemoryBlock
from memory.manager import MemoryManager

EMOTION_LABEL = "emotion"
MAX_EVENT_TRIGGERS = 20


class EmotionState(BaseModel):
    """Structured payload stored in the emotion MemoryBlock.content (JSON)."""

    valence: float = Field(0.0, ge=-1.0, le=1.0)
    arousal: float = Field(0.5, ge=0.0, le=1.0)
    dominance: float = Field(0.5, ge=0.0, le=1.0)
    primary_emotion: str = "neutral"
    intensity: float = Field(0.5, ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=datetime.now)
    decay_factor: float = 1.0
    event_triggers: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EmotionEngine:
    """Event-driven emotion continuity engine backed by L1 emotion MemoryBlock."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.decay_rate = float(BLOCK_SPECS.get(EMOTION_LABEL, {}).get("decay_rate", 0.01))

    # ── serialization ──────────────────────────────────────────────────

    @staticmethod
    def _dump_state(state: EmotionState) -> str:
        return json.dumps(state.model_dump(mode="json"), ensure_ascii=False)

    @staticmethod
    def _load_state(content: str) -> EmotionState:
        if not content or not str(content).strip():
            return EmotionState()
        text = str(content).strip()
        if not text.startswith("{"):
            return EmotionState(metadata={"legacy_text": text[:200]})
        try:
            data = json.loads(text)
            return EmotionState(**data)
        except (json.JSONDecodeError, TypeError, ValueError):
            return EmotionState()

    def _get_or_create_block(self) -> MemoryBlock:
        block = self.memory.get_active_block(EMOTION_LABEL, touch=False)
        if block:
            return block
        initial = EmotionState()
        created = self.memory.create_block(
            EMOTION_LABEL,
            self._dump_state(initial),
            importance=0.7,
            source="emotion_engine",
        )
        if isinstance(created, dict):
            raise RuntimeError(f"failed to create emotion block: {created}")
        self.memory.protect_block(EMOTION_LABEL)
        return created

    # ── core update ────────────────────────────────────────────────────

    def update_from_interaction(
        self,
        role: str,
        content: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.6,
    ) -> EmotionState:
        """Update emotion state from an interaction turn (Replika-style continuity)."""
        block = self._get_or_create_block()
        state = self._load_state(block.content)

        delta_valence, delta_arousal, primary = self._analyze_emotion_signal(
            role, content, context
        )

        state.valence = max(-1.0, min(1.0, state.valence + delta_valence * importance))
        state.arousal = max(0.0, min(1.0, state.arousal + delta_arousal * importance))
        state.primary_emotion = primary
        state.intensity = min(1.0, state.intensity + abs(delta_valence) * 0.3)
        state.last_updated = datetime.now()
        state.event_triggers.append({
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "summary": (content or "")[:120],
            "delta": {"valence": delta_valence, "arousal": delta_arousal},
        })
        if len(state.event_triggers) > MAX_EVENT_TRIGGERS:
            state.event_triggers = state.event_triggers[-MAX_EVENT_TRIGGERS:]

        payload = self._dump_state(state)
        gov = self.memory.governance.check(EMOTION_LABEL, payload, importance)
        if not gov.allowed:
            return self._load_state(block.content)

        state.metadata["governance_status"] = gov.status
        if gov.consistency_flags:
            state.metadata["consistency_flags"] = gov.consistency_flags

        self._apply_decay(state)
        result = self.memory.update_block(
            block.block_id,
            self._dump_state(state),
            source="emotion_engine",
        )
        if isinstance(result, dict) and result.get("denied"):
            return self._load_state(block.content)
        return state

    def _analyze_emotion_signal(
        self,
        role: str,
        content: str,
        context: Optional[Dict[str, Any]],
    ) -> tuple[float, float, str]:
        text = (content or "").lower()
        if any(w in text for w in ["开心", "高兴", "感谢", "谢谢", "love", "great", "wonderful"]):
            return 0.4, 0.3, "joy"
        if any(w in text for w in ["难过", "sad", "tired", "lonely", "depressed", "伤心"]):
            return -0.35, 0.2, "sadness"
        if any(w in text for w in ["好奇", "interesting", "why", "how", "为什么", "怎么"]):
            return 0.15, 0.4, "curiosity"
        if any(w in text for w in ["生气", "angry", "frustrated", "hate", "愤怒"]):
            return -0.3, 0.5, "anger"
        if any(w in text for w in ["担心", "afraid", "fear", "焦虑", "害怕"]):
            return -0.25, 0.55, "fear"
        if role == "assistant" and context and context.get("positive_feedback"):
            return 0.2, 0.15, "joy"
        return 0.05, 0.1, "neutral"

    def _apply_decay(self, state: EmotionState) -> None:
        hours = max(0.0, (datetime.now() - state.last_updated).total_seconds() / 3600.0)
        if hours < 0.01 or self.decay_rate <= 0.0:
            return
        decay = math.exp(-self.decay_rate * hours)
        state.valence *= decay
        state.arousal = max(0.3, state.arousal * decay)
        state.decay_factor = round(decay, 4)

    def refresh_decay(self) -> Optional[EmotionState]:
        """Re-apply time decay and persist (e.g. during maintenance)."""
        block = self.memory.get_active_block(EMOTION_LABEL, touch=False)
        if not block:
            return None
        state = self._load_state(block.content)
        self._apply_decay(state)
        updated = self.memory.update_block(
            block.block_id,
            self._dump_state(state),
            source="emotion_decay",
        )
        return state if isinstance(updated, MemoryBlock) else None

    # ── modulation (L2 / recall / prompt) ─────────────────────────────

    def get_modulation(self) -> Dict[str, Any]:
        """Attention / recall / prompt modulation parameters."""
        block = self.memory.get_active_block(EMOTION_LABEL, touch=True)
        if not block:
            return {
                "valence_bias": 0.0,
                "arousal_boost": 0.0,
                "primary_emotion": "neutral",
                "intensity": 0.5,
                "tone": "neutral",
                "recall_weight_boost": 0.0,
            }

        state = self._load_state(block.content)
        self._apply_decay(state)
        return {
            "valence_bias": round(state.valence * 0.4, 4),
            "arousal_boost": round(state.arousal * 0.3, 4),
            "primary_emotion": state.primary_emotion,
            "intensity": round(state.intensity, 4),
            "tone": self._emotion_to_tone(state.primary_emotion),
            "recall_weight_boost": 0.2 if state.arousal > 0.6 else 0.0,
            "decay_factor": state.decay_factor,
        }

    @staticmethod
    def _emotion_to_tone(emotion: str) -> str:
        mapping = {
            "joy": "warm and encouraging",
            "sadness": "empathetic and gentle",
            "curiosity": "inquisitive and engaged",
            "anger": "calm and steady",
            "fear": "reassuring and steady",
            "neutral": "balanced and thoughtful",
        }
        return mapping.get(emotion, "balanced and thoughtful")

    def get_state_summary(self) -> Dict[str, Any]:
        block = self.memory.get_active_block(EMOTION_LABEL, touch=False)
        if not block:
            return {"primary_emotion": "neutral", "intensity": 0.5}
        state = self._load_state(block.content)
        return state.model_dump(mode="json")

    def format_context_block(self) -> str:
        mod = self.get_modulation()
        return (
            f"【Emotion Context】\n"
            f"• primary={mod['primary_emotion']} intensity={mod['intensity']:.2f} "
            f"tone={mod['tone']} valence_bias={mod['valence_bias']:.2f}"
        )

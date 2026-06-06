"""G2 — Persistent Working Self (Memory is State)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.personality.dna_schema import PersonalityDNA
    from runtime.cognitive_parser import ParsedCognitiveState
    from runtime.state import CognitiveStateManager


@dataclass
class PersistentCognitiveState:
    """持久化工作自我 — anticipatory cognitive state carrier."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    goal_focus: str = "general"
    emotional_intensity: float = 0.3
    cognitive_load: float = 0.4
    identity_threat: float = 0.0
    relationship_tone: float = 0.7
    prediction_error: float = 0.0
    cumulative_coherence: float = 0.85
    turn_count: int = 0
    recent_reflections: List[str] = field(default_factory=list)

    def update_from_input(
        self,
        user_input: str,
        dna: "PersonalityDNA",
        *,
        parsed: Optional["ParsedCognitiveState"] = None,
        layer: str = "episodic",
        importance: float = 0.5,
    ) -> None:
        """State transition driven by input + personality attractor."""
        text = user_input.lower()
        self.turn_count += 1
        self.timestamp = datetime.now().isoformat()

        if any(k in text for k in ("目标", "计划", "长期", "goal")):
            self.goal_focus = "goal"
        elif any(k in text for k in ("身份", "我是谁", "identity")):
            self.goal_focus = "identity"
        elif layer in ("goal", "identity", "belief"):
            self.goal_focus = layer

        arousal = min(0.95, self.emotional_intensity + importance * 0.12)
        if parsed and parsed.dissonance_score > 0.4:
            arousal = min(0.95, arousal + parsed.dissonance_score * 0.2)
        self.emotional_intensity = arousal
        self.cognitive_load = min(0.95, self.cognitive_load + 0.04 + importance * 0.03)

        neuroticism = 1.0 - dna.emotional_stability
        if neuroticism > 0.35 and any(k in text for k in ("变了", "不像", "矛盾", "失望")):
            self.identity_threat = min(1.0, self.identity_threat + 0.1 * neuroticism)

        if parsed:
            self.relationship_tone = max(
                0.0, min(1.0, self.relationship_tone + parsed.relation_shift)
            )

    def update_prediction_error(self, expected_tone: float = 0.5) -> float:
        """Predictive processing — mismatch between expected and felt state."""
        self.prediction_error = abs(self.emotional_intensity - expected_tone) * 0.6 + abs(
            self.relationship_tone - expected_tone
        ) * 0.4
        self.cumulative_coherence = max(
            0.2,
            self.cumulative_coherence * 0.98 + (1.0 - self.prediction_error) * 0.02,
        )
        return self.prediction_error

    def decay(self) -> None:
        self.emotional_intensity *= 0.92
        self.cognitive_load *= 0.95
        self.identity_threat *= 0.88
        self.prediction_error *= 0.9

    def add_reflection(self, summary: str, max_items: int = 8) -> None:
        self.recent_reflections.append(summary[:200])
        if len(self.recent_reflections) > max_items:
            self.recent_reflections = self.recent_reflections[-max_items:]

    def sync_to_legacy(self, manager: "CognitiveStateManager") -> None:
        manager.update_cognitive_load(self.cognitive_load)
        if self.goal_focus != "general":
            manager.update_goal_focus(self.goal_focus, strength=0.85)
        if self.identity_threat > 0.55:
            manager.update_identity_mode("conflicted")
        elif self.prediction_error > 0.5:
            manager.update_identity_mode("reflective")
        else:
            manager.update_identity_mode("stable")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersistentCognitiveState":
        allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in allowed})

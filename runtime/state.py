import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class CognitiveStateManager:
    """Cognitive State Manager — 运行时认知状态跟踪系统"""

    def __init__(self):
        self.current_goal_focus: Optional[str] = None
        self.current_relationship_focus: Optional[str] = None
        self.current_identity_mode: str = "stable"
        self.active_beliefs: Dict[str, Dict] = {}
        self.attention_entropy: float = 0.0
        self.cognitive_load: float = 0.0
        self.last_update = time.time()
        self.history: List[Dict] = []

    def update_goal_focus(self, goal: str, strength: float = 0.85):
        self.current_goal_focus = goal
        self._record_state_change("goal_focus", goal)

    def update_relationship_focus(self, relationship: str, strength: float = 0.8):
        self.current_relationship_focus = relationship
        self._record_state_change("relationship_focus", relationship)

    def update_identity_mode(self, mode: str):
        allowed = {"stable", "adaptive", "reflective", "conflicted"}
        if mode in allowed:
            self.current_identity_mode = mode
            self._record_state_change("identity_mode", mode)

    def add_active_belief(self, key: str, content: str, confidence: float = 0.75):
        self.active_beliefs[key] = {
            "content": content,
            "confidence": max(0.1, min(1.0, confidence)),
            "last_updated": datetime.now().isoformat(),
        }
        self._record_state_change("belief", key)

    def remove_belief(self, key: str):
        self.active_beliefs.pop(key, None)

    def calculate_attention_entropy(self, attention_scores: List[float]) -> float:
        if not attention_scores:
            return 0.0
        scores = [max(0.01, s) for s in attention_scores]
        total = sum(scores)
        probs = [s / total for s in scores]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        self.attention_entropy = (
            min(1.0, entropy / math.log2(len(scores)) if len(scores) > 1 else 0.0)
        )
        return self.attention_entropy

    def update_cognitive_load(self, load: float):
        self.cognitive_load = max(0.0, min(1.0, load))

    def _record_state_change(self, change_type: str, value: Any):
        self.history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": change_type,
                "value": value,
                "cognitive_load": self.cognitive_load,
                "entropy": self.attention_entropy,
            }
        )
        if len(self.history) > 100:
            self.history.pop(0)

    def get_full_state(self) -> Dict[str, Any]:
        return {
            "current_goal_focus": self.current_goal_focus,
            "current_relationship_focus": self.current_relationship_focus,
            "current_identity_mode": self.current_identity_mode,
            "active_beliefs": self.active_beliefs,
            "attention_entropy": self.attention_entropy,
            "cognitive_load": self.cognitive_load,
            "last_update": datetime.now().isoformat(),
            "history_length": len(self.history),
        }

    def get_stability_metrics(self) -> Dict[str, float]:
        return {
            "attention_entropy": self.attention_entropy,
            "cognitive_load": self.cognitive_load,
            "belief_count": len(self.active_beliefs),
            "identity_stability": 1.0 - self.attention_entropy * 0.6,
            "load_risk": 1.0 if self.cognitive_load > 0.85 else 0.0,
        }

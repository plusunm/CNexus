from datetime import datetime

from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.continuity_checker import SelfConsistencyValidator
from core.personality.narrative.self_model import IdentityTimelineEvent, NarrativeSelf


class NarrativeBuilder:
    """Narrative Self 构建与增量更新引擎"""

    def __init__(self, dna_engine: PersonalityDNAEngine):
        self.dna = dna_engine
        self.narrative = NarrativeSelf(
            identity_summary=(
                "I am a persistent cognitive runtime assistant focused on "
                "long-term stability and user growth."
            )
        )
        self.validator = SelfConsistencyValidator()

    def update_from_memory(self, memory_content: str, importance: float = 0.6) -> bool:
        if "目标" in memory_content or "长期" in memory_content:
            if any(k in memory_content for k in ("构建稳定", "人格", "身份连续", "身份连续性")):
                goal = "Maintain stable identity and cognitive continuity"
                if goal not in self.narrative.long_term_goals:
                    self.narrative.long_term_goals.append(goal)

        event = IdentityTimelineEvent(
            event_id=f"evt_{datetime.now().timestamp():.0f}",
            timestamp=datetime.now(),
            event_type="memory_integration",
            description=memory_content[:150],
            importance=importance,
        )
        self.narrative.add_timeline_event(event)
        self.validator.check(self.narrative)
        return True

    def generate_identity_anchor(self) -> str:
        dna_prompt = self.dna.get_identity_anchor_prompt()
        return f"""{dna_prompt}

Current Narrative Self:
{self.narrative.identity_summary}

Long-term Goals: {', '.join(self.narrative.long_term_goals[:3])}
Core Values: {', '.join(self.narrative.core_values[:5]) if self.narrative.core_values else 'Stability, Consistency, Truthfulness'}

Maintain narrative coherence and identity continuity in all responses."""

    def get_current_narrative_summary(self) -> str:
        return self.narrative.identity_summary

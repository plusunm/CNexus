from datetime import datetime
from typing import List, Tuple

from core.personality.narrative.self_model import NarrativeSelf


class SelfConsistencyValidator:
    """自我一致性校验器"""

    def check(self, narrative: NarrativeSelf) -> Tuple[bool, List[str], float]:
        issues = []
        score = 1.0

        if len(narrative.core_values) > 8:
            issues.append("Too many core values — risk of fragmentation")
            score *= 0.85

        if len(narrative.key_milestones) > 30:
            recent = narrative.key_milestones[-10:]
            if any("放弃" in e.description and "坚持" in e.description for e in recent):
                issues.append("Contradictory behavior detected in recent timeline")
                score *= 0.75

        coherence = max(0.3, score)
        narrative.narrative_coherence_score = coherence

        return len(issues) == 0, issues, coherence

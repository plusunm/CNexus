from datetime import datetime
from typing import Dict, List

from core.personality.dna_schema import PersonalityDNA


class DNAMutationGuard:
    """人格突变防护系统 — 防止快速漂移"""

    MAX_DELTA_PER_DAY = 0.012
    MAX_MUTATIONS_PER_WEEK = 5

    def __init__(self):
        self.last_mutation_time = datetime.now()
        self.mutation_history: List[Dict] = []

    def validate_mutation(self, current: PersonalityDNA, proposed: PersonalityDNA) -> tuple[bool, str]:
        now = datetime.now()
        days_since_last = (now - self.last_mutation_time).days

        total_delta = 0.0
        changed_fields = 0

        for field in current.model_fields:
            if field in ("version", "last_updated", "mutation_count"):
                continue
            old_val = getattr(current, field)
            new_val = getattr(proposed, field)
            delta = abs(new_val - old_val)
            total_delta += delta
            if delta > 0.001:
                changed_fields += 1

        if days_since_last < 1 and total_delta > self.MAX_DELTA_PER_DAY * (changed_fields + 1):
            return False, f"Daily mutation limit exceeded. Total delta: {total_delta:.4f}"

        recent_mutations = [m for m in self.mutation_history if (now - m["timestamp"]).days < 7]
        if len(recent_mutations) >= self.MAX_MUTATIONS_PER_WEEK:
            return False, "Weekly mutation frequency limit reached"

        return True, "Mutation approved"

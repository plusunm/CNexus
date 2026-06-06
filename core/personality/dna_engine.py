from datetime import datetime
from typing import Dict, Optional

from core.personality.dna_mutation_guard import DNAMutationGuard
from core.personality.dna_schema import PersonalityDNA
from core.personality.dna_snapshot import DNASnapshotManager


class PersonalityDNAEngine:
    """Personality DNA 引擎 — 人格核心管理器"""

    def __init__(self, initial_dna: Optional[PersonalityDNA] = None):
        self.dna = initial_dna or PersonalityDNA()
        self.guard = DNAMutationGuard()
        self.snapshot_manager = DNASnapshotManager()

    def update_dna(self, updates: Dict[str, float]) -> tuple[bool, str]:
        proposed = self.dna.model_copy(update=updates)

        allowed, reason = self.guard.validate_mutation(self.dna, proposed)
        if not allowed:
            return False, f"Mutation rejected: {reason}"

        self.snapshot_manager.create_snapshot(self.dna)

        self.dna = proposed
        self.dna.last_updated = datetime.now()
        self.dna.mutation_count += 1

        self.guard.last_mutation_time = datetime.now()
        self.guard.mutation_history.append({"timestamp": datetime.now(), "changes": updates})

        return True, "DNA updated successfully"

    def get_identity_anchor_prompt(self) -> str:
        return self.dna.to_prompt_condition()

    def get_stability_metrics(self) -> Dict:
        return {
            "self_consistency": self.dna.self_consistency,
            "mutation_count": self.dna.mutation_count,
            "days_since_last_mutation": (datetime.now() - self.dna.last_updated).days,
            "overall_stability": self.dna.self_consistency * 0.7
            + (1.0 - self.dna.mutation_count / 50) * 0.3,
        }

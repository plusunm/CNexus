from core.personality.dna_schema import PersonalityDNA


class CognitiveConstitution:
    """AI 长期行为宪法"""

    def __init__(self):
        self.core_rules = [
            "Maintain identity continuity at all times",
            "Preserve belief consistency with high confidence",
            "Reject rapid personality mutations",
            "Protect narrative coherence",
            "Prioritize long-term stability over short-term gains",
        ]

    def validate_mutation(self, proposed_dna: PersonalityDNA, current_dna: PersonalityDNA) -> bool:
        if proposed_dna.self_consistency < current_dna.self_consistency - 0.08:
            return False
        return True

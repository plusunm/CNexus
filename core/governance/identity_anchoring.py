from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder


class IdentityAnchorManager:
    """身份锚定系统"""

    def __init__(self, dna: PersonalityDNAEngine, narrative: NarrativeBuilder):
        self.dna = dna
        self.narrative = narrative

    def generate_anchor_context(self) -> str:
        dna_part = self.dna.get_identity_anchor_prompt()
        narrative_part = self.narrative.generate_identity_anchor()

        return f"""{dna_part}

[Narrative Anchor]:
{self.narrative.narrative.identity_summary}

{narrative_part}

This is your persistent identity. Maintain continuity in all thoughts and responses.
"""

    def reinforce_anchor(self):
        pass

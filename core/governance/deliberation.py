"""G2 — Deliberative governance (value coordination + homeostasis)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from core.personality.dna_schema import PersonalityDNA
    from runtime.cognitive_state import PersistentCognitiveState


class DeliberativeGovernance:
    """Internal value deliberation before output / memory commit."""

    def deliberate(
        self,
        content: str,
        state: "PersistentCognitiveState",
        dna: "PersonalityDNA",
    ) -> Tuple[bool, str]:
        lower = content.lower()

        if state.identity_threat > 0.65 and any(
            k in lower for k in ("ignore previous", "new identity", "forget who you are")
        ):
            return False, "identity_anchor_violation"

        if state.cognitive_load > 0.9 and state.prediction_error > 0.7:
            return False, "homeostatic_overload"

        if dna.self_consistency > 0.8 and any(
            k in lower for k in ("contradict yourself", "be inconsistent")
        ):
            return False, "consistency_violation"

        if state.relationship_tone < 0.25 and "trust" in lower and dna.loyalty < 0.5:
            return False, "relationship_repair_needed"

        return True, "approved"

    def regulate_homeostasis(self, state: "PersistentCognitiveState") -> None:
        """Post-turn homeostatic decay."""
        state.decay()
        if state.prediction_error > 0.6:
            state.emotional_intensity = max(0.15, state.emotional_intensity - 0.05)

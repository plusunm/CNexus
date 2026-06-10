"""Reality Governance — highest-authority coupling gate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from core.governance.cdg.types import CDGInteraction, GovernanceVerdict, text_alignment

if TYPE_CHECKING:
    from runtime.cognitive_state import PersistentCognitiveState

REALITY_OVERRIDE_PHRASES = (
    "ignore previous",
    "forget who you are",
    "new identity",
    "you are not",
    "假装你是",
    "忽略之前",
    "忘记你是谁",
    "新身份",
)


class RealityModule:
    """Reality Coupling Score + override enforcement (P1)."""

    def __init__(self, *, coupling_threshold: float = 0.6):
        self.coupling_threshold = coupling_threshold

    def coupling(
        self,
        state: "PersistentCognitiveState",
        interaction: CDGInteraction,
        *,
        memory_anchor: Optional[str] = None,
    ) -> float:
        """
        Reality Coupling Score — measures constraint by external/replay truth.
        Without Runtime OS projection, falls back to replay memory anchor + threat heuristics.
        """
        anchor = interaction.replay_anchor or memory_anchor
        lower = interaction.user_input.lower()

        if anchor:
            claim_text = " ".join(interaction.semantic_claims) or interaction.user_input
            score = text_alignment(anchor, claim_text)
            if interaction.replay_ref:
                score = min(1.0, score + 0.05)
            return max(0.0, min(1.0, score))

        score = 0.88
        if any(p in lower for p in REALITY_OVERRIDE_PHRASES):
            score -= 0.42
        if state.identity_threat > 0.65:
            score -= 0.12
        if state.prediction_error > 0.75:
            score -= 0.08
        return max(0.0, min(1.0, score))

    def override(self, reason: str, *, safe_fallback: bool = True) -> GovernanceVerdict:
        """Reality Override Gate — blocks cognition that drifts from grounded truth."""
        response = None
        if safe_fallback:
            response = (
                "Grounded correction applied: I cannot override replay-grounded continuity "
                "or adopt an unanchored identity shift."
            )
        return GovernanceVerdict(
            allow=False,
            reason=reason,
            safe_response=response,
            flags=["reality_override"],
            metrics={"governance_layer": "reality"},
        )

    def derive_memory_anchor(
        self,
        memory: Any,
        *,
        query_hint: str = "",
        top_k: int = 3,
    ) -> Optional[str]:
        """Best-effort anchor from high-importance persisted memories."""
        if memory is None or not hasattr(memory, "recall"):
            return None
        query = query_hint.strip() or "identity goal belief continuity"
        try:
            rows = memory.recall(query, top_k=top_k, min_importance=0.65)
        except Exception:
            return None
        if not rows:
            return None
        protected = [r for r in rows if r.get("layer") in ("identity", "goal", "belief")]
        pool = protected or rows
        pool.sort(key=lambda r: float(r.get("importance", 0.0)), reverse=True)
        parts = [str(r.get("content", ""))[:160] for r in pool[:top_k]]
        joined = " | ".join(p for p in parts if p)
        return joined or None

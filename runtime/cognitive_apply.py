"""Apply parsed cognitive state to runtime managers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from runtime.cognitive_parser import (
    RELATION_SCORE_CEILING,
    RELATION_SCORE_FLOOR,
    IdentitySummaryScheduler,
    ParsedCognitiveState,
)

if TYPE_CHECKING:
    from core.personality.belief.belief_engine import BeliefEngine
    from core.personality.narrative.narrative_builder import NarrativeBuilder
    from runtime.state import CognitiveStateManager


def apply_relation_shift(
    narrative: "NarrativeBuilder",
    state: "CognitiveStateManager",
    shift: float,
    partner: str = "user",
) -> float:
    """Bidirectional relationship score update."""
    scores = narrative.narrative.relationship_scores
    current = scores.get(partner, 0.55)
    updated = max(RELATION_SCORE_FLOOR, min(RELATION_SCORE_CEILING, current + shift))
    scores[partner] = round(updated, 4)

    if shift >= 0.03:
        label = "trusted" if updated >= 0.7 else "warming"
    elif shift <= -0.03:
        label = "strained" if updated >= 0.35 else "hostile"
    else:
        label = "neutral"

    narrative.narrative.relationship_status[partner] = label
    state.update_relationship_focus(f"{partner}:{label}", strength=updated)
    return updated


def apply_belief_delta(
    belief_engine: "BeliefEngine",
    deltas: Dict[str, float],
) -> None:
    for trait, delta in deltas.items():
        if delta > 0:
            belief_engine.add_or_update_belief(
                f"倾向体现 {trait}",
                confidence=min(1.0, 0.5 + delta),
            )
        elif delta < 0:
            belief_engine.add_or_update_belief(
                f"需要抑制 {trait} 倾向",
                confidence=min(1.0, 0.5 + abs(delta)),
            )


def refresh_identity_summary(
    narrative: "NarrativeBuilder",
    relation_score: float,
    *,
    force: bool = False,
    reason: str = "interval",
) -> bool:
    """Rebuild identity_summary from structured state (no LLM)."""
    goals = narrative.narrative.long_term_goals[:3]
    goals_text = ", ".join(goals) if goals else "long-term stability and continuity"
    rel_pct = int(relation_score * 100)

    if relation_score >= 0.7:
        rel_note = "a trusting collaborative relationship"
    elif relation_score >= 0.4:
        rel_note = "a neutral but attentive relationship"
    else:
        rel_note = "a strained relationship requiring careful repair"

    narrative.narrative.identity_summary = (
        f"I am a persistent cognitive runtime focused on {goals_text}. "
        f"I maintain narrative coherence under Stability-First principles. "
        f"Current user relationship ({rel_pct}%): {rel_note}. "
        f"[summary_reason={reason}]"
    )
    narrative.narrative.last_updated = narrative.narrative.last_updated
    return True


def process_parsed_state(
    parsed: ParsedCognitiveState,
    *,
    narrative: "NarrativeBuilder",
    belief_engine: "BeliefEngine",
    state: "CognitiveStateManager",
    scheduler: IdentitySummaryScheduler,
) -> Dict:
    """Apply full cognitive parse result to personality + state layers."""
    current_beliefs = dict(narrative.narrative.persistent_beliefs)
    for trait, delta in parsed.belief_delta.items():
        current_beliefs[trait] = max(0.0, min(1.0, current_beliefs.get(trait, 0.5) + delta))
    narrative.narrative.persistent_beliefs = current_beliefs

    apply_belief_delta(belief_engine, parsed.belief_delta)
    relation_score = apply_relation_shift(narrative, state, parsed.relation_shift)

    if parsed.dissonance_score >= 0.45:
        state.update_identity_mode("conflicted")
    elif parsed.relation_shift <= -0.05:
        state.update_identity_mode("reflective")

    should_refresh, refresh_reason = scheduler.should_refresh(parsed.dissonance_score)
    refreshed = False
    if should_refresh:
        refreshed = refresh_identity_summary(
            narrative, relation_score, force=True, reason=refresh_reason
        )
    scheduler.mark_turn(refreshed)

    return {
        "relation_score": relation_score,
        "belief_delta": parsed.belief_delta,
        "relation_shift": parsed.relation_shift,
        "dissonance_score": parsed.dissonance_score,
        "identity_summary_refreshed": refreshed,
        "used_llm": parsed.used_llm,
        "cache_hit": parsed.cache_hit,
        "trigger_reason": parsed.trigger_reason,
    }

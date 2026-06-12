"""GoalManager — single mount point for capture / governance goal verification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.governance.values_governance import ValuesGovernance
    from core.personality.intent_engine import Goal, IntentEngine, IntentState
    from core.personality.narrative.narrative_builder import NarrativeBuilder

from core.personality.intent_engine import GoalStatus

CAPTURE_INTENT_LAYERS = frozenset({"goal", "identity", "episodic", "working"})


class GoalManager:
    """Thin facade over IntentEngine for capture hot path and governance observation."""

    def __init__(
        self,
        intent_engine: "IntentEngine",
        *,
        narrative_builder: Optional["NarrativeBuilder"] = None,
        values_governance: Optional["ValuesGovernance"] = None,
    ):
        self.intent = intent_engine
        self.narrative = narrative_builder
        self.values = values_governance

    def mount_on_capture(
        self,
        role: str,
        content: str,
        layer: str,
        importance: float,
        *,
        context: Optional[Dict[str, Any]] = None,
        update_intent: bool = True,
    ) -> Optional["IntentState"]:
        """Mount goal extraction on capture path — IntentEngine owns intent block JSON."""
        if not update_intent or layer not in CAPTURE_INTENT_LAYERS:
            return None

        state = self.intent.update_from_interaction(
            role,
            content,
            context=context,
            importance=importance,
        )
        if layer == "goal":
            self._sync_narrative_goal(state)
        return state

    def active_goals(self, top_k: int = 3) -> List["Goal"]:
        return self.intent.get_active_goals(top_k=top_k)

    def current_focus(self) -> Optional[str]:
        summary = self.intent.get_state_summary()
        return summary.get("current_focus")

    def motivation_boost(self) -> float:
        return self.intent.get_motivation_boost()

    def format_context_block(self) -> str:
        return self.intent.format_context_block()

    def observe_governance(
        self,
        values_governance: Optional["ValuesGovernance"] = None,
    ) -> Dict[str, Any]:
        """Read-only goal snapshot for governance cycle verification."""
        goals = self.active_goals(top_k=3)
        vg = values_governance or self.values
        alignment = None
        if vg is not None:
            record = self.intent.check_value_alignment(vg)
            if record is not None:
                alignment = record.model_dump(mode="json")

        top = goals[0] if goals else None
        return {
            "active_goal_count": len(goals),
            "current_focus": self.current_focus(),
            "top_goal": top.model_dump(mode="json") if top else None,
            "motivation_boost": self.motivation_boost(),
            "value_alignment": alignment,
            "goal_influence_weight": (
                round(top.priority * top.motivation * top.alignment_score, 4) if top else 0.0
            ),
        }

    def _sync_narrative_goal(self, state: "IntentState") -> None:
        if self.narrative is None:
            return
        active = [g for g in state.active_goals if g.status == GoalStatus.ACTIVE]
        if not active:
            return
        top = max(active, key=lambda g: g.priority * g.motivation * g.alignment_score)
        desc = top.description[:120].strip()
        if not desc:
            return
        goals = self.narrative.narrative.long_term_goals
        if desc not in goals:
            goals.append(desc)
        if len(goals) > 8:
            self.narrative.narrative.long_term_goals = goals[-8:]

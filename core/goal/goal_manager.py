"""GoalManager — synthesis-backed capture mount and governance hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from core.governance.values_governance import ValuesGovernance
    from core.personality.belief.belief_engine import BeliefEngine
    from core.personality.intent_engine import Goal, IntentEngine, IntentState
    from core.personality.narrative.narrative_builder import NarrativeBuilder
    from runtime.cognitive_state import PersistentCognitiveState

from core.goal.synthesis import GoalSynthesizer
from core.personality.intent_engine import GoalStatus

CAPTURE_INTENT_LAYERS = frozenset({"goal", "identity", "episodic", "working"})
CseMode = Literal["batch", "idle", "realtime"]


class GoalManager:
    """Facade: ingest → synthesize → project via GoalSynthesizer."""

    def __init__(
        self,
        intent_engine: "IntentEngine",
        *,
        narrative_builder: Optional["NarrativeBuilder"] = None,
        working_self: Optional["PersistentCognitiveState"] = None,
        belief_engine: Optional["BeliefEngine"] = None,
        values_governance: Optional["ValuesGovernance"] = None,
        cse_mode: CseMode = "realtime",
    ):
        self.intent = intent_engine
        self.synthesizer = GoalSynthesizer(
            intent_engine,
            narrative_builder=narrative_builder,
            working_self=working_self,
            belief_engine=belief_engine,
            values_governance=values_governance,
        )
        self._cse_mode: CseMode = cse_mode
        self._pending_batch = 0

    def set_cse_mode(self, mode: str) -> None:
        normalized = str(mode or "idle").lower()
        if normalized not in ("batch", "idle", "realtime"):
            normalized = "idle"
        self._cse_mode = normalized  # type: ignore[assignment]

    @property
    def cse_mode(self) -> str:
        return self._cse_mode

    def flush_synthesis(self) -> None:
        """Run pending synthesis + projection (batch / idle deferred paths)."""
        if self._pending_batch <= 0:
            return
        self.synthesizer.synthesize()
        self.synthesizer.project()
        self._pending_batch = 0

    def _maybe_synthesize_project(self) -> None:
        self._pending_batch += 1
        if self._cse_mode == "realtime":
            self.synthesizer.synthesize()
            self.synthesizer.project()
            self._pending_batch = 0

    def bind_runtime(
        self,
        *,
        working_self: Optional["PersistentCognitiveState"] = None,
        belief_engine: Optional["BeliefEngine"] = None,
        values_governance: Optional["ValuesGovernance"] = None,
        narrative_builder: Optional["NarrativeBuilder"] = None,
    ) -> None:
        if working_self is not None:
            self.synthesizer.working_self = working_self
        if belief_engine is not None:
            self.synthesizer.belief_engine = belief_engine
        if values_governance is not None:
            self.synthesizer.values = values_governance
        if narrative_builder is not None:
            self.synthesizer.narrative = narrative_builder

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
        if not update_intent or layer not in CAPTURE_INTENT_LAYERS:
            return None

        self.synthesizer.ingest_capture(
            role, content, layer, importance, context=context
        )
        self._maybe_synthesize_project()
        if self._cse_mode == "realtime":
            return self._intent_state_from_canonical()
        return None

    def ingest_reflection(
        self,
        *,
        inner_thought: str = "",
        query: str = "",
        goal_id: Optional[str] = None,
        alignment_score: float = 0.75,
    ) -> None:
        self.synthesizer.ingest_reflection(
            inner_thought=inner_thought,
            query=query,
            goal_id=goal_id,
            alignment_score=alignment_score,
        )
        self._maybe_synthesize_project()

    def reconcile_governance(
        self,
        values_governance: Optional["ValuesGovernance"] = None,
    ) -> Dict[str, Any]:
        if values_governance is not None:
            self.synthesizer.values = values_governance
        reconcile_report = self.synthesizer.reconcile()
        observe = self.observe_governance(values_governance)
        return {**observe, **reconcile_report}

    def active_goals(self, top_k: int = 3) -> List["Goal"]:
        return self.synthesizer.active_canonical_goals(top_k=top_k)

    def current_focus(self) -> Optional[str]:
        return self.synthesizer.state.current_focus_id

    def motivation_boost(self) -> float:
        return self.synthesizer.motivation_boost()

    def format_context_block(self) -> str:
        return self.intent.format_context_block()

    def observe_governance(
        self,
        values_governance: Optional["ValuesGovernance"] = None,
    ) -> Dict[str, Any]:
        goals = self.active_goals(top_k=3)
        vg = values_governance or self.synthesizer.values
        alignment = None
        if vg is not None:
            record = self.intent.check_value_alignment(vg, persist=False)
            if record is not None:
                alignment = record.model_dump(mode="json")

        top = goals[0] if goals else None
        synth = self.synthesizer.state
        return {
            "active_goal_count": len(goals),
            "current_focus": self.current_focus(),
            "top_goal": top.model_dump(mode="json") if top else None,
            "motivation_boost": self.motivation_boost(),
            "value_alignment": alignment,
            "goal_influence_weight": (
                round(top.priority * top.motivation * top.alignment_score, 4) if top else 0.0
            ),
            "synthesis_generation": synth.synthesis_generation,
            "conflicts": [c.model_dump(mode="json") for c in synth.conflicts],
            "belief_links": len(synth.belief_links),
            "cse_mode": self._cse_mode,
            "pending_batch": self._pending_batch,
        }

    def _intent_state_from_canonical(self) -> "IntentState":
        from core.personality.intent_engine import IntentState

        synth = self.synthesizer.state
        return IntentState(
            active_goals=[g for g in synth.canonical_goals if g.status == GoalStatus.ACTIVE],
            current_focus=synth.current_focus_id,
        )

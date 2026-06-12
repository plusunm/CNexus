"""Goal Synthesis Layer — canonical goals from multi-source signals."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from core.personality.belief.belief_meta import BeliefMeta, attach_meta_to_belief_payload
from core.personality.intent_engine import Goal, GoalStatus, IntentState

if TYPE_CHECKING:
    from core.governance.values_governance import ValuesGovernance
    from core.personality.belief.belief_engine import BeliefEngine
    from core.personality.intent_engine import IntentEngine
    from core.personality.narrative.narrative_builder import NarrativeBuilder
    from runtime.cognitive_state import PersistentCognitiveState

GoalSignalSource = Literal["capture", "reflection", "governance", "narrative", "working_self"]

CONFLICT_KEYWORD_PAIRS = (
    ("短期", "长期"),
    ("快速", "稳定"),
    ("效率", "连续性"),
    ("short-term", "long-term"),
)
STALE_HOURS = 72
LOW_ALIGNMENT_THRESHOLD = 0.35


class GoalSignal(BaseModel):
    source: GoalSignalSource
    role: str = "user"
    content: str
    layer: str = "episodic"
    importance: float = Field(0.6, ge=0.0, le=1.0)
    context: Optional[Dict[str, Any]] = None


class GoalConflict(BaseModel):
    left_id: str
    right_id: str
    reason: str


class SynthesizedGoalState(BaseModel):
    canonical_goals: List[Goal] = Field(default_factory=list)
    current_focus_id: Optional[str] = None
    conflicts: List[GoalConflict] = Field(default_factory=list)
    belief_links: List[BeliefMeta] = Field(default_factory=list)
    last_synthesis_at: datetime = Field(default_factory=datetime.now)
    synthesis_generation: int = 0


class GoalSynthesizer:
    """Merge goal signals → canonical state → project to intent / narrative / working_self / belief."""

    def __init__(
        self,
        intent_engine: "IntentEngine",
        *,
        narrative_builder: Optional["NarrativeBuilder"] = None,
        working_self: Optional["PersistentCognitiveState"] = None,
        belief_engine: Optional["BeliefEngine"] = None,
        values_governance: Optional["ValuesGovernance"] = None,
    ):
        self.intent = intent_engine
        self.narrative = narrative_builder
        self.working_self = working_self
        self.belief_engine = belief_engine
        self.values = values_governance
        self._pending: List[GoalSignal] = []
        self._generation = 0
        self._state: Optional[SynthesizedGoalState] = None

    @property
    def state(self) -> SynthesizedGoalState:
        if self._state is None:
            self._state = self._load_from_intent()
        return self._state

    def ingest(self, signal: GoalSignal) -> None:
        self._pending.append(signal)

    def ingest_capture(
        self,
        role: str,
        content: str,
        layer: str,
        importance: float,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.ingest(
            GoalSignal(
                source="capture",
                role=role,
                content=content,
                layer=layer,
                importance=importance,
                context=context,
            )
        )

    def ingest_reflection(
        self,
        *,
        inner_thought: str = "",
        query: str = "",
        goal_id: Optional[str] = None,
        alignment_score: float = 0.75,
    ) -> None:
        text = inner_thought or query
        if not text.strip():
            return
        ctx: Dict[str, Any] = {"reflection": True}
        if goal_id:
            ctx["explicit_goal"] = text[:150]
            ctx["goal_priority"] = alignment_score
        self.ingest(
            GoalSignal(
                source="reflection",
                role="system",
                content=text,
                layer="belief",
                importance=0.7,
                context=ctx,
            )
        )

    def synthesize(self, *, reconcile: bool = False) -> SynthesizedGoalState:
        base = self._load_intent_state()
        alignment = self.intent._estimate_alignment_score()

        for signal in self._pending:
            self.intent.apply_signal_to_state(
                base,
                signal.role,
                signal.content,
                context=signal.context,
                importance=signal.importance,
                alignment_score=alignment,
            )

        self._merge_narrative_sources(base)
        self._merge_working_self_hint(base)

        conflicts = self._detect_conflicts(base)
        if reconcile:
            self._reconcile(base, conflicts)

        active = [g for g in base.active_goals if g.status == GoalStatus.ACTIVE]
        if active:
            top = max(active, key=self._goal_score)
            base.current_focus = top.goal_id

        self._generation += 1
        belief_links = self._build_belief_links(base, reconcile=reconcile)

        self._state = SynthesizedGoalState(
            canonical_goals=list(base.active_goals),
            current_focus_id=base.current_focus,
            conflicts=conflicts,
            belief_links=belief_links,
            last_synthesis_at=datetime.now(),
            synthesis_generation=self._generation,
        )
        base.metadata["synthesis_generation"] = self._generation
        base.metadata["conflict_count"] = len(conflicts)
        self._pending.clear()
        return self._state

    def project(self) -> Dict[str, Any]:
        if self._state is None:
            self.synthesize()
        assert self._state is not None

        intent_state = IntentState(
            active_goals=list(self._state.canonical_goals),
            current_focus=self._state.current_focus_id,
            last_updated=datetime.now(),
            motivation_baseline=self._load_intent_state().motivation_baseline,
            metadata={
                "synthesis_generation": self._state.synthesis_generation,
                "conflicts": [c.model_dump(mode="json") for c in self._state.conflicts],
            },
        )
        self.intent.persist_state(intent_state, source="goal_synthesis")

        if self.narrative is not None:
            active = [
                g for g in self._state.canonical_goals if g.status == GoalStatus.ACTIVE
            ]
            active.sort(key=self._goal_score, reverse=True)
            self.narrative.narrative.long_term_goals = [
                g.description[:120].strip() for g in active[:8] if g.description.strip()
            ]

        if self.working_self is not None:
            focus_goal = self._focus_goal()
            if focus_goal is not None:
                self.working_self.goal_focus = self._goal_focus_token(focus_goal)

        belief_report = self._project_belief_meta(self._state.belief_links)

        return {
            "projected": True,
            "synthesis_generation": self._state.synthesis_generation,
            "current_focus": self._state.current_focus_id,
            "active_goal_count": len(
                [g for g in self._state.canonical_goals if g.status == GoalStatus.ACTIVE]
            ),
            "belief_meta": belief_report,
        }

    def reconcile(self) -> Dict[str, Any]:
        self.synthesize(reconcile=True)
        report = self.project()
        report["reconciled"] = True
        if self._state:
            report["conflicts"] = [c.model_dump(mode="json") for c in self._state.conflicts]
        return report

    def active_canonical_goals(self, top_k: int = 3) -> List[Goal]:
        goals = [g for g in self.state.canonical_goals if g.status == GoalStatus.ACTIVE]
        goals.sort(key=self._goal_score, reverse=True)
        return goals[:top_k]

    def motivation_boost(self) -> float:
        goals = self.active_canonical_goals(top_k=1)
        if not goals:
            return 0.0
        return round(goals[0].motivation * 0.4, 4)

    # ── internal ───────────────────────────────────────────────────────

    @staticmethod
    def _goal_score(goal: Goal) -> float:
        return goal.priority * goal.motivation * goal.alignment_score

    def _load_from_intent(self) -> SynthesizedGoalState:
        base = self._load_intent_state()
        gen = int(base.metadata.get("synthesis_generation", 0))
        conflicts_raw = base.metadata.get("conflicts") or []
        conflicts: List[GoalConflict] = []
        for item in conflicts_raw:
            if isinstance(item, dict):
                try:
                    conflicts.append(GoalConflict(**item))
                except (TypeError, ValueError):
                    pass
        return SynthesizedGoalState(
            canonical_goals=list(base.active_goals),
            current_focus_id=base.current_focus,
            conflicts=conflicts,
            synthesis_generation=gen,
        )

    def _load_intent_state(self) -> IntentState:
        block = self.intent.memory.get_active_block("intent", touch=False)
        if not block:
            return IntentState()
        return self.intent.load_state(block.content)

    def _merge_narrative_sources(self, base: IntentState) -> None:
        if self.narrative is None:
            return
        for desc in self.narrative.narrative.long_term_goals:
            text = (desc or "").strip()
            if not text:
                continue
            goal = Goal(
                goal_id=f"g_n_{uuid.uuid4().hex[:6]}",
                description=text[:150],
                priority=0.62,
                motivation=0.68,
                alignment_score=self.intent._estimate_alignment_score(),
            )
            self.intent.apply_signal_to_state(
                base, "system", text, context={"explicit_goal": text}, importance=0.5
            )

    def _merge_working_self_hint(self, base: IntentState) -> None:
        if self.working_self is None:
            return
        focus = (self.working_self.goal_focus or "").strip()
        if not focus or focus == "general":
            return
        hint = f"working_self focus: {focus}"
        self.intent.apply_signal_to_state(
            base,
            "system",
            hint,
            context={"explicit_goal": focus, "goal_priority": 0.55},
            importance=0.45,
        )

    def _detect_conflicts(self, base: IntentState) -> List[GoalConflict]:
        conflicts: List[GoalConflict] = []
        active = [g for g in base.active_goals if g.status == GoalStatus.ACTIVE]
        for i, left in enumerate(active):
            for right in active[i + 1 :]:
                reason = self._conflict_reason(left.description, right.description)
                if reason:
                    conflicts.append(
                        GoalConflict(left_id=left.goal_id, right_id=right.goal_id, reason=reason)
                    )
        return conflicts

    @staticmethod
    def _conflict_reason(left: str, right: str) -> Optional[str]:
        ll, rr = left.lower(), right.lower()
        for a, b in CONFLICT_KEYWORD_PAIRS:
            if (a in ll and b in rr) or (b in ll and a in rr):
                return f"keyword_conflict:{a}/{b}"
        return None

    def _reconcile(self, base: IntentState, conflicts: List[GoalConflict]) -> None:
        now = datetime.now()
        stale_cutoff = now - timedelta(hours=STALE_HOURS)

        for goal in base.active_goals:
            if goal.status != GoalStatus.ACTIVE:
                continue
            if goal.alignment_score < LOW_ALIGNMENT_THRESHOLD:
                goal.status = GoalStatus.PAUSED
            elif goal.created_at < stale_cutoff and goal.progress < 0.05:
                goal.status = GoalStatus.PAUSED

        for conflict in conflicts:
            left = next((g for g in base.active_goals if g.goal_id == conflict.left_id), None)
            right = next((g for g in base.active_goals if g.goal_id == conflict.right_id), None)
            if not left or not right:
                continue
            if left.status != GoalStatus.ACTIVE or right.status != GoalStatus.ACTIVE:
                continue
            loser = left if self._goal_score(left) < self._goal_score(right) else right
            loser.status = GoalStatus.PAUSED

    def _build_belief_links(
        self,
        base: IntentState,
        *,
        reconcile: bool = False,
    ) -> List[BeliefMeta]:
        links: List[BeliefMeta] = []
        top = self._top_active(base)
        if top is None:
            return links

        if self.values is not None and reconcile:
            record = self.intent.check_value_alignment(self.values)
            if record is not None:
                links.append(
                    BeliefMeta(
                        belief_id=f"goal:{top.goal_id}",
                        goal_id=top.goal_id,
                        alignment_score=float(record.alignment_score),
                        confidence_delta=0.05,
                        source="governance",
                    )
                )

        if self.belief_engine is not None:
            for belief_id, belief in self.belief_engine.graph.beliefs.items():
                content = (belief.content or "").lower()
                if any(token in content for token in top.description.lower().split() if len(token) >= 2):
                    links.append(
                        BeliefMeta(
                            belief_id=belief_id,
                            goal_id=top.goal_id,
                            alignment_score=top.alignment_score,
                            confidence_delta=0.02,
                            source="reflection",
                        )
                    )
        return links[-16:]

    def _project_belief_meta(self, links: List[BeliefMeta]) -> Dict[str, Any]:
        if not links or self.belief_engine is None:
            return {"attached": 0, "skipped": "no_engine_or_links"}

        payload = self.belief_engine.export_belief_store_payload()
        for link in links:
            payload = attach_meta_to_belief_payload(payload, link, block_label="belief_store")

        content = json.dumps(payload, ensure_ascii=False)
        manager = self.belief_engine._memory_manager
        if manager is None:
            return {"attached": 0, "skipped": "no_memory_manager"}

        existing = manager.get_active_block("belief_store", touch=False)
        if existing:
            manager.update_block(existing.block_id, content, source="goal_synthesis")
        else:
            manager.create_block("belief_store", content, source="goal_synthesis")

        return {"attached": len(links), "block": "belief_store"}

    def _focus_goal(self) -> Optional[Goal]:
        if self._state is None:
            return None
        if self._state.current_focus_id:
            for goal in self._state.canonical_goals:
                if goal.goal_id == self._state.current_focus_id:
                    return goal
        active = self.active_canonical_goals(top_k=1)
        return active[0] if active else None

    @staticmethod
    def _top_active(base: IntentState) -> Optional[Goal]:
        active = [g for g in base.active_goals if g.status == GoalStatus.ACTIVE]
        if not active:
            return None
        return max(active, key=GoalSynthesizer._goal_score)

    @staticmethod
    def _goal_focus_token(goal: Goal) -> str:
        text = goal.description.lower()
        if any(k in text for k in ("身份", "identity", "连续")):
            return "identity"
        if any(k in text for k in ("目标", "goal", "长期", "稳定")):
            return "goal"
        return "goal"

"""IntentEngine — goal tracking and motivation via intent MemoryBlock."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.governance.values_governance import ValueAlignmentRecord, ValuesGovernance

from pydantic import BaseModel, Field

from memory.block import BLOCK_SPECS, MemoryBlock
from memory.manager import MemoryManager

INTENT_LABEL = "intent"
MAX_ACTIVE_GOALS = 8
PROACTIVE_MOTIVATION_THRESHOLD = 0.75
PROACTIVE_PROGRESS_CAP = 0.85


class ProactiveTrigger(BaseModel):
    should_trigger: bool = False
    reason: str = ""
    suggested_action: str = ""
    priority: float = Field(0.0, ge=0.0, le=1.0)
    goal_id: Optional[str] = None


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class Goal(BaseModel):
    goal_id: str
    description: str
    priority: float = Field(0.5, ge=0.0, le=1.0)
    status: GoalStatus = GoalStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    progress: float = Field(0.0, ge=0.0, le=1.0)
    motivation: float = Field(0.5, ge=0.0, le=1.0)
    alignment_score: float = Field(0.8, ge=0.0, le=1.0)
    parent_goal_id: Optional[str] = None
    sub_goals: List[str] = Field(default_factory=list)


class IntentState(BaseModel):
    """Structured payload stored in the intent MemoryBlock.content (JSON)."""

    active_goals: List[Goal] = Field(default_factory=list)
    current_focus: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    motivation_baseline: float = Field(0.6, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentEngine:
    """Goal decomposition + motivation tracking backed by L1 intent MemoryBlock."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    # ── serialization ──────────────────────────────────────────────────

    @staticmethod
    def _dump_state(state: IntentState) -> str:
        return json.dumps(state.model_dump(mode="json"), ensure_ascii=False)

    @staticmethod
    def _load_state(content: str) -> IntentState:
        if not content or not str(content).strip():
            return IntentState()
        text = str(content).strip()
        if not text.startswith("{"):
            goal = Goal(
                goal_id=f"g_{uuid.uuid4().hex[:8]}",
                description=text[:150],
                priority=0.6,
                motivation=0.6,
            )
            return IntentState(active_goals=[goal], current_focus=goal.goal_id)
        try:
            data = json.loads(text)
            return IntentState(**data)
        except (json.JSONDecodeError, TypeError, ValueError):
            return IntentState()

    def _get_or_create_block(self) -> MemoryBlock:
        block = self.memory.get_active_block(INTENT_LABEL, touch=False)
        if block:
            return block
        initial = IntentState()
        created = self.memory.create_block(
            INTENT_LABEL,
            self._dump_state(initial),
            importance=0.9,
            source="intent_engine",
        )
        if isinstance(created, dict):
            raise RuntimeError(f"failed to create intent block: {created}")
        self.memory.protect_block(INTENT_LABEL)
        return created

    def _compact_state(self, state: IntentState, *, limit: int = 1150) -> IntentState:
        """Keep intent JSON under block limit (1200) to avoid truncated invalid JSON."""
        working = state.model_copy(deep=True)
        for _ in range(8):
            if len(self._dump_state(working)) <= limit:
                return working
            active = [g for g in working.active_goals if g.status == GoalStatus.ACTIVE]
            active.sort(key=lambda g: g.priority * g.motivation, reverse=True)
            if len(active) > 1:
                keep = {g.goal_id for g in active[: max(1, len(active) - 1)]}
                working.active_goals = [
                    g for g in working.active_goals if g.goal_id in keep or g.status != GoalStatus.ACTIVE
                ]
            for goal in working.active_goals:
                if goal.status == GoalStatus.ACTIVE and len(goal.description) > 48:
                    goal.description = goal.description[:48]
        return working

    def _persist_state(
        self,
        state: IntentState,
        *,
        importance: float = 0.7,
        source: str = "intent_engine",
    ) -> IntentState:
        state = self._compact_state(state)
        block = self._get_or_create_block()
        payload = self._dump_state(state)
        gov = self.memory.governance.check(INTENT_LABEL, payload, importance)
        if not gov.allowed:
            return self._load_state(block.content)

        state.metadata["governance_status"] = gov.status
        if gov.consistency_flags:
            state.metadata["consistency_flags"] = gov.consistency_flags

        result = self.memory.update_block(
            block.block_id,
            self._dump_state(state),
            source=source,
        )
        if isinstance(result, dict) and result.get("denied"):
            return self._load_state(block.content)
        return state

    def load_state(self, content: str) -> IntentState:
        return self._load_state(content)

    def persist_state(
        self,
        state: IntentState,
        *,
        importance: float = 0.7,
        source: str = "intent_engine",
    ) -> IntentState:
        return self._persist_state(state, importance=importance, source=source)

    def apply_signal_to_state(
        self,
        state: IntentState,
        role: str,
        content: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.6,
        alignment_score: Optional[float] = None,
    ) -> IntentState:
        """Apply one signal onto in-memory IntentState without persisting."""
        score = alignment_score if alignment_score is not None else self._estimate_alignment_score()
        if context and context.get("goal_motivation") is not None:
            motivation_floor = float(context["goal_motivation"])
        else:
            motivation_floor = None
        if context and context.get("goal_priority") is not None:
            priority_floor = float(context["goal_priority"])
        else:
            priority_floor = None

        for goal in self._extract_goals(role, content, context, score):
            if motivation_floor is not None:
                goal.motivation = max(goal.motivation, motivation_floor)
            if priority_floor is not None:
                goal.priority = max(goal.priority, priority_floor)
            self._add_or_update_goal(state, goal, importance)

        state.last_updated = datetime.now()
        return state

    # ── core update ────────────────────────────────────────────────────

    def update_from_interaction(
        self,
        role: str,
        content: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.6,
    ) -> IntentState:
        """Extract/update goals and motivation from an interaction turn."""
        block = self._get_or_create_block()
        state = self._load_state(block.content)

        persona_alignment = self._estimate_alignment_score()
        state = self.apply_signal_to_state(
            state,
            role,
            content,
            context=context,
            importance=importance,
            alignment_score=persona_alignment,
        )

        active = [g for g in state.active_goals if g.status == GoalStatus.ACTIVE]
        if active:
            top = max(active, key=lambda g: g.priority * g.motivation * g.alignment_score)
            state.current_focus = top.goal_id
            state.motivation_baseline = min(1.0, state.motivation_baseline + 0.05 * importance)

        return self._persist_state(state, importance=importance)

    def _estimate_alignment_score(self) -> float:
        persona = self.memory.get_active_block("persona", touch=False)
        if not persona:
            return 0.75
        text = (persona.content or "").lower()
        if any(k in text for k in ("稳定", "理性", "工程", "连续", "stable", "engineering")):
            return 0.9
        return 0.8

    def _extract_goals(
        self,
        role: str,
        content: str,
        context: Optional[Dict[str, Any]],
        alignment_score: float,
    ) -> List[Goal]:
        text = (content or "").lower()
        goals: List[Goal] = []

        goal_keywords = [
            "我想", "我希望", "我要", "目标", "计划", "长期",
            "goal", "target", "plan", "intend", "hope to",
        ]
        if any(kw in text for kw in goal_keywords):
            goals.append(
                Goal(
                    goal_id=f"g_{uuid.uuid4().hex[:8]}",
                    description=(content or "")[:150],
                    priority=0.7,
                    motivation=0.75,
                    alignment_score=alignment_score,
                )
            )

        if context and context.get("explicit_goal"):
            goals.append(
                Goal(
                    goal_id=f"g_{uuid.uuid4().hex[:8]}",
                    description=str(context["explicit_goal"])[:150],
                    priority=float(context.get("goal_priority", 0.8)),
                    motivation=float(context.get("goal_motivation", 0.8)),
                    alignment_score=alignment_score,
                )
            )

        if role == "assistant" and any(kw in text for kw in ["下一步", "建议", "next step"]):
            goals.append(
                Goal(
                    goal_id=f"g_{uuid.uuid4().hex[:8]}",
                    description=(content or "")[:120],
                    priority=0.55,
                    motivation=0.6,
                    alignment_score=alignment_score,
                )
            )

        return goals

    def _add_or_update_goal(self, state: IntentState, new_goal: Goal, importance: float) -> None:
        key = new_goal.description[:50].strip().lower()
        existing = next(
            (
                g
                for g in state.active_goals
                if g.description[:50].strip().lower() == key and g.status == GoalStatus.ACTIVE
            ),
            None,
        )
        if existing:
            existing.priority = max(existing.priority, new_goal.priority)
            existing.motivation = max(existing.motivation, new_goal.motivation)
            existing.alignment_score = max(existing.alignment_score, new_goal.alignment_score)
            existing.progress = min(1.0, existing.progress + 0.05 * importance)
        else:
            state.active_goals.append(new_goal)

        active = [g for g in state.active_goals if g.status == GoalStatus.ACTIVE]
        if len(active) > MAX_ACTIVE_GOALS:
            active.sort(key=lambda g: g.priority * g.motivation, reverse=True)
            keep_ids = {g.goal_id for g in active[:MAX_ACTIVE_GOALS]}
            for g in state.active_goals:
                if g.status == GoalStatus.ACTIVE and g.goal_id not in keep_ids:
                    g.status = GoalStatus.PAUSED

    # ── public API ─────────────────────────────────────────────────────

    def get_active_goals(self, top_k: int = 3) -> List[Goal]:
        block = self.memory.get_active_block(INTENT_LABEL, touch=True)
        if not block:
            return []
        state = self._load_state(block.content)
        active = [g for g in state.active_goals if g.status == GoalStatus.ACTIVE]
        return sorted(
            active,
            key=lambda g: g.priority * g.motivation * g.alignment_score,
            reverse=True,
        )[:top_k]

    def get_motivation_boost(self) -> float:
        """Modulation signal for DynamicAttentionField / PredictiveSelf."""
        goals = self.get_active_goals(top_k=1)
        if not goals:
            return 0.0
        return round(goals[0].motivation * 0.4, 4)

    def trigger_proactive(
        self,
        min_motivation: float = 0.72,
        *,
        max_progress: float = PROACTIVE_PROGRESS_CAP,
    ) -> ProactiveTrigger:
        """Decide whether to proactively advance the top active goal."""
        goals = self.get_active_goals(top_k=3)
        if not goals:
            return ProactiveTrigger(should_trigger=False)

        top_goal = goals[0]
        priority = round(top_goal.motivation * top_goal.alignment_score, 4)

        if priority >= min_motivation and top_goal.progress < max_progress:
            return ProactiveTrigger(
                should_trigger=True,
                reason=f"高动机目标推进：{top_goal.description[:60]}",
                suggested_action=self._generate_proactive_suggestion(top_goal),
                priority=priority,
                goal_id=top_goal.goal_id,
            )
        return ProactiveTrigger(should_trigger=False)

    def trigger_proactive_message(
        self,
        min_motivation: float = PROACTIVE_MOTIVATION_THRESHOLD,
    ) -> Optional[str]:
        """Backward-compatible string API."""
        trigger = self.trigger_proactive(min_motivation=min_motivation)
        if trigger.should_trigger:
            return trigger.suggested_action or trigger.reason
        return None

    @staticmethod
    def _generate_proactive_suggestion(goal: Goal) -> str:
        return f"要不要我帮你推进「{goal.description[:50]}」这个目标？"

    def update_goal_progress(self, goal_id: str, progress_delta: float) -> Optional[IntentState]:
        block = self.memory.get_active_block(INTENT_LABEL, touch=False)
        if not block:
            return None
        state = self._load_state(block.content)
        for goal in state.active_goals:
            if goal.goal_id == goal_id:
                goal.progress = min(1.0, max(0.0, goal.progress + progress_delta))
                if goal.progress >= 1.0:
                    goal.status = GoalStatus.COMPLETED
                break
        state.last_updated = datetime.now()
        return self._persist_state(state)

    def get_state_summary(self) -> Dict[str, Any]:
        block = self.memory.get_active_block(INTENT_LABEL, touch=False)
        if not block:
            return {"active_goals": [], "current_focus": None, "motivation_baseline": 0.6}
        return self._load_state(block.content).model_dump(mode="json")

    def format_context_block(self) -> str:
        goals = self.get_active_goals(top_k=3)
        if not goals:
            return "【Intent Context】\n• no active goals"
        lines = ["【Intent Context】"]
        for g in goals:
            lines.append(
                f"• [{g.goal_id}] {g.description[:80]} "
                f"(p={g.priority:.2f} m={g.motivation:.2f} "
                f"align={g.alignment_score:.2f} prog={g.progress:.0%})"
            )
        return "\n".join(lines)

    def check_value_alignment(
        self,
        values_governance: "ValuesGovernance",
        *,
        persona_values: Optional[List[str]] = None,
        importance: float = 0.75,
    ) -> Optional["ValueAlignmentRecord"]:
        """Run ValuesGovernance on the top active goal and sync alignment_score."""
        goals = self.get_active_goals(1)
        if not goals:
            return None
        top_goal = goals[0]
        record = values_governance.check_intent_alignment(
            intent_description=top_goal.description,
            persona_values=persona_values,
            importance=importance,
            metadata={"goal_id": top_goal.goal_id},
        )
        self._sync_goal_alignment(top_goal.goal_id, record.alignment_score)
        return record

    def _sync_goal_alignment(self, goal_id: str, alignment_score: float) -> None:
        block = self.memory.get_active_block(INTENT_LABEL, touch=False)
        if not block:
            return
        state = self._load_state(block.content)
        for goal in state.active_goals:
            if goal.goal_id == goal_id:
                goal.alignment_score = alignment_score
                break
        state.last_updated = datetime.now()
        self._persist_state(state)

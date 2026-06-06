import logging
import uuid
from datetime import datetime, timedelta
from typing import Callable, List, Optional, TYPE_CHECKING

from core.personality.reflective.action_generator import ActionGenerator
from core.personality.reflective.cultivation_engine import CultivationEngine
from core.personality.reflective.reflective_memory import ReflectionRecord
from core.personality.reflective.reflective_store import ReflectiveMemoryStore
from core.personality.reflective.review_scheduler import ReviewScheduler
from core.personality.reflective.trait_detector import TraitDetector

if TYPE_CHECKING:
    from core.personality.belief.belief_engine import BeliefEngine
    from core.personality.narrative.narrative_builder import NarrativeBuilder

logger = logging.getLogger(__name__)

MemoryPersister = Callable[..., str]


class ReflectionPipeline:
    """反思连续性管道 — 连接 Personality 与 Governance（Subject Continuity 闭环）"""

    def __init__(
        self,
        reflective_store: ReflectiveMemoryStore,
        memory_persister: Optional[MemoryPersister] = None,
        narrative: Optional["NarrativeBuilder"] = None,
        belief: Optional["BeliefEngine"] = None,
    ):
        self.store = reflective_store
        self.memory_persister = memory_persister
        self.narrative = narrative
        self.belief = belief
        self.trait_detector = TraitDetector()
        self.cultivation_engine = CultivationEngine()
        self.action_generator = ActionGenerator()
        self.scheduler = ReviewScheduler()

    @property
    def records(self) -> List[ReflectionRecord]:
        return self.store.records

    def process_reflection(
        self, content: str, source_traits: Optional[List[str]] = None
    ) -> ReflectionRecord:
        logger.info("Reflective Continuity Pipeline started")

        traits = source_traits or self.trait_detector.detect(content)
        primary_trait = traits[0] if traits else "自我觉察不足"

        scene = self.cultivation_engine.get_scene(primary_trait) or "未找到典型场景"
        inner_thought = f"回想类似经历，我在「{primary_trait}」上存在可改进空间。触发内容：{content[:120]}"

        methods = self.cultivation_engine.match_methods(traits)
        actions = self.action_generator.generate(methods)

        record = ReflectionRecord(
            reflection_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            traits=traits,
            scene=scene,
            inner_thought=inner_thought,
            suggested_methods=methods,
            action_steps=actions[:3],
            next_review_date=datetime.now() + timedelta(days=7),
            coherence_score=0.88,
        )

        if self.memory_persister:
            summary = self._generate_summary(record)
            self.memory_persister(
                "system", summary, layer="semantic", importance=0.82, emotional_weight=0.6
            )
            self.memory_persister(
                "system",
                f"[心性图式] {', '.join(traits)} → {', '.join(methods)}",
                layer="semantic",
                importance=0.78,
            )

        self._apply_continuity_loop(content, traits, inner_thought, record.reflection_id)

        self.store.append(record)
        self.scheduler.schedule_review(record)

        logger.info("Reflection completed and persisted")
        return record

    def _apply_continuity_loop(
        self, content: str, traits: List[str], inner_thought: str, reflection_id: str
    ) -> None:
        """Subject Continuity 闭环 — 同步 Narrative + Belief"""
        if self.narrative:
            self.narrative.update_from_memory(content, importance=0.85)
            self.narrative.update_from_memory(
                f"Reflection on {', '.join(traits)}: {inner_thought[:100]}",
                importance=0.85,
            )

        if self.belief:
            for trait in traits:
                self.belief.add_or_update_belief(
                    f"我在 {trait} 上需要改进",
                    confidence=0.75,
                    source_memory_id=reflection_id,
                )

    def get_active_reflections(self) -> List[ReflectionRecord]:
        return self.store.get_active()

    def run_due_reviews(self) -> List[ReflectionRecord]:
        return self.scheduler.due_reviews()

    def _generate_summary(self, record: ReflectionRecord) -> str:
        first_action = record.action_steps[0] if record.action_steps else "每日自省"
        return (
            f"【心性反思】发现 {', '.join(record.traits)} 等问题。"
            f"场景：{record.scene}。"
            f"决定采用 {', '.join(record.suggested_methods)} 修养，"
            f"首要行动：{first_action}。"
        )

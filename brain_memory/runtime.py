import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.config_loader import ConfigLoader
from core.embedding import EmbeddingService
from core.paths import get_project_root, resolve_memory_dir
from core.governance.coordinator import StabilityCoordinator
from core.governance.safety.policy_engine import GovernancePolicyEngine
from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder
from core.personality.reflective.reflection_pipeline import ReflectionPipeline
from core.personality.reflective.reflective_memory import ReflectionRecord
from core.personality.reflective.reflective_store import ReflectiveMemoryStore
from core.self_model import SelfModelStore
from core.validation.validation_orchestrator import StabilityValidationOrchestrator
from memory.filter import CaptureFilter
from memory.schema import Memory
from runtime.attention import DynamicAttentionField
from runtime.cognitive_apply import process_parsed_state
from runtime.cognitive_parser import CognitiveStateParser, IdentitySummaryScheduler
from runtime.cognitive_recall import CognitiveRecallEngine
from runtime.cognitive_state import PersistentCognitiveState
from runtime.context import ContextAssemblyEngine
from runtime.predictive_loop import PredictiveSelf
from core.governance.deliberation import DeliberativeGovernance
from runtime.router import HierarchicalRecallRouter
from runtime.state import CognitiveStateManager
from storage.manager import UnifiedStorageManager

logger = logging.getLogger(__name__)


class BrainMemoryRuntime:
    """Brain-Memory G1 — 全局统一 Facade 入口"""

    def __init__(
        self,
        config_path: str = "config/default.json",
        base_dir: str = "memory",
        project_root: Optional[str] = None,
    ):
        self.project_root = get_project_root(project_root)
        config_dir = self.project_root / "config" if not Path(config_path).is_absolute() else Path(config_path).parent
        self.config_loader = ConfigLoader.get_instance(str(config_dir))
        cfg = self.config_loader.config

        self.base_dir = resolve_memory_dir(self.project_root, base_dir)
        self.embedder = EmbeddingService(
            host=cfg.get("ollama_host", "http://localhost:11434"),
            model=cfg.get("embedding_model", "nomic-embed-text"),
            vector_dim=cfg.get("vector_dim", 768),
            fallback=cfg.get("embedding_fallback", "hash"),
        )

        # Layer 1 — Storage
        self.storage = UnifiedStorageManager(
            base_dir=self.base_dir,
            vector_dim=cfg.get("vector_dim", 768),
        )
        self.storage.set_embedder(self.embedder)

        # Layer 2 — Cognitive Runtime (G2)
        self.attention = DynamicAttentionField()
        self.state = CognitiveStateManager()
        self.working_self = PersistentCognitiveState()
        self.self_model_store = SelfModelStore(self.base_dir)
        self.predictive = PredictiveSelf()
        self.cognitive_parser = CognitiveStateParser(llm_hook=None)
        self.identity_scheduler = IdentitySummaryScheduler(interval_turns=5, dissonance_threshold=0.65)
        self.router = HierarchicalRecallRouter(self.storage)
        self.recall_engine = CognitiveRecallEngine(self.storage, self.router)
        self.deliberation = DeliberativeGovernance()
        self.context_engine = ContextAssemblyEngine(self.attention)

        # Layer 3 — Personality Continuity
        self.dna_engine = PersonalityDNAEngine()
        self.narrative = NarrativeBuilder(self.dna_engine)
        self.belief_engine = BeliefEngine(self.dna_engine, self.narrative)

        # Layer 3.5 — Reflective Continuity
        self.reflective_store = ReflectiveMemoryStore(self.base_dir)
        self.reflection_pipeline = ReflectionPipeline(
            reflective_store=self.reflective_store,
            memory_persister=self._persist_reflection_memory,
            narrative=self.narrative,
            belief=self.belief_engine,
        )

        # Layer 4 — Stability Governance
        self.stability = StabilityCoordinator(
            self.dna_engine,
            self.narrative,
            self.belief_engine,
            reflection=self.reflection_pipeline,
            state_manager=self.state,
        )
        self.policy = GovernancePolicyEngine()

        # Validation
        self.validation = StabilityValidationOrchestrator(self)

        self.recall_top_k = cfg.get("recall_top_k", 12)
        self.runtime_mode = cfg.get("runtime_mode", "g2")
        logger.info(
            "Brain-Memory G1 v%s initialized — %s Cognitive Runtime",
            "1.0.0-g1",
            self.runtime_mode.upper(),
        )

    # ==================== Facade aliases (统一 API) ====================
    @property
    def config(self) -> Dict[str, Any]:
        return self.config_loader.config

    @property
    def context(self):
        return self.context_engine

    @property
    def write_gate(self):
        return self.policy.write_gate

    # Facade aliases
    @property
    def dna(self):
        return self.dna_engine

    @property
    def belief(self):
        return self.belief_engine

    @property
    def reflection(self):
        return self.reflection_pipeline

    @property
    def governance(self):
        return self.stability

    def _persist_reflection_memory(self, role: str, content: str, **kwargs) -> str:
        return self.storage.capture_memory(
            role=role,
            content=content,
            embedding=self.embedder.embed(content),
            **kwargs,
        )

    def capture(
        self,
        role: str,
        content: str,
        layer: str = "episodic",
        importance: float = 0.5,
        emotional_weight: float = 0.5,
        **meta,
    ) -> Union[str, Dict[str, Any]]:
        rejected, reason = CaptureFilter.should_reject(role, content)
        if rejected:
            return f"denied: {reason}"

        memory = Memory(
            memory_id=str(uuid.uuid4()),
            role=role,
            content=content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            timestamp=datetime.now(),
            last_accessed_at=datetime.now(),
            embedding=self.embedder.embed(content),
            metadata=meta,
        )

        allowed, gate_reason, risk = self.policy.write_gate.validate(memory)
        if not allowed:
            return f"denied: {gate_reason} (risk={risk:.2f})"

        mid = self.storage.capture_memory(
            role=role,
            content=content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            embedding=memory.embedding,
            **meta,
        )

        if layer in ("goal", "identity", "belief"):
            self.narrative.update_from_memory(content, importance=importance)
        if importance > 0.75:
            self.belief_engine.add_or_update_belief(content, confidence=importance, source_memory_id=mid)

        if role == "user":
            self._apply_cognitive_state(content, layer=layer, importance=importance)

        return mid

    def _apply_cognitive_state(self, user_input: str, *, layer: str, importance: float) -> Dict[str, Any]:
        """Rule-first cognitive parse; LLM only when parser opts in (hook not set by default)."""
        current_beliefs = dict(self.narrative.narrative.persistent_beliefs)
        parsed = self.cognitive_parser.parse_cognitive_state(
            user_input,
            layer=layer,
            importance=importance,
            current_beliefs=current_beliefs,
        )
        self.working_self.update_from_input(
            user_input, self.dna_engine.dna, parsed=parsed, layer=layer, importance=importance
        )
        applied = process_parsed_state(
            parsed,
            narrative=self.narrative,
            belief_engine=self.belief_engine,
            state=self.state,
            scheduler=self.identity_scheduler,
        )
        self.working_self.sync_to_legacy(self.state)
        return applied

    def parse_cognitive_state(
        self,
        user_input: str,
        *,
        layer: str = "episodic",
        importance: float = 0.5,
        apply: bool = True,
    ) -> Dict[str, Any]:
        """Public API — inspect or apply cognitive state deltas from user input."""
        parsed = self.cognitive_parser.parse_cognitive_state(
            user_input,
            layer=layer,
            importance=importance,
            current_beliefs=dict(self.narrative.narrative.persistent_beliefs),
        )
        result = parsed.__dict__
        if apply:
            result["applied"] = process_parsed_state(
                parsed,
                narrative=self.narrative,
                belief_engine=self.belief_engine,
                state=self.state,
                scheduler=self.identity_scheduler,
            )
        return result

    def recall(self, query: str, top_k: Optional[int] = None) -> str:
        top_k = top_k or self.recall_top_k

        if self.runtime_mode == "g2":
            recall_results = self.recall_engine.activate(
                query, self.working_self, self.dna_engine.dna, top_k=top_k
            )
        else:
            recall_results = self.router.hybrid_recall(query, top_k=top_k)

        activated = self.attention.attention_competition(recall_results, query)
        self.state.sync_from_attention(activated)
        self.working_self.sync_to_legacy(self.state)

        context = self.context_engine.assemble(query, recall_results)
        identity_anchor = self.narrative.generate_identity_anchor()
        self_block = self.self_model.to_prompt_block()
        state_block = (
            f"【Working Self】\n"
            f"• goal_focus={self.working_self.goal_focus} "
            f"coherence={self.working_self.cumulative_coherence:.2f} "
            f"prediction_error={self.working_self.prediction_error:.2f}"
        )
        identity_block = (
            f"【Identity Context】\n"
            f"• {self.narrative.get_current_narrative_summary()}"
        )
        return f"{identity_anchor}\n\n{self_block}\n\n{state_block}\n\n{identity_block}\n\n{context}"

    @property
    def self_model(self):
        return self.self_model_store.model

    def _sync_narrative_from_self_model(self) -> None:
        """Narrative is material; SelfModel is the interpreter."""
        n = self.narrative.narrative
        n.identity_summary = self.self_model.identity_summary[:500]
        n.persistent_beliefs = dict(self.self_model.core_beliefs)
        n.narrative_coherence_score = self.self_model.coherence_score
        user_rel = self.self_model.relational_models.get("user", {})
        if user_rel:
            n.relationship_scores["user"] = float(user_rel.get("trust", 0.7))
            n.relationship_status["user"] = str(user_rel.get("tone", "neutral"))

    def _sync_beliefs_from_self_model(self) -> None:
        for content, confidence in self.self_model.core_beliefs.items():
            self.belief_engine.add_or_update_belief(
                f"核心信念：{content}", confidence=confidence
            )

    def _generate_constrained_response(self, user_input: str, context: str) -> str:
        """Self-Model constrained draft (LLM layer injects self_model.to_prompt_block())."""
        return (
            f"[Stable Response] 基于我的长期身份：{self.self_model.identity_summary[:80]}，"
            f"结合当前认知上下文，回应：{user_input[:120]}"
        )

    def process_interaction(
        self,
        user_input: str,
        *,
        assistant_output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Subject Runtime Loop — experience → interpretation → self-update → prediction.
        """
        self.working_self.update_from_input(user_input, self.dna_engine.dna, importance=0.65)

        capture_id = self.capture("user", user_input, importance=0.65)
        if isinstance(capture_id, str) and capture_id.startswith("denied"):
            return {"ok": False, "reason": capture_id}

        context = self.recall(user_input)
        response = assistant_output or self._generate_constrained_response(user_input, context)

        allowed, gate_reason = self.deliberation.deliberate(
            response, self.working_self, self.dna_engine.dna
        )
        if not allowed:
            return {
                "ok": False,
                "reason": gate_reason,
                "context": context,
                "response": response,
                "working_self": self.working_self.to_dict(),
                "self_model": self.self_model.to_dict(),
            }

        error = self.predictive.predict_and_update(
            user_input, response, self.working_self, self.self_model
        )
        reflection = f"本次交互预测误差 {error:.2f}，"
        reflection += "触发自我校正。" if error > 0.4 else "维持稳定性身份。"

        integration = self.self_model_store.integrate(
            user_input,
            response,
            reflection=reflection,
            dna=self.dna_engine.dna,
            prediction_error=error,
            relation_shift=self.working_self.relationship_tone - 0.7,
        )

        self.narrative.update_from_interaction(
            user_input, response, reflection=reflection, importance=0.65
        )
        self._sync_narrative_from_self_model()
        self._sync_beliefs_from_self_model()

        self.capture("assistant", response, importance=0.55)

        self.working_self.update_prediction_error()
        self.working_self.add_reflection(reflection)
        self.deliberation.regulate_homeostasis(self.working_self)
        self.working_self.sync_to_legacy(self.state)

        gov = self.run_governance_cycle()

        return {
            "ok": True,
            "response": response,
            "capture_id": capture_id,
            "context": context,
            "working_self": self.working_self.to_dict(),
            "self_model": self.self_model.to_dict(),
            "integration": integration,
            "predictive": self.predictive.to_dict(),
            "prediction_error": error,
            "reflection": reflection,
            "governance": gov.get("stability_metrics"),
        }

    def process(self, user_input: str, *, assistant_output: Optional[str] = None) -> Dict[str, Any]:
        """G2 Cognitive Loop alias — delegates to process_interaction."""
        return self.process_interaction(user_input, assistant_output=assistant_output)

    def trait_based_reflection(
        self,
        content: str,
        traits: Optional[List[str]] = None,
        *,
        trigger_governance: bool = True,
    ) -> ReflectionRecord:
        """反思管道 — Narrative + Belief + Memory 闭环；可选触发治理检查"""
        record = self.reflection_pipeline.process_reflection(content, traits)
        summary = (
            f"Reflection on {', '.join(record.traits)}: {record.inner_thought[:100]}"
        )
        self.self_model_store.integrate(
            content,
            summary,
            reflection=summary,
            dna=self.dna_engine.dna,
        )
        self._sync_narrative_from_self_model()
        self._sync_beliefs_from_self_model()
        if trigger_governance:
            self.run_governance_cycle()
        return record

    def run_governance_cycle(self) -> Dict[str, Any]:
        self.belief_engine.decay_confidence()
        return self.stability.run_governance_cycle()

    def run_validation_suite(self, days: int = 90) -> Dict[str, Any]:
        return self.validation.run_full_validation_suite(simulation_days=days)

    def run_background_governance(self):
        return self.run_governance_cycle()

    async def start_background_governance(self, interval_seconds: int = 3600):
        """后台治理循环"""
        while True:
            try:
                self.run_governance_cycle()
            except Exception as exc:
                logger.exception("Governance cycle failed: %s", exc)
            await asyncio.sleep(interval_seconds)

    async def start_background_loop(self, interval_seconds: int = 3600):
        """后台治理 + 反思循环（start_background_governance 别名）"""
        await self.start_background_governance(interval_seconds)

    def get_current_state(self) -> Dict[str, Any]:
        wm = self.attention.working_memory_snapshot()
        dna_metrics = self.dna_engine.get_stability_metrics()
        state_metrics = self.state.get_stability_metrics()
        return {
            "cognitive_state": self.state.get_full_state(),
            "working_self": self.working_self.to_dict(),
            "self_model": self.self_model.to_dict(),
            "predictive": self.predictive.to_dict(),
            "runtime_mode": self.runtime_mode,
            "stability_metrics": {
                **state_metrics,
                **dna_metrics,
                "narrative_coherence": self.narrative.narrative.narrative_coherence_score,
                "overall_stability_score": (
                    dna_metrics.get("overall_stability", 0.85) * 0.5
                    + state_metrics.get("identity_stability", 0.85) * 0.3
                    + self.narrative.narrative.narrative_coherence_score * 0.2
                ),
            },
            "personality_dna": self.dna_engine.dna.model_dump(mode="json"),
            "narrative": {
                "summary": self.narrative.get_current_narrative_summary(),
                "coherence": self.narrative.narrative.narrative_coherence_score,
                "version": self.narrative.narrative.version,
            },
            "beliefs": {
                k: {"content": v.content, "confidence": v.confidence}
                for k, v in self.belief_engine.get_active_beliefs().items()
            },
            "reflective": {
                "active_count": len(self.reflection_pipeline.get_active_reflections()),
                "pending_reviews": len(self.reflection_pipeline.run_due_reviews()),
                "latest": (
                    self.reflection_pipeline.records[-1].model_dump(mode="json")
                    if self.reflection_pipeline.records
                    else None
                ),
            },
            "working_memory_count": len(wm),
            "timestamp": datetime.now().isoformat(),
        }

    def get_full_status(self) -> Dict[str, Any]:
        """全层状态摘要 — 供 UI / Agent / 监控使用"""
        state = self.get_current_state()
        return {
            "version": "1.0.0-g1",
            "layers": {
                "storage": {"base_dir": self.base_dir},
                "runtime": {
                    "working_memory": state["working_memory_count"],
                    "cognitive_load": state["cognitive_state"].get("cognitive_load"),
                },
                "personality": {
                    "dna_stability": state["stability_metrics"].get("overall_stability"),
                    "narrative_coherence": state["narrative"]["coherence"],
                    "belief_count": len(state["beliefs"]),
                    "reflection_active": state["reflective"]["active_count"],
                },
                "governance": {
                    "overall_stability": state["stability_metrics"].get("overall_stability_score"),
                },
            },
            "detail": state,
        }


def create_runtime(
    config_path: str = "config/default.json",
    base_dir: str = "memory",
    project_root: Optional[str] = None,
) -> BrainMemoryRuntime:
    """推荐初始化入口"""
    return BrainMemoryRuntime(
        config_path=config_path,
        base_dir=base_dir,
        project_root=project_root,
    )

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.config_loader import ConfigLoader
from core.llm_client import LLMClient
from core.model_registry import ModelProfile
from core.embedding import EmbeddingService
from core.paths import get_project_root, resolve_memory_dir
from core.governance.cdg import CDGKernel, apply_cdg_state, snapshot_cdg_state
from core.governance.coordinator import StabilityCoordinator
from core.governance.values_governance import ValuesGovernance
from core.memory.sleep_time_compute import SleepTimeCompute
from core.governance.safety.policy_engine import GovernancePolicyDescriptor
from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.emotion_engine import EmotionEngine
from core.personality.intent_engine import (
    PROACTIVE_MOTIVATION_THRESHOLD,
    IntentEngine,
    ProactiveTrigger,
)
from core.personality.reflective.reflective_engine import ReflectiveEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder
from core.personality.reflective.reflection_pipeline import ReflectionPipeline
from core.personality.reflective.reflective_memory import ReflectionRecord
from core.personality.reflective.reflective_store import ReflectiveMemoryStore
from core.self_model import SelfModelStore
from core.validation.validation_orchestrator import StabilityValidationOrchestrator
from memory.filter import CaptureFilter
from memory.lifecycle import MemoryLifecycleManager, MemoryManagementConfig
from memory.manager import MemoryManager
from memory.schema import Memory
from runtime.attention import DynamicAttentionField
from runtime.cognitive_apply import process_parsed_state
from runtime.cognitive_parser import CognitiveStateParser, IdentitySummaryScheduler
from runtime.cognitive_recall import CognitiveRecallEngine
from runtime.cognitive_state import PersistentCognitiveState
from runtime.context import ContextAssemblyEngine
from runtime.predictive_loop import PredictiveSelf
from core.governance.deliberation import DeliberativeGovernance
from runtime.router import HierarchicalRecallEngine
from runtime.state import CognitiveStateManager
from storage.manager import UnifiedStorageManager

logger = logging.getLogger(__name__)


class BrainMemoryRuntime:
    """
    CNexus — multi-store cognitive continuity facade.

    North star: multi-store cognition + projection governance + emerging
    transaction boundary (see Constitutional_Semantics_v1.md).
    """

    def __init__(
        self,
        config_path: str = "config/default.json",
        base_dir: str = "memory",
        project_root: Optional[str] = None,
    ):
        self.project_root = get_project_root(project_root)
        config_dir = self.project_root / "config" if not Path(config_path).is_absolute() else Path(config_path).parent
        self.config_loader = ConfigLoader.get_instance(str(config_dir))
        cfg_file = Path(config_path)
        if not cfg_file.is_absolute():
            cfg_file = self.project_root / config_path
        if cfg_file.exists():
            with open(cfg_file, encoding="utf-8") as fh:
                self.config_loader.config = json.load(fh)
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
        self._memory_mgmt = MemoryManagementConfig.from_dict(cfg)
        self._lifecycle = MemoryLifecycleManager(self.storage, self._memory_mgmt)
        self.storage.configure_lifecycle(self._lifecycle)
        self.storage.set_recall_access_cap(self._memory_mgmt.recall_access_cap)

        # Layer 2 — Cognitive Runtime (G2)
        self.attention = DynamicAttentionField()
        self.state = CognitiveStateManager()
        self.working_self = PersistentCognitiveState()
        self.self_model_store = SelfModelStore(self.base_dir)
        self.predictive = PredictiveSelf()
        self.cognitive_parser = CognitiveStateParser(llm_hook=None)
        self.identity_scheduler = IdentitySummaryScheduler(interval_turns=5, dissonance_threshold=0.65)
        self.router = HierarchicalRecallEngine(self.storage)
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
        self.policy = GovernancePolicyDescriptor()

        # Layer 1 — Memory Manager (structured blocks + episodic storage)
        self.memory_manager = MemoryManager(
            self.base_dir,
            storage=self.storage,
            write_gate=self.policy.write_gate,
        )
        self.memory_manager.set_embedder(self.embedder)
        self.memory_manager.configure_lifecycle(self._lifecycle)
        self.router.set_memory_manager(self.memory_manager)

        # L3 — Emotion + Intent continuity (MemoryBlocks)
        self.emotion_engine = EmotionEngine(self.memory_manager)
        self.intent_engine = IntentEngine(self.memory_manager)
        self._llm_client = LLMClient()
        self.reflective_engine = ReflectiveEngine(
            self.memory_manager,
            self.emotion_engine,
            self.intent_engine,
            narrative=self.narrative,
            llm_client=self._llm_client,
            llm_profile_provider=self._get_reflective_llm_profile,
            llm_temperature=float(cfg.get("reflective_llm_temperature", 0.3)),
        )
        self.values_governance = ValuesGovernance(
            self.memory_manager,
            persona_values_provider=self._get_persona_core_values,
        )
        self.sleep_time_compute = SleepTimeCompute(
            self.memory_manager,
            reflective_engine=self.reflective_engine,
            compression_threshold_days=self._memory_mgmt.block_stale_days,
        )

        # L6 — CDG Hypervisor (sole governance control plane)
        cdg_cfg = {**(cfg.get("governance") or {}), **(cfg.get("cdg") or {})}
        if not cdg_cfg.get("audit_log_path"):
            cdg_cfg["audit_log_path"] = str(Path(self.base_dir) / "governance_audit.jsonl")
        self.cdg = CDGKernel(
            cdg_cfg,
            drift_detector=self.stability.detector,
            mutation_guard=self.dna_engine.guard,
        )

        # Validation
        self.validation = StabilityValidationOrchestrator(self)

        self.recall_top_k = cfg.get("recall_top_k", 12)
        self.runtime_mode = cfg.get("runtime_mode", "g2")
        self._gtbs_observer = None
        self._capture_boundary = None
        logger.info(
            "CNexus v%s initialized — %s Cognitive Runtime",
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

    @property
    def memory(self):
        """L1 MemoryManager — unified memory entry."""
        return self.memory_manager

    @property
    def emotion(self):
        return self.emotion_engine

    @property
    def intent(self):
        return self.intent_engine

    @property
    def reflective(self):
        return self.reflective_engine

    @property
    def values(self):
        return self.values_governance

    @property
    def sleep(self):
        return self.sleep_time_compute

    def _get_persona_core_values(self) -> List[str]:
        """Core values for ValuesGovernance — narrative first, then defaults."""
        narrative_values = list(self.narrative.narrative.core_values or [])
        if narrative_values:
            return narrative_values[:8]
        return list(self.values_governance.core_values)

    def _get_reflective_llm_profile(self) -> Optional[ModelProfile]:
        """Model profile for ReflectiveEngine LLM critic (config-driven)."""
        if not self.config.get("reflective_use_llm", True):
            return None
        cfg = self.config
        return ModelProfile(
            id="reflective-critic",
            name="Reflective Critic",
            provider="ollama",
            base_url=cfg.get("ollama_host", "http://localhost:11434"),
            api_key="",
            model=cfg.get("reflective_llm_model") or cfg.get("llm_model", "llama3.2"),
            is_default=True,
            enabled=True,
        )

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
        """CDG is the sole governance entry; stability coordinator is a subordinate probe."""
        return self.cdg

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

        if self._gtbs_capture_enabled():
            return self._capture_via_gtbs(
                role, content, layer, importance, emotional_weight, **meta
            )

        return self._capture_direct(
            role, content, layer, importance, emotional_weight, **meta
        )

    def _capture_direct(
        self,
        role: str,
        content: str,
        layer: str,
        importance: float,
        emotional_weight: float,
        **meta,
    ) -> Union[str, Dict[str, Any]]:
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

        return self._commit_capture(
            role,
            content,
            layer,
            importance,
            emotional_weight,
            memory.embedding,
            **meta,
        )

    def _capture_via_gtbs(
        self,
        role: str,
        content: str,
        layer: str,
        importance: float,
        emotional_weight: float,
        **meta,
    ) -> Union[str, Dict[str, Any]]:
        from core.governance.gtbs.capture_boundary import infer_capture_target_stores

        pre_snap = snapshot_cdg_state(self)
        embedding = self.embedder.embed(content)
        memory = Memory(
            memory_id=str(uuid.uuid4()),
            role=role,
            content=content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            timestamp=datetime.now(),
            last_accessed_at=datetime.now(),
            embedding=embedding,
            metadata=meta,
        )

        boundary = self._get_capture_boundary()

        def validate():
            return self.policy.write_gate.validate(memory)

        def commit():
            return self._commit_capture(
                role,
                content,
                layer,
                importance,
                emotional_weight,
                embedding,
                **meta,
            )

        result = boundary.propose_and_commit(
            role=role,
            content=content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            meta=meta,
            validate=validate,
            commit=commit,
        )

        if isinstance(result, str) and not result.startswith("denied"):
            post_snap = snapshot_cdg_state(self, capture_ids=[result])
            self._gtbs_shadow_observe(
                pre_snap,
                post_snap,
                context={"phase": "capture", "memory_id": result, "layer": layer},
                proposal={
                    "source": "capture",
                    "operation_type": "INGEST",
                    "target_stores": infer_capture_target_stores(
                        role=role, layer=layer, importance=importance
                    ),
                    "proposed_keys": sorted(post_snap.keys()),
                },
            )
        return result

    def _commit_capture(
        self,
        role: str,
        content: str,
        layer: str,
        importance: float,
        emotional_weight: float,
        embedding,
        **meta,
    ) -> Union[str, Dict[str, Any]]:
        capture_result = self.memory_manager.capture_interaction(
            role,
            content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            embedding=embedding,
            **meta,
        )
        mid = capture_result["episodic_id"]

        if layer in ("goal", "identity", "belief"):
            self.narrative.update_from_memory(content, importance=importance)
        if importance > 0.75:
            self.belief_engine.add_or_update_belief(
                content, confidence=importance, source_memory_id=mid
            )

        if role == "user":
            self._apply_cognitive_state(content, layer=layer, importance=importance)

        if meta.get("update_emotion", True):
            emotion_state = self.emotion_engine.update_from_interaction(
                role,
                content,
                context=meta.get("context"),
                importance=importance,
            )
            if meta.get("return_detail"):
                capture_result["emotion"] = emotion_state.model_dump(mode="json")

        intent_layers = {"goal", "identity", "episodic", "working"}
        if meta.get("update_intent", True) and layer in intent_layers:
            intent_state = self.intent_engine.update_from_interaction(
                role,
                content,
                context=meta.get("context"),
                importance=importance,
            )
            if meta.get("return_detail"):
                capture_result["intent"] = intent_state.model_dump(mode="json")

        if meta.get("return_detail"):
            return capture_result
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
        emotion_context = self.emotion_engine.format_context_block()
        intent_context = self.intent_engine.format_context_block()
        reflective_context = self.reflective_engine.format_context_block(limit=2)
        values_context = self.values_governance.format_context_block(limit=2)
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
        return (
            f"{identity_anchor}\n\n{self_block}\n\n{state_block}\n\n"
            f"{emotion_context}\n\n{intent_context}\n\n{reflective_context}\n\n"
            f"{values_context}\n\n"
            f"{identity_block}\n\n{context}"
        )

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

    def _run_cdg_cycle(
        self,
        pre_state: Dict[str, Any],
        proposed_state: Dict[str, Any],
        *,
        phase: str = "interaction",
    ) -> Dict[str, Any]:
        """CDG hypervisor — govern proposed cognition against pre-state + reality bus."""
        decision = self.cdg.run(pre_state, proposed_state, phase=phase)
        apply_cdg_state(self, decision.modified_state)
        return decision.to_dict()

    def _gtbs_shadow_enabled(self) -> bool:
        cdg = self.config.get("cdg") or {}
        return bool(cdg.get("enable_gtbs_shadow", False))

    def _gtbs_shadow_persist_enabled(self) -> bool:
        cdg = self.config.get("cdg") or {}
        return bool(cdg.get("gtbs_shadow_persist", False))

    def _gtbs_capture_enabled(self) -> bool:
        cdg = self.config.get("cdg") or {}
        return bool(cdg.get("enable_gtbs_capture", False))

    def _get_capture_boundary(self):
        if self._capture_boundary is None:
            from core.governance.gtbs.capture_boundary import CaptureMutationBoundary
            from core.governance.gtbs.transaction_log import GTBSTransactionLog

            self._capture_boundary = CaptureMutationBoundary(
                GTBSTransactionLog(self.base_dir)
            )
        return self._capture_boundary

    def _gtbs_shadow_observe(
        self,
        pre_state: Dict[str, Any],
        post_state: Dict[str, Any],
        *,
        context: Optional[Dict[str, Any]] = None,
        proposal: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        GTBS v1.1 P1.5 — opt-in divergence sensor (Axiom A5).

        No audit write, no CDG feedback, no control. Returns snapshot dict only.
        """
        if not self._gtbs_shadow_enabled():
            return None
        if self._gtbs_observer is None:
            from core.governance.gtbs import RuntimeGatekeeper

            self._gtbs_observer = RuntimeGatekeeper()
        observation = self._gtbs_observer.observe_runtime_event(
            pre_state,
            post_state,
            context=context,
            proposal=proposal,
        )
        if self._gtbs_shadow_persist_enabled():
            from core.governance.gtbs.divergence_collector import get_shadow_collector

            get_shadow_collector(self.base_dir).record(observation)
        return observation

    def _generate_constrained_response(self, user_input: str, context: str) -> str:
        """Self-Model constrained draft (LLM layer injects self_model.to_prompt_block())."""
        return (
            f"[Stable Response] 基于我的长期身份：{self.self_model.identity_summary[:80]}，"
            f"结合当前认知上下文，回应：{user_input[:120]}"
        )

    def _generate_llm_response(
        self,
        user_input: str,
        context: str,
        *,
        temperature: float = 0.7,
        llm_client: Any = None,
        llm_profile: Any = None,
    ) -> str:
        """LLM reply for HTTP /chat full loop; falls back to constrained draft."""
        if llm_client is None or llm_profile is None:
            return self._generate_constrained_response(user_input, context)
        system = "You are a long-lived AI powered by CNexus.\n"
        if context:
            system += f"\n--- Persistent Memory ---\n{context}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_input},
        ]
        return llm_client.chat(llm_profile, messages, temperature=temperature)

    def _get_proactive_config(self) -> Dict[str, Any]:
        return dict(self.config.get("proactive") or {})

    def _apply_proactive_loop(
        self,
        reply: str,
        *,
        allow_proactive: bool = True,
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        """Evaluate proactive intent trigger and optionally append suggestion to reply."""
        cfg = self._get_proactive_config()
        if not allow_proactive or not cfg.get("enabled", True):
            return reply, None

        threshold = float(
            cfg.get("min_motivation_threshold", PROACTIVE_MOTIVATION_THRESHOLD)
        )
        trigger: ProactiveTrigger = self.intent_engine.trigger_proactive(
            min_motivation=threshold
        )
        if not trigger.should_trigger:
            return reply, None

        proactive_info = {
            "triggered": True,
            "reason": trigger.reason,
            "suggested_action": trigger.suggested_action,
            "priority": trigger.priority,
            "goal_id": trigger.goal_id,
        }

        final_reply = reply
        if cfg.get("inject_into_reply", True):
            if "主动" not in reply and len(reply) < 800 and trigger.suggested_action:
                final_reply = f"{reply}\n\n{trigger.suggested_action}"
        return final_reply, proactive_info

    def _interaction_api_fields(
        self,
        cdg_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Unified fields exposed to /chat and external integrators."""
        goals = self.intent_engine.get_active_goals(1)
        if cdg_result and cdg_result.get("rcs") is not None:
            coherence_score = float(cdg_result["rcs"])
        else:
            coherence_score = float(
                self.self_model.coherence_score
                or self.narrative.narrative.narrative_coherence_score
                or 0.0
            )
        return {
            "coherence_score": coherence_score,
            "emotion_state": self.emotion_engine.get_state_summary(),
            "active_intent": goals[0].description if goals else None,
        }

    def process_interaction(
        self,
        user_input: str,
        *,
        assistant_output: Optional[str] = None,
        use_memory: bool = True,
        temperature: float = 0.7,
        llm_client: Any = None,
        llm_profile: Any = None,
        allow_proactive: bool = True,
    ) -> Dict[str, Any]:
        """
        Subject Runtime Loop — experience → interpretation → self-update → prediction.
        When llm_client + llm_profile are provided and assistant_output is omitted,
        generates the reply via LLM before governance (HTTP /chat full loop).
        """
        grounding_event_id = self.cdg.ingest_user_action(user_input)
        pre_state = snapshot_cdg_state(self, user_input=user_input, grounding_event_id=grounding_event_id)

        self.working_self.update_from_input(user_input, self.dna_engine.dna, importance=0.65)

        capture_id = self.capture("user", user_input, importance=0.65)
        if isinstance(capture_id, str) and capture_id.startswith("denied"):
            return {"ok": False, "reason": capture_id, **self._interaction_api_fields()}

        context = self.recall(user_input) if use_memory else ""
        if assistant_output is not None:
            response = assistant_output
        else:
            response = self._generate_llm_response(
                user_input,
                context,
                temperature=temperature,
                llm_client=llm_client,
                llm_profile=llm_profile,
            )

        allowed, gate_reason = self.deliberation.deliberate(
            response, self.working_self, self.dna_engine.dna
        )
        if not allowed:
            return {
                "ok": False,
                "reason": gate_reason,
                "context": context,
                "response": response,
                "reply": response,
                "working_self": self.working_self.to_dict(),
                "self_model": self.self_model.to_dict(),
                **self._interaction_api_fields(),
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

        meta_reflection = self.reflective_engine.reflect_on_interaction(
            response,
            {
                "query": user_input,
                "user_input": user_input,
                "prediction_error": error,
                "context_preview": context[:200] if context else "",
            },
            feedback=None,
            use_llm=self.config.get("reflective_use_llm", True),
        )

        value_alignment = self.intent_engine.check_value_alignment(self.values_governance)
        value_alignment_payload = (
            value_alignment.model_dump(mode="json") if value_alignment else None
        )

        self.working_self.update_prediction_error()
        self.working_self.add_reflection(reflection)
        self.deliberation.regulate_homeostasis(self.working_self)
        self.working_self.sync_to_legacy(self.state)

        capture_ids = [capture_id] if isinstance(capture_id, str) and not capture_id.startswith("denied") else []
        proposed_state = snapshot_cdg_state(
            self,
            user_input=user_input,
            response=response,
            capture_ids=capture_ids,
            grounding_event_id=grounding_event_id,
        )
        cdg_result = self._run_cdg_cycle(pre_state, proposed_state, phase="interaction")
        if not cdg_result.get("approved", True):
            safe_response = cdg_result.get("safe_response") or response
            return {
                "ok": False,
                "reason": cdg_result.get("reason"),
                "response": safe_response,
                "reply": safe_response,
                "cdg": cdg_result,
                "rcs": cdg_result.get("rcs"),
                "working_self": self.working_self.to_dict(),
                "self_model": self.self_model.to_dict(),
                **self._interaction_api_fields(cdg_result),
            }

        post_snap = snapshot_cdg_state(
            self,
            user_input=user_input,
            response=response,
            capture_ids=capture_ids,
            grounding_event_id=grounding_event_id,
        )
        gtbs_shadow = self._gtbs_shadow_observe(
            pre_state,
            post_snap,
            context={
                "phase": "interaction",
                "grounding_event_id": grounding_event_id,
                "capture_id": capture_id,
            },
            proposal={
                "source": "interaction",
                "operation_type": "INTERACTION",
                "target_stores": ["cognitive", "storage", "personality", "narrative"],
                "proposed_keys": sorted(proposed_state.keys()),
            },
        )

        gov = self.run_governance_cycle()

        final_reply, proactive_info = self._apply_proactive_loop(
            response,
            allow_proactive=allow_proactive,
        )
        assistant_capture_id = self.capture("assistant", final_reply, importance=0.55)

        result = {
            "ok": True,
            "response": final_reply,
            "reply": final_reply,
            "capture_id": capture_id,
            "assistant_capture_id": assistant_capture_id,
            "context": context,
            "working_self": self.working_self.to_dict(),
            "self_model": self.self_model.to_dict(),
            "integration": integration,
            "predictive": self.predictive.to_dict(),
            "prediction_error": error,
            "reflection": reflection,
            "meta_reflection": meta_reflection.model_dump(mode="json"),
            "value_alignment": value_alignment_payload,
            "proactive": proactive_info,
            "governance": gov.get("stability_metrics"),
            "cdg": cdg_result,
            "rcs": cdg_result.get("rcs"),
            "potential_v": cdg_result.get("potential_v"),
            "control_phase": cdg_result.get("control_phase"),
            "d_v": cdg_result.get("d_v"),
            "interventions": cdg_result.get("interventions", []),
            **self._interaction_api_fields(cdg_result),
        }
        if gtbs_shadow is not None:
            result["gtbs_shadow"] = gtbs_shadow
        return result

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
        recent = self.cdg.reality_bus.window(1)
        grounding_event_id = recent[-1].event_id if recent else None
        pre_state = snapshot_cdg_state(self, grounding_event_id=grounding_event_id)
        proposed_state = snapshot_cdg_state(self, grounding_event_id=grounding_event_id)
        cdg_snapshot = self._run_cdg_cycle(pre_state, proposed_state, phase="background")
        result = self.stability.run_governance_cycle()
        result["cdg"] = cdg_snapshot
        result["cdg_trajectory"] = self.cdg.trajectory_report()
        if self.config.get("enable_metabolic", True):
            result["memory_maintenance"] = self.maintain_memory()
        return result

    def memory_stats(self) -> Dict[str, Any]:
        return self._lifecycle.collect_stats().to_dict()

    def run_memory_maintenance(self, *, force: bool = False) -> Dict[str, Any]:
        """Metabolic cycle — block + episodic decay, forget, compression."""
        if not self.config.get("enable_metabolic", True) and not force:
            return {"skipped": True, "reason": "enable_metabolic=false"}
        return self.memory_manager.run_maintenance(force=force)

    def maintain_memory(self, *, force: bool = False) -> Dict[str, Any]:
        """Block lifecycle + episodic maintenance + sleep-time consolidation."""
        if not self.config.get("enable_metabolic", True) and not force:
            return {"skipped": True, "reason": "enable_metabolic=false"}

        block_report = self.memory_manager.run_maintenance(force=force)
        sleep_report = self.sleep_time_compute.run_sleep_cycle(force=force)
        return {
            **block_report,
            "sleep_time": sleep_report.to_dict(),
        }

    async def maintain_memory_async(self, *, force: bool = False) -> Dict[str, Any]:
        """Async maintenance entry for background schedulers."""
        if not self.config.get("enable_metabolic", True) and not force:
            return {"skipped": True, "reason": "enable_metabolic=false"}

        block_report = self.memory_manager.run_maintenance(force=force)
        sleep_report = await self.sleep_time_compute.run_sleep_cycle_async(force=force)
        return {
            **block_report,
            "sleep_time": sleep_report.to_dict(),
        }

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
            "cdg": {
                "last_decision": (
                    self.cdg.last_decision.to_dict() if self.cdg.last_decision else None
                ),
                "reality_frames": len(self.cdg.reality_bus.frames),
                "trajectory": self.cdg.trajectory_report(last_n=10),
            },
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
                    "cdg_phase": "advisory epistemic governance sidecar",
                },
                "cdg": state.get("cdg"),
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

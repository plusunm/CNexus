import asyncio
import copy
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.config_loader import ConfigLoader
from core.runtime_profile import apply_runtime_profile_with_meta
from core.execution.inference_scheduler import InferenceScheduler
from core.execution.local_stack import LocalStackManager
from core.execution.plane import ExecutionPlane
from core.llm_client import LLMClient
from core.model_registry import ModelProfile
from core.embedding import EmbeddingService
from core.paths import get_project_root, resolve_memory_dir
from core.goal.goal_manager import GoalManager
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
    PROACTIVE_PROGRESS_CAP,
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
from memory.runtime_guard import runtime_write_context
from memory.schema import Memory
from runtime.attention import DynamicAttentionField
from runtime.cognitive_apply import process_parsed_state
from runtime.cognitive_parser import CognitiveStateParser, IdentitySummaryScheduler
from runtime.cognitive_recall import CognitiveRecallEngine
from runtime.cognitive_state import PersistentCognitiveState
from runtime.context import ContextAssemblyEngine
from runtime.predictive_loop import PredictiveSelf
from core.governance.deliberation import DeliberativeGovernance
from core.governance.pipeline import GovernancePipeline
from runtime.recall_pipeline import RecallPipeline
from brain_memory.runtime_state import dump_runtime_state, restore_runtime_state
from core.observability.metrics import get_metrics
from core.observability.mind_overview import build_mind_overview
from core.runtime.entry_registry import RUNTIME_ENTRY_MATRIX, get_entry_spec
from runtime.router import HierarchicalRecallEngine
from runtime.state import CognitiveStateManager
from storage.manager import UnifiedStorageManager

logger = logging.getLogger(__name__)


class BrainMemoryRuntime:
    """
    CNexus — multi-store cognitive continuity facade (L1→L5).

    SDK v0.1: ``create_runtime()`` + ``process_interaction(message=..., user_id=..., metadata=...)``
    returns ``response``, ``attention_state``, ``provenance``, ``reflection_triggered``.
    Positional ``user_input`` remains supported for backward compatibility.
    """

    @classmethod
    def create_runtime(
        cls,
        config_path: str = "config/default.json",
        base_dir: str = "memory",
        project_root: Optional[str] = None,
    ) -> "BrainMemoryRuntime":
        """Recommended factory — mirrors module-level ``create_runtime``."""
        return cls(
            config_path=config_path,
            base_dir=base_dir,
            project_root=project_root,
        )

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
        merged_cfg, self._compute_profile, self._compute_policy = apply_runtime_profile_with_meta(
            self.config_loader.config
        )
        self.config_loader.config = merged_cfg
        cfg = merged_cfg

        if os.environ.get("CNEXUS_ENV") == "production" and os.environ.get("CNEXUS_BYPASS_RUNTIME_GUARD") == "1":
            raise RuntimeError(
                "CNEXUS_BYPASS_RUNTIME_GUARD=1 is forbidden when CNEXUS_ENV=production"
            )

        self.base_dir = resolve_memory_dir(self.project_root, base_dir)
        fail_loud = bool(cfg.get("embedding_fail_loud_in_production", False))
        if os.environ.get("CNEXUS_ENV") == "production":
            fail_loud = fail_loud or bool(cfg.get("embedding_fail_loud_in_production", True))
        self._execution_plane = ExecutionPlane.from_config(cfg)
        self._inference_scheduler = InferenceScheduler.from_config(
            self._execution_plane,
            cfg,
            base_dir=str(self.base_dir),
        )
        self._local_stack = LocalStackManager(self._execution_plane, cfg)
        self.embedder = EmbeddingService(
            scheduler=self._inference_scheduler,
            host=cfg.get("ollama_host", "http://localhost:11434"),
            model=cfg.get("embedding_model", "nomic-embed-text"),
            vector_dim=cfg.get("vector_dim", 768),
            fallback=cfg.get("embedding_fallback", "hash"),
            fail_loud_in_production=fail_loud,
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

        safety_cfg = cfg.get("safety") or {}
        write_gate_threshold = float(
            safety_cfg.get("write_gate_threshold")
            or cfg.get("write_gate_threshold", 0.65)
        )
        self.policy = GovernancePolicyDescriptor(write_gate_threshold=write_gate_threshold)

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

        # Layer 1 — Memory Manager (structured blocks + episodic storage)
        self.memory_manager = MemoryManager(
            self.base_dir,
            storage=self.storage,
            write_gate=self.policy.write_gate,
        )
        self.memory_manager.set_embedder(self.embedder)
        self.memory_manager.configure_lifecycle(self._lifecycle)
        self.belief_engine.set_memory_manager(self.memory_manager)
        self.belief_engine.restore_from_memory_manager()
        self.router.set_memory_manager(self.memory_manager)
        self.context_engine.set_memory_manager(self.memory_manager)
        self.router.warm_up()
        snapshot = self.memory_manager.get_attention_snapshot()
        if snapshot:
            self.attention.hydrate_from_snapshot(snapshot)

        # L3 — Emotion + Intent continuity (MemoryBlocks)
        self.emotion_engine = EmotionEngine(self.memory_manager)
        self.intent_engine = IntentEngine(self.memory_manager)
        self.goal_manager = GoalManager(
            self.intent_engine,
            narrative_builder=self.narrative,
            working_self=self.working_self,
            cse_mode=str(cfg.get("cse_mode") or "idle"),
        )
        self._llm_client = LLMClient(scheduler=self._inference_scheduler)
        self._llm_client.bind_plane(self._execution_plane)
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
        self.goal_manager.bind_runtime(
            belief_engine=self.belief_engine,
            values_governance=self.values_governance,
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
        self.governance_pipeline = GovernancePipeline(
            self.deliberation,
            self.cdg,
            values_governance=self.values_governance,
            intent_engine=self.intent_engine,
        )
        self.recall_pipeline = RecallPipeline(self)

        # Validation
        self.validation = StabilityValidationOrchestrator(self)

        self.recall_top_k = cfg.get("recall_top_k", 12)
        self.runtime_mode = cfg.get("runtime_mode", "g2")
        self._gtbs_observer = None
        self._capture_boundary = None
        self._write_intent_bus = None
        self._attention_turn = 0
        self._last_reflection_turn = -999
        self._chat_prepare_cache: Dict[str, Dict[str, Any]] = {}
        self._chat_prepare_lock = threading.Lock()
        self._chat_prepare_ttl_seconds = int(cfg.get("chat_prepare_ttl_seconds", 300))
        self._last_governance_at: Optional[str] = None
        try:
            from core.spine.identity.store import configure_identity_store
            from core.spine.integration import register_spine_writer
            from core.spine.storage import SpineEventLog
            from core.spine.token.token_store import configure_token_store
            from core.spine.writer import SpineWriter

            base = str(self.base_dir)
            configure_identity_store(base)
            configure_token_store(base)
            register_spine_writer(SpineWriter(SpineEventLog(base)))
        except Exception as exc:
            logger.warning("Spine integration unavailable at runtime init: %s", exc)
        try:
            from core.runtime.execution_trace import configure_execution_trace

            configure_execution_trace(str(self.base_dir))
        except Exception as exc:
            logger.debug("Execution trace not configured: %s", exc)
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
    def execution_plane(self) -> ExecutionPlane:
        return self._execution_plane

    @property
    def inference_scheduler(self) -> InferenceScheduler:
        return self._inference_scheduler

    @property
    def compute_profile(self):
        return self._compute_profile

    @property
    def compute_policy(self):
        return self._compute_policy

    @property
    def local_stack(self) -> LocalStackManager:
        return self._local_stack

    @property
    def llm_client(self) -> LLMClient:
        return self._llm_client

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
    def goal(self):
        return self.goal_manager

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

    def _sync_attention_snapshot(self) -> Dict[str, Any]:
        self._attention_turn += 1
        sync_info = self.attention.sync_and_persist(self.memory_manager, self._attention_turn)
        if float(sync_info.get("drift_score", 0.0)) >= 0.45:
            self._record_attention_drift_reflection(sync_info)
        return sync_info

    def _record_attention_drift_reflection(self, sync_info: Dict[str, Any]) -> None:
        drift = float(sync_info.get("drift_score", 0.0))
        top_focus = sync_info.get("top_focus") or []
        note = (
            f"Attention drift detected (score={drift:.2f}); "
            f"top_focus={top_focus}. Recording stability note."
        )
        try:
            self.reflective_engine.reflect_on_interaction(
                note,
                {
                    "query": "attention_drift",
                    "attention_sync": sync_info,
                    "prediction_error": drift,
                },
                feedback="attention_shift",
                use_llm=False,
            )
        except Exception as exc:
            logger.warning("Attention drift reflection skipped: %s", exc)

    @property
    def attention_state_block(self):
        return self.memory_manager.get_attention_state_block()

    @property
    def episodic_event_block(self):
        return self.memory_manager.get_episodic_block("event")

    @property
    def episodic_dialogue_block(self):
        return self.memory_manager.get_episodic_block("dialogue")

    @property
    def episodic_decision_block(self):
        return self.memory_manager.get_episodic_block("decision")

    @property
    def episodic_event_store(self):
        return self.episodic_event_block

    @property
    def episodic_dialogue_store(self):
        return self.episodic_dialogue_block

    @property
    def episodic_decision_store(self):
        return self.episodic_decision_block

    def _persist_reflection_memory(self, role: str, content: str, **kwargs) -> str:
        with runtime_write_context():
            result = self.capture(
                role,
                content,
                layer=kwargs.pop("layer", "episodic"),
                importance=kwargs.pop("importance", 0.6),
                update_emotion=False,
                update_intent=False,
                **kwargs,
            )
        if isinstance(result, dict):
            return str(result.get("episodic_id") or "")
        return str(result)

    def capture(
        self,
        role: str,
        content: str,
        layer: str = "episodic",
        importance: float = 0.5,
        emotional_weight: float = 0.5,
        **meta,
    ) -> Union[str, Dict[str, Any]]:
        with runtime_write_context():
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

        pre_snap = snapshot_cdg_state(self)
        cdg_ok, cdg_reason = self._precheck_capture_cdg(
            role=role, content=content, layer=layer, pre_state=pre_snap
        )
        if not cdg_ok:
            return f"denied: cdg_blocked ({cdg_reason})"

        from core.governance.gtbs.adapters.capture_adapter import build_capture_write_intent
        from core.governance.gtbs.write_funnel import maybe_execute_write_intent

        return maybe_execute_write_intent(
            self,
            lambda: build_capture_write_intent(
                role=role,
                content=content,
                layer=layer,
                importance=importance,
                emotional_weight=emotional_weight,
                meta=meta,
                source="capture_direct",
            ),
            lambda: self._commit_capture(
                role,
                content,
                layer,
                importance,
                emotional_weight,
                memory.embedding,
                **meta,
            ),
            tier_b_meta={"role": role, "layer": layer, "importance": importance},
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
        cdg_ok, cdg_reason = self._precheck_capture_cdg(
            role=role, content=content, layer=layer, pre_state=pre_snap
        )
        if not cdg_ok:
            return f"denied: cdg_blocked ({cdg_reason})"

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
            runtime=self,
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
            intent_state = self.goal_manager.mount_on_capture(
                role,
                content,
                layer,
                importance,
                context=meta.get("context"),
                update_intent=True,
            )
            if layer in ("goal", "identity") and self.goal_manager.cse_mode == "batch":
                self.goal_manager.flush_synthesis()
            if meta.get("return_detail") and intent_state is not None:
                capture_result["intent"] = intent_state.model_dump(mode="json")

        if meta.get("return_detail"):
            from core.spine.hooks.mutation import emit_capture_mutation

            emit_capture_mutation(
                memory_id=str(mid),
                role=role,
                layer=layer,
                importance=importance,
            )
            return capture_result
        from core.spine.hooks.mutation import emit_capture_mutation

        emit_capture_mutation(
            memory_id=str(mid),
            role=role,
            layer=layer,
            importance=importance,
        )
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
        self._maybe_emit_working_self_shadow(
            user_input,
            importance=importance,
            layer=layer,
            source="cognitive_state",
        )
        from core.spine.state.track import commit_runtime_state_diff, snapshot_runtime_tier_a

        _ws_before = snapshot_runtime_tier_a(self)
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
        commit_runtime_state_diff(self, _ws_before, label="cognitive_state")
        return applied

    def _maybe_emit_working_self_shadow(
        self,
        text: str,
        *,
        importance: float,
        layer: Optional[str] = None,
        source: str = "interaction",
    ) -> None:
        from core.governance.gtbs.adapters.working_self_adapter import (
            maybe_emit_working_self_shadow,
        )

        maybe_emit_working_self_shadow(
            self,
            text=text,
            importance=importance,
            layer=layer,
            source=source,
        )

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
            with runtime_write_context():
                result["applied"] = process_parsed_state(
                    parsed,
                    narrative=self.narrative,
                    belief_engine=self.belief_engine,
                    state=self.state,
                    scheduler=self.identity_scheduler,
                )
        return result

    def recall(
        self,
        query: str,
        top_k: Optional[int] = None,
        *,
        use_attention: bool = True,
        mutate_state: bool = False,
    ) -> str:
        from core.control_plane.guards import warn_direct_runtime_access

        warn_direct_runtime_access("recall")
        return self.recall_pipeline.recall(
            query,
            top_k=top_k,
            use_attention=use_attention,
            mutate_state=mutate_state,
        )

    def dump_state(self) -> Dict[str, Any]:
        """Production snapshot — see brain_memory.runtime_state."""
        return dump_runtime_state(self)

    def restore_state(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        return restore_runtime_state(self, snapshot)

    def get_entry_matrix(self) -> Dict[str, Any]:
        return dict(RUNTIME_ENTRY_MATRIX)

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        return get_metrics().snapshot()

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

    def _predictive_checkpoint(self) -> Dict[str, Any]:
        return {
            "prediction_error": self.predictive.prediction_error,
            "surprise_level": self.predictive.surprise_level,
            "correction_count": self.predictive.correction_count,
            "self_expectations": dict(self.self_model.self_expectations),
            "working_prediction_error": self.working_self.prediction_error,
        }

    def _restore_predictive_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        self.predictive.prediction_error = float(checkpoint.get("prediction_error", 0.0))
        self.predictive.surprise_level = float(checkpoint.get("surprise_level", 0.0))
        self.predictive.correction_count = int(checkpoint.get("correction_count", 0))
        self.working_self.prediction_error = float(
            checkpoint.get("working_prediction_error", 0.0)
        )
        expectations = checkpoint.get("self_expectations")
        if isinstance(expectations, dict):
            self.self_model.self_expectations.clear()
            self.self_model.self_expectations.update(expectations)

    def _apply_post_cdg_interaction_updates(
        self,
        *,
        text: str,
        response: str,
        reflection: str,
        error: float,
        context: str,
        chat_mode: bool = False,
    ) -> tuple[Any, Dict[str, Any], bool]:
        integration = self.self_model_store.integrate(
            text,
            response,
            reflection=reflection,
            dna=self.dna_engine.dna,
            prediction_error=error,
            relation_shift=self.working_self.relationship_tone - 0.7,
        )

        self.narrative.update_from_interaction(
            text, response, reflection=reflection, importance=0.65
        )
        self._sync_narrative_from_self_model()
        self.belief_engine._persist_narrative_block()
        self._sync_beliefs_from_self_model()

        meta_reflection_payload: Dict[str, Any] = {}
        reflection_triggered = False
        cooldown = int(self.config.get("reflection_cooldown_turns", 0))
        turns_since_reflection = self._attention_turn - self._last_reflection_turn
        use_refl_llm = bool(self.config.get("reflective_use_llm", True)) and not chat_mode
        if cooldown > 0 and turns_since_reflection < cooldown:
            use_refl_llm = False

        if use_refl_llm or cooldown == 0:
            meta_reflection = self.reflective_engine.reflect_on_interaction(
                response,
                {
                    "query": text,
                    "user_input": text,
                    "prediction_error": error,
                    "context_preview": context[:200] if context else "",
                },
                feedback=None,
                use_llm=use_refl_llm,
            )
            meta_reflection_payload = meta_reflection.model_dump(mode="json")
            reflection_triggered = error > 0.4 or bool(
                meta_reflection_payload.get("inner_thought")
                or meta_reflection_payload.get("scene")
            )
            if reflection_triggered:
                self._last_reflection_turn = self._attention_turn
            focus_id = self.goal_manager.current_focus()
            self.goal_manager.ingest_reflection(
                inner_thought=str(meta_reflection_payload.get("inner_thought") or ""),
                query=text,
                goal_id=focus_id,
                alignment_score=float(error) if error < 1.0 else 0.75,
            )

        return integration, meta_reflection_payload, reflection_triggered

    def _schedule_chat_deferred_cognition(self, work: Any) -> None:
        if not self.config.get("chat_defer_cognition", True):
            with runtime_write_context():
                work()
            return
        thread = threading.Thread(
            target=self._run_chat_deferred_cognition,
            args=(work,),
            name="cnexus-chat-deferred",
            daemon=True,
        )
        thread.start()

    def _run_chat_deferred_cognition(self, work: Any) -> None:
        try:
            with runtime_write_context():
                work()
        except Exception as exc:
            logger.exception("Chat deferred cognition failed")
            self._emit_deferred_cognition_error(exc)

    def _emit_deferred_cognition_error(self, exc: Exception) -> None:
        payload = {"error": str(exc), "type": type(exc).__name__}
        try:
            from api.runtime_log import runtime_log

            runtime_log("error", "chat_deferred", "后台认知任务失败", **payload)
        except Exception:
            pass

    def _finish_chat_cognition_background(
        self,
        *,
        text: str,
        response: str,
        llm_reply: str,
        context: str,
        capture_id: Any,
        chat_governance_notes: List[Dict[str, Any]],
        grounding_event_id: str,
        pre_state: Dict[str, Any],
        meta: Dict[str, Any],
        user_id: Optional[str],
        allow_proactive: bool,
    ) -> None:
        """Post-reply cognition for chat — capture, CDG, reflection (no reply rewrite)."""
        from core.governance.gtbs.adapters.chat_deferred_adapter import (
            maybe_emit_chat_deferred_shadow,
        )

        maybe_emit_chat_deferred_shadow(
            self,
            text=text,
            capture_id=capture_id,
            grounding_event_id=grounding_event_id,
        )
        pred_ckpt = self._predictive_checkpoint()
        error = self.predictive.predict_and_update(
            text, response, self.working_self, self.self_model
        )
        reflection = f"本次交互预测误差 {error:.2f}，"
        reflection += "触发自我校正。" if error > 0.4 else "维持稳定性身份。"

        value_alignment = self.intent_engine.check_value_alignment(self.values_governance)
        values_mode = str((self.config.get("governance") or {}).get("values_mode", "OBSERVE"))
        values_decision = self.governance_pipeline.apply_values_enforcement(
            values_mode, response, value_alignment
        )
        if values_decision.action == "BLOCK":
            chat_governance_notes.append(
                {
                    "stage": "values",
                    "action": "BLOCK",
                    "reason": values_decision.reason,
                    "decision": values_decision.to_dict(),
                }
            )
        elif values_decision.action == "REWRITE" and values_decision.safe_text:
            chat_governance_notes.append(
                {
                    "stage": "values",
                    "action": "REWRITE",
                    "reason": values_decision.reason,
                    "decision": values_decision.to_dict(),
                }
            )

        capture_ids = (
            [capture_id]
            if isinstance(capture_id, str) and not capture_id.startswith("denied")
            else []
        )
        proposed_state = snapshot_cdg_state(
            self,
            user_input=text,
            response=response,
            capture_ids=capture_ids,
            grounding_event_id=grounding_event_id,
        )
        cdg_result = self._run_cdg_cycle(pre_state, proposed_state, phase="interaction")
        if not cdg_result.get("approved", True):
            chat_governance_notes.append(
                {
                    "stage": "cdg",
                    "action": "BLOCK",
                    "reason": cdg_result.get("reason"),
                    "decision": cdg_result,
                }
            )

        self._apply_post_cdg_interaction_updates(
            text=text,
            response=response,
            reflection=reflection,
            error=error,
            context=context,
            chat_mode=True,
        )

        self.working_self.update_prediction_error()
        self.working_self.add_reflection(reflection)
        self.deliberation.regulate_homeostasis(self.working_self)
        self.working_self.sync_to_legacy(self.state)

        post_snap = snapshot_cdg_state(
            self,
            user_input=text,
            response=response,
            capture_ids=capture_ids,
            grounding_event_id=grounding_event_id,
        )
        self._gtbs_shadow_observe(
            pre_state,
            post_snap,
            context={
                "phase": "interaction",
                "grounding_event_id": grounding_event_id,
                "capture_id": capture_id,
                "chat_deferred": True,
            },
            proposal={
                "source": "interaction",
                "operation_type": "INTERACTION",
                "target_stores": ["cognitive", "storage", "personality", "narrative"],
                "proposed_keys": sorted(proposed_state.keys()),
            },
        )

        self._apply_proactive_loop(
            llm_reply,
            allow_proactive=allow_proactive,
            inject_into_reply=False,
        )
        self.run_governance_cycle()
        assistant_capture_id = self.capture(
            "assistant", llm_reply, importance=0.55, **meta
        )
        logger.info(
            "Chat deferred cognition done user_capture=%s assistant_capture=%s",
            capture_id,
            assistant_capture_id,
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
        from core.governance.gtbs.adapters.cdg_adapter import maybe_emit_cdg_apply_shadow

        intent_id = maybe_emit_cdg_apply_shadow(
            self,
            phase=phase,
            pre_state=pre_state,
            proposed_state=proposed_state,
            modified_state=decision.modified_state,
            decision_summary={
                "approved": decision.approved,
                "phase": phase,
                "interventions": list(decision.interventions)[:5],
            },
        )
        apply_cdg_state(self, decision.modified_state)
        from core.spine.hooks.mutation import emit_cdg_mutation

        emit_cdg_mutation(
            phase=phase,
            intent_id=intent_id,
            extra={"approved": decision.approved},
        )
        if intent_id and hasattr(self, "_get_write_intent_bus"):
            self._get_write_intent_bus().record_shadow_commit(
                intent_id,
                receipt={"phase": phase, "applied": True},
            )
        return decision.to_dict()

    def _chat_intercept_output_enabled(self) -> bool:
        gov = self.config.get("governance") or {}
        return bool(gov.get("chat_intercept_output", True))

    def _cdg_capture_block_enabled(self) -> bool:
        cdg = self.config.get("cdg") or {}
        return bool(cdg.get("block_capture_writes", True))

    def _precheck_capture_cdg(
        self,
        *,
        role: str,
        content: str,
        layer: str,
        pre_state: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        if not self._cdg_capture_block_enabled():
            return True, ""
        pre = pre_state or snapshot_cdg_state(self)
        proposed = copy.deepcopy(pre)
        proposed["memory"].append(
            {
                "memory_id": "pending_capture",
                "content": content,
                "causal_parent": "",
                "is_synthetic": False,
                "provenance": "capture",
                "layer": layer,
                "role": role,
            }
        )
        decision = self.cdg.run(pre, proposed, phase="capture")
        if decision.approved:
            return True, ""
        reason = str(decision.metrics.get("reason") or "cdg_blocked")
        logger.info("Capture: CDG pre-write block: %s", reason)
        return False, reason

    def _maybe_intercept_chat_reply(
        self,
        gov_pre: Any,
        reply: str,
        chat_governance_notes: List[Dict[str, Any]],
    ) -> tuple[str, bool]:
        if gov_pre.approved:
            return reply, False
        chat_governance_notes.append(
            {
                "stage": "output_check",
                "action": "BLOCK",
                "reason": gov_pre.reason,
                "decision": gov_pre.to_dict(),
            }
        )
        if self._chat_intercept_output_enabled():
            safe = gov_pre.safe_text or self.governance_pipeline.safe_fallback(
                gov_pre.reason, reply
            )
            logger.info("Chat: governance intercept: %s", gov_pre.reason)
            return safe, True
        logger.info("Chat: governance note (not intercepting): %s", gov_pre.reason)
        return reply, False

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
            from core.governance.gtbs.write_intent_bus import shadow_emit_enabled

            bus = self._get_write_intent_bus() if shadow_emit_enabled(config=self.config) else None
            self._capture_boundary = CaptureMutationBoundary(
                GTBSTransactionLog(self.base_dir),
                write_intent_bus=bus,
            )
        return self._capture_boundary

    def _get_write_intent_bus(self):
        if self._write_intent_bus is None:
            from core.governance.gtbs.transaction_log import GTBSTransactionLog
            from core.governance.gtbs.write_intent_bus import WriteIntentBus

            self._write_intent_bus = WriteIntentBus(GTBSTransactionLog(self.base_dir))
        return self._write_intent_bus

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

    def _build_chat_governance_injection(
        self,
        user_input: str,
        chat_governance_notes: List[Dict[str, Any]],
        *,
        persist_alignment: bool = False,
    ) -> str:
        """Dialogue governance — inject guidance into LLM system prompt only."""
        parts: List[str] = []

        allowed, reason = self.deliberation.deliberate(
            user_input, self.working_self, self.dna_engine.dna
        )
        if not allowed:
            parts.append(
                f"【Governance】User message flagged ({reason}). "
                "Respond within identity and values; do not adopt conflicting roles."
            )
            chat_governance_notes.append(
                {"stage": "input_deliberation", "action": "INJECT", "reason": reason}
            )

        align = self.values_governance.check_intent_alignment(
            user_input,
            importance=0.65,
            metadata={"source": "chat_user_input"},
            persist=persist_alignment,
        )
        status = str(getattr(align.status, "value", align.status)).lower()
        if status not in ("aligned",):
            if align.suggested_adjustments:
                parts.append(
                    "【Values guidance】" + "; ".join(align.suggested_adjustments[:4])
                )
            elif align.reasons:
                parts.append("【Values guidance】" + "; ".join(align.reasons[:4]))
            chat_governance_notes.append(
                {
                    "stage": "input_values",
                    "action": "INJECT",
                    "reason": status,
                    "alignment_score": align.alignment_score,
                }
            )

        anchor = self.dna_engine.get_identity_anchor_prompt()
        if anchor:
            parts.append(f"【Identity constraints】\n{anchor}")

        values_mode = str((self.config.get("governance") or {}).get("values_mode", "OBSERVE")).upper()
        if values_mode in ("FLAG", "REWRITE", "BLOCK"):
            parts.append(
                f"【Governance mode】{values_mode} — apply constraints in your reply directly."
            )

        return "\n\n".join(parts)

    def _compose_chat_llm_messages(
        self,
        user_input: str,
        context: str,
        *,
        extra_system: Optional[str] = None,
    ) -> tuple[str, List[Dict[str, str]]]:
        system = "You are a long-lived AI powered by CNexus.\n"
        if extra_system:
            system += f"\n--- Governance ---\n{extra_system}\n"
        if context:
            system += f"\n--- Persistent Memory ---\n{context}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_input},
        ]
        return system, messages

    def _format_chat_outbound_preview(
        self,
        user_input: str,
        context: str,
        governance_injection: str,
        system_prompt: str,
    ) -> str:
        lines = [
            "【你的消息】",
            user_input,
            "",
            "【系统注入 · 记忆】",
            context.strip() if context.strip() else "(无)",
            "",
            "【系统注入 · 治理 / 身份】",
            governance_injection.strip() if governance_injection.strip() else "(无)",
            "",
            "【将发送给模型的完整提示】",
            "--- system ---",
            system_prompt,
            "--- user ---",
            user_input,
        ]
        return "\n".join(lines)

    def _purge_expired_chat_prepare(self) -> None:
        now = time.time()
        with self._chat_prepare_lock:
            expired = [
                key
                for key, value in self._chat_prepare_cache.items()
                if value.get("expires_at", 0) < now
            ]
            for key in expired:
                self._chat_prepare_cache.pop(key, None)

    def _trace_interaction_step(self, step: str, **extra: Any) -> None:
        """Append-only interaction trace — never blocks the main loop."""
        try:
            from core.runtime.execution_trace import append_execution_trace

            append_execution_trace(
                str(self.base_dir),
                {"type": "interaction_step", "step": step, **extra},
            )
        except Exception:
            logger.debug("interaction trace skipped for step=%s", step, exc_info=True)

    def prepare_chat_turn(
        self,
        text: str,
        *,
        use_memory: bool = True,
        chat_mode: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build outbound LLM payload for human authorization — no capture or LLM call."""
        message = (text or "").strip()
        if not message:
            raise ValueError("message is required")

        meta = dict(metadata or {})
        self._purge_expired_chat_prepare()

        chat_governance_notes: List[Dict[str, Any]] = []
        context = ""
        if use_memory:
            recall_k = int(self.config.get("chat_recall_top_k", 6)) if chat_mode else None
            context = self.recall(message, top_k=recall_k, mutate_state=False)
        if chat_mode and context:
            max_ctx = int(self.config.get("chat_max_context_chars", 4000))
            if len(context) > max_ctx:
                context = context[:max_ctx] + "\n…"

        governance_injection = ""
        if chat_mode:
            governance_injection = self._build_chat_governance_injection(
                message, chat_governance_notes, persist_alignment=False
            )

        system_prompt, messages = self._compose_chat_llm_messages(
            message,
            context,
            extra_system=governance_injection or None,
        )
        prepare_id = uuid.uuid4().hex
        expires_at = time.time() + self._chat_prepare_ttl_seconds
        bundle = {
            "prepare_id": prepare_id,
            "text": message,
            "context": context,
            "governance_injection": governance_injection,
            "chat_governance_notes": list(chat_governance_notes),
            "messages": messages,
            "system_prompt": system_prompt,
            "meta": meta,
            "use_memory": use_memory,
            "chat_mode": chat_mode,
            "expires_at": expires_at,
        }
        with self._chat_prepare_lock:
            self._chat_prepare_cache[prepare_id] = bundle

        outbound_preview = self._format_chat_outbound_preview(
            message,
            context,
            governance_injection,
            system_prompt,
        )
        has_injection = bool(context.strip() or governance_injection.strip())

        return {
            "prepare_id": prepare_id,
            "user_message": message,
            "memory_context": context,
            "governance_injection": governance_injection,
            "system_prompt": system_prompt,
            "outbound_preview": outbound_preview,
            "has_injection": has_injection,
            "chat_governance_notes": chat_governance_notes,
            "expires_in_seconds": self._chat_prepare_ttl_seconds,
            "messages": messages,
        }

    def cancel_prepared_chat_turn(self, prepare_id: str) -> bool:
        self._purge_expired_chat_prepare()
        with self._chat_prepare_lock:
            return self._chat_prepare_cache.pop(prepare_id, None) is not None

    def _execute_authorized_chat_turn(
        self,
        text: str,
        *,
        context: str,
        governance_injection: str,
        chat_governance_notes: List[Dict[str, Any]],
        messages: List[Dict[str, str]],
        meta: Dict[str, Any],
        user_id: Optional[str],
        temperature: float,
        llm_client: Any,
        llm_profile: Any,
        allow_proactive: bool,
        chat_mode: bool,
    ) -> Dict[str, Any]:
        grounding_event_id = self.cdg.ingest_user_action(text)
        pre_state = snapshot_cdg_state(self, user_input=text, grounding_event_id=grounding_event_id)

        if chat_mode:
            self.values_governance.check_intent_alignment(
                text,
                importance=0.65,
                metadata={"source": "chat_user_input", "phase": "authorized_send"},
                persist=True,
            )

        self._maybe_emit_working_self_shadow(text, importance=0.65, source="prepared_chat")
        from core.spine.state.track import commit_runtime_state_diff, snapshot_runtime_tier_a

        _ws_before = snapshot_runtime_tier_a(self)
        self.working_self.update_from_input(text, self.dna_engine.dna, importance=0.65)
        commit_runtime_state_diff(self, _ws_before, label="chat_working_self")

        capture_id: Any = self.capture("user", text, importance=0.65, **meta)
        capture_denied = isinstance(capture_id, str) and capture_id.startswith("denied")
        if capture_denied and chat_mode:
            logger.info("Chat: capture denied (not intercepting): %s", capture_id)
            chat_governance_notes.append(
                {"stage": "capture", "action": "DENY", "reason": capture_id}
            )
        elif capture_denied:
            return self._finalize_interaction_result(
                {
                    "ok": False,
                    "reason": capture_id,
                    **self._interaction_api_fields(),
                },
                user_id=user_id,
                meta=meta,
            )

        if llm_client is None or llm_profile is None:
            response = self._generate_constrained_response(text, context)
        else:
            from core.spine.emit import emit_execution_llm_call

            llm_ev = emit_execution_llm_call(
                caller="_execute_authorized_chat_turn",
                model_hint=str(getattr(llm_profile, "model", "") or ""),
                input_chars=len(text) + len(context),
            )
            response = llm_client.chat(llm_profile, messages, temperature=temperature)
            try:
                from core.runtime.trace_context import get_trace_id
                from core.spine.token.hooks import emit_tokens_for_llm_chars

                tid = (llm_ev.trace_id if llm_ev else None) or get_trace_id()
                if tid:
                    emit_tokens_for_llm_chars(
                        tid,
                        spine_event_id=llm_ev.event_id if llm_ev else None,
                        input_chars=len(text) + len(context),
                        output_chars=len(response or ""),
                        base_dir=str(self.base_dir),
                        caller="_execute_authorized_chat_turn",
                    )
            except Exception:
                pass
        llm_reply = response

        gov_pre = self.governance_pipeline.check_output(
            response, self.working_self, self.dna_engine.dna
        )
        intercepted = False
        if chat_mode:
            llm_reply, intercepted = self._maybe_intercept_chat_reply(
                gov_pre, llm_reply, chat_governance_notes
            )
            response = llm_reply
        elif not gov_pre.approved:
            safe_response = gov_pre.safe_text or self.governance_pipeline.safe_fallback(
                gov_pre.reason, response
            )
            return self._finalize_interaction_result(
                {
                    "ok": False,
                    "reason": gov_pre.reason,
                    "context": context,
                    "response": safe_response,
                    "reply": safe_response,
                    "governance_decision": gov_pre.to_dict(),
                    "working_self": self.working_self.to_dict(),
                    "self_model": self.self_model.to_dict(),
                    **self._interaction_api_fields(),
                },
                user_id=user_id,
                meta=meta,
            )

        chat_defer = (
            chat_mode
            and llm_reply is not None
            and self.config.get("chat_defer_cognition", True)
            and not meta.get("full_cognitive_loop")
        )
        if chat_defer:
            quick: Dict[str, Any] = {
                "ok": True,
                "response": llm_reply,
                "reply": llm_reply,
                "user_message": text,
                "capture_id": capture_id,
                "context": context,
                "chat_mode": True,
                "intercepted": intercepted,
                "llm_reply_pristine": not intercepted,
                "cognition_deferred": True,
                "human_authorized": True,
                **self._interaction_api_fields(),
            }
            if governance_injection:
                quick["governance_injection_chars"] = len(governance_injection)
            if chat_governance_notes:
                quick["chat_governance_notes"] = list(chat_governance_notes)
            if not gov_pre.approved:
                quick["governance_decision"] = gov_pre.to_dict()

            self._schedule_chat_deferred_cognition(
                lambda: self._finish_chat_cognition_background(
                    text=text,
                    response=response,
                    llm_reply=llm_reply,
                    context=context,
                    capture_id=capture_id,
                    chat_governance_notes=list(chat_governance_notes),
                    grounding_event_id=grounding_event_id,
                    pre_state=pre_state,
                    meta=dict(meta),
                    user_id=user_id,
                    allow_proactive=allow_proactive,
                )
            )
            return self._finalize_interaction_result(quick, user_id=user_id, meta=meta)

        self._finish_chat_cognition_background(
            text=text,
            response=response,
            llm_reply=llm_reply,
            context=context,
            capture_id=capture_id,
            chat_governance_notes=list(chat_governance_notes),
            grounding_event_id=grounding_event_id,
            pre_state=pre_state,
            meta=dict(meta),
            user_id=user_id,
            allow_proactive=allow_proactive,
        )
        full: Dict[str, Any] = {
            "ok": True,
            "response": llm_reply,
            "reply": llm_reply,
            "user_message": text,
            "capture_id": capture_id,
            "context": context,
            "chat_mode": True,
            "human_authorized": True,
            "cognition_deferred": False,
            "intercepted": intercepted,
            "llm_reply_pristine": not intercepted,
            **self._interaction_api_fields(),
        }
        if chat_governance_notes:
            full["chat_governance_notes"] = list(chat_governance_notes)
        return self._finalize_interaction_result(full, user_id=user_id, meta=meta)

    def confirm_prepared_chat_turn(
        self,
        prepare_id: str,
        *,
        temperature: float = 0.7,
        llm_client: Any = None,
        llm_profile: Any = None,
        allow_proactive: bool = True,
        user_id: Optional[str] = None,
        send_mode: str = "with_injection",
    ) -> Dict[str, Any]:
        """Send an authorized prepared chat turn to the LLM."""
        self._purge_expired_chat_prepare()
        with self._chat_prepare_lock:
            bundle = self._chat_prepare_cache.pop(prepare_id, None)
        if not bundle:
            minutes = max(1, self._chat_prepare_ttl_seconds // 60)
            raise ValueError(
                f"授权预览已过期（有效期 {minutes} 分钟）。请重新输入消息并点击发送，生成新的授权预览后再确认。"
            )

        text = bundle["text"]
        meta = dict(bundle["meta"])
        chat_governance_notes = list(bundle["chat_governance_notes"])
        injection_skipped = send_mode == "user_only"

        if injection_skipped:
            context = ""
            governance_injection = ""
            chat_governance_notes.append(
                {
                    "stage": "authorization",
                    "action": "SKIP_INJECTION",
                    "reason": "user_only",
                }
            )
            _, messages = self._compose_chat_llm_messages(text, "", extra_system=None)
            meta["skip_injection"] = True
        else:
            context = bundle["context"]
            governance_injection = bundle["governance_injection"]
            messages = bundle["messages"]

        with runtime_write_context():
            result = self._execute_authorized_chat_turn(
                text,
                context=context,
                governance_injection=governance_injection,
                chat_governance_notes=chat_governance_notes,
                messages=messages,
                meta=meta,
                user_id=user_id,
                temperature=temperature,
                llm_client=llm_client,
                llm_profile=llm_profile,
                allow_proactive=allow_proactive,
                chat_mode=bool(bundle.get("chat_mode", True)),
            )
        result["send_mode"] = send_mode
        result["injection_skipped"] = injection_skipped
        result["full_cognitive_loop"] = bool(meta.get("full_cognitive_loop"))
        return result

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
        extra_system: Optional[str] = None,
    ) -> str:
        """LLM reply for HTTP /chat full loop; falls back to constrained draft."""
        if llm_client is None or llm_profile is None:
            return self._generate_constrained_response(user_input, context)
        system, messages = self._compose_chat_llm_messages(
            user_input,
            context,
            extra_system=extra_system,
        )
        from core.spine.emit import emit_execution_llm_call

        llm_ev = emit_execution_llm_call(
            caller="_generate_llm_response",
            model_hint=str(getattr(llm_profile, "model", "") or ""),
            input_chars=len(user_input) + len(context),
        )
        reply = llm_client.chat(llm_profile, messages, temperature=temperature)
        try:
            from core.runtime.trace_context import get_trace_id
            from core.spine.token.hooks import emit_tokens_for_llm_chars

            tid = (llm_ev.trace_id if llm_ev else None) or get_trace_id()
            if tid:
                emit_tokens_for_llm_chars(
                    tid,
                    spine_event_id=llm_ev.event_id if llm_ev else None,
                    input_chars=len(user_input) + len(context),
                    output_chars=len(reply or ""),
                    base_dir=str(self.base_dir),
                    caller="_generate_llm_response",
                )
        except Exception:
            pass
        return reply

    def _get_proactive_config(self) -> Dict[str, Any]:
        return dict(self.config.get("proactive") or {})

    def _apply_proactive_loop(
        self,
        reply: str,
        *,
        allow_proactive: bool = True,
        inject_into_reply: bool = True,
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        """Evaluate proactive intent trigger and optionally append suggestion to reply."""
        cfg = self._get_proactive_config()
        if not allow_proactive or not cfg.get("enabled", True):
            return reply, None

        threshold = float(
            cfg.get("min_motivation_threshold", PROACTIVE_MOTIVATION_THRESHOLD)
        )
        trigger: ProactiveTrigger = self.intent_engine.trigger_proactive(
            min_motivation=threshold,
            max_progress=float(cfg.get("max_progress", PROACTIVE_PROGRESS_CAP)),
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
        if inject_into_reply and cfg.get("inject_into_reply", True):
            if "主动" not in reply and len(reply) < 800 and trigger.suggested_action:
                final_reply = f"{reply}\n\n{trigger.suggested_action}"
        return final_reply, proactive_info

    def _interaction_attention_state(self) -> Dict[str, Any]:
        snapshot = self.memory_manager.get_attention_snapshot()
        if not snapshot:
            return {}
        block = self.attention_state_block
        if block is not None and hasattr(block, "recall_priority"):
            priority = int(block.recall_priority)
        else:
            priority = int(getattr(block, "priority", 4)) if block is not None else 4
        focus_scores = snapshot.get("focus_scores") or {}
        top_focus = snapshot.get("top_focus") or list(focus_scores.keys())[:3]
        recent_topics = [
            str(item).replace("_", " ")
            for item in top_focus[:5]
        ]
        return {
            "focus": " + ".join(str(item) for item in top_focus) or "balanced",
            "priority": priority,
            "focus_scores": focus_scores,
            "dynamic_field": {"recent_topics": recent_topics},
            "last_sync_turn": snapshot.get("last_sync_turn"),
        }

    def _infer_blocks_used(self, result: Dict[str, Any]) -> List[str]:
        labels: List[str] = []
        if result.get("emotion_state"):
            labels.append("emotion")
        if result.get("active_intent"):
            labels.append("intent")
        attention = result.get("attention_state") or {}
        if "user_profile" in (attention.get("focus_scores") or {}):
            labels.append("user_profile")
        if result.get("ok", True):
            labels.extend(["persona", "working_memory", "attention_state"])
        return sorted(set(labels))

    def _infer_episodic_layers(self, result: Dict[str, Any]) -> List[int]:
        layers: List[int] = []
        router = getattr(self, "router", None)
        if router is not None and hasattr(router, "get_stats"):
            sources = router.get_stats().get("sources") or {}
            if sources.get("block") or sources.get("memory_block"):
                layers.extend([1, 2])
            if set(sources.keys()) & {"vector", "graph", "storage", "episodic"}:
                layers.extend([3, 4, 5, 6, 7, 8])
        if not layers and result.get("context"):
            layers = [3, 5]
        return sorted(set(layers))

    def _build_interaction_provenance(
        self,
        result: Dict[str, Any],
        *,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        ok = bool(result.get("ok", True))
        cdg = result.get("cdg") or {}
        cdg_intercept = bool(cdg) and not cdg.get("approved", True)
        if ok and not cdg_intercept:
            values_check = "passed"
            revision_note = None
        else:
            values_check = "revised"
            revision_note = result.get("reason")

        trace_id = result.get("capture_id") or result.get("grounding_event_id")
        if not trace_id and user_id:
            trace_id = f"trace_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{user_id}"
        elif not trace_id:
            trace_id = f"trace_{uuid.uuid4().hex[:12]}"

        return {
            "trace_id": str(trace_id),
            "blocks_used": self._infer_blocks_used(result),
            "episodic_layers": self._infer_episodic_layers(result),
            "governance": {
                "values_check": values_check,
                "cdg_intercept": cdg_intercept,
                "revision_note": revision_note,
            },
            "timestamp": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        }

    def _finalize_interaction_result(
        self,
        result: Dict[str, Any],
        *,
        user_id: Optional[str],
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        result.setdefault("user_id", user_id)
        result.setdefault("session_id", meta.get("session_id"))
        result.setdefault("attention_state", self._interaction_attention_state())
        result.setdefault("reflection_triggered", False)
        result["provenance"] = self._build_interaction_provenance(result, user_id=user_id)
        self._trace_interaction_step(
            "complete",
            ok=bool(result.get("ok", True)),
            chat_mode=bool(result.get("chat_mode")),
            cognition_deferred=bool(result.get("cognition_deferred")),
        )
        if meta.get("persona_block"):
            sdk_meta = dict(result.get("meta") or {})
            sdk_meta["persona_block"] = meta["persona_block"]
            result["meta"] = sdk_meta
        return result

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

    def _should_delegate_to_ir(
        self,
        *,
        meta: Dict[str, Any],
        assistant_output: Optional[str],
        chat_mode: bool,
        llm_client: Any,
        llm_profile: Any,
    ) -> bool:
        if os.environ.get("CNEXUS_IR_DELEGATE", "0") not in ("1", "true", "yes"):
            return False
        if meta.get("ir_delegate") is False:
            return False
        if assistant_output is not None:
            return False
        if chat_mode:
            return True
        return llm_client is not None and llm_profile is not None

    def _process_interaction_via_ir(
        self,
        text: str,
        *,
        meta: Dict[str, Any],
        user_id: Optional[str],
        use_memory: bool,
        temperature: float,
        llm_client: Any,
        llm_profile: Any,
    ) -> Dict[str, Any]:
        from ir_kernel.facade import execute_chat_dag

        template = str(meta.get("ir_template") or "cognitive_chat_full")
        commit = bool(meta.get("ir_commit", True))
        session_meta = {
            k: meta[k]
            for k in ("session_id", "user_id", "model_id")
            if meta.get(k) is not None
        }
        ir_out = execute_chat_dag(
            self,
            text,
            template=template,
            use_memory=use_memory,
            llm_client=llm_client,
            llm_profile=llm_profile,
            temperature=temperature,
            commit=commit,
            session_meta=session_meta,
        )
        result: Dict[str, Any] = {
            "ok": bool(ir_out.get("ok")),
            "response": ir_out.get("reply") or "",
            "reply": ir_out.get("reply") or "",
            "trace_id": ir_out.get("trace_id"),
            "graph_id": ir_out.get("graph_id"),
            "outbound_preview": ir_out.get("outbound_preview") or "",
            "chat_mode": True,
            "ir_path": True,
            "ir_template": ir_out.get("template") or template,
            **self._interaction_api_fields(),
        }
        if ir_out.get("ir"):
            result["ir"] = ir_out["ir"]
        if ir_out.get("commit_results"):
            result["commit_results"] = ir_out["commit_results"]
        if not result["ok"]:
            result["reason"] = ir_out.get("error") or {"code": "IR_EXEC_FAILED"}
        return self._finalize_interaction_result(result, user_id=user_id, meta=meta)

    def process_interaction(
        self,
        user_input: str = "",
        *,
        message: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        assistant_output: Optional[str] = None,
        use_memory: bool = True,
        temperature: float = 0.7,
        llm_client: Any = None,
        llm_profile: Any = None,
        allow_proactive: bool = True,
        chat_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Subject Runtime Loop — experience → interpretation → self-update → prediction.
        When llm_client + llm_profile are provided and assistant_output is omitted,
        generates the reply via LLM before governance (HTTP /chat full loop).
        chat_mode: dialogue — capture and governance run on input; LLM reply is never modified.
        """
        text = (message or user_input or "").strip()
        if not text:
            raise ValueError("message or user_input is required")

        from core.runtime.trace_context import get_trace_id
        from core.spine.emit import emit_execution_chat

        emit_execution_chat(
            user_preview=text,
            mode="chat" if chat_mode else "interact",
            trace_id=get_trace_id(),
        )

        meta = dict(metadata or {})
        if user_id:
            meta.setdefault("user_id", user_id)
        if "enable_memory" in meta:
            use_memory = bool(meta["enable_memory"])
        if meta.get("persona_block"):
            meta.setdefault("persona_variant", meta["persona_block"])

        if (
            not chat_mode
            and llm_client is not None
            and llm_profile is not None
            and assistant_output is None
        ):
            chat_mode = True

        with runtime_write_context():
            if self._should_delegate_to_ir(
                meta=meta,
                assistant_output=assistant_output,
                chat_mode=chat_mode,
                llm_client=llm_client,
                llm_profile=llm_profile,
            ):
                return self._process_interaction_via_ir(
                    text,
                    meta=meta,
                    user_id=user_id,
                    use_memory=use_memory,
                    temperature=temperature,
                    llm_client=llm_client,
                    llm_profile=llm_profile,
                )
            return self._process_interaction_inner(
                text,
                meta=meta,
                user_id=user_id,
                use_memory=use_memory,
                temperature=temperature,
                llm_client=llm_client,
                llm_profile=llm_profile,
                allow_proactive=allow_proactive,
                assistant_output=assistant_output,
                chat_mode=chat_mode,
            )

    def _process_interaction_inner(
        self,
        text: str,
        *,
        meta: Dict[str, Any],
        user_id: Optional[str],
        use_memory: bool,
        temperature: float,
        llm_client: Any,
        llm_profile: Any,
        allow_proactive: bool,
        assistant_output: Optional[str],
        chat_mode: bool = False,
    ) -> Dict[str, Any]:
        grounding_event_id = self.cdg.ingest_user_action(text)
        pre_state = snapshot_cdg_state(self, user_input=text, grounding_event_id=grounding_event_id)
        self._trace_interaction_step("cdg_ingest", chat_mode=chat_mode)

        self._maybe_emit_working_self_shadow(text, importance=0.65, source="process_interaction")
        from core.spine.state.track import commit_runtime_state_diff, snapshot_runtime_tier_a

        _ws_before = snapshot_runtime_tier_a(self)
        self.working_self.update_from_input(text, self.dna_engine.dna, importance=0.65)
        commit_runtime_state_diff(self, _ws_before, label="chat_working_self")

        context = ""
        capture_id: Any = None
        chat_governance_notes: List[Dict[str, Any]] = []

        capture_id = self.capture("user", text, importance=0.65, **meta)
        capture_denied = isinstance(capture_id, str) and capture_id.startswith("denied")
        self._trace_interaction_step("capture_user", denied=capture_denied)
        if capture_denied and chat_mode:
            logger.info("Chat: capture denied (not intercepting): %s", capture_id)
            chat_governance_notes.append(
                {"stage": "capture", "action": "DENY", "reason": capture_id}
            )
        elif capture_denied:
            return self._finalize_interaction_result(
                {
                    "ok": False,
                    "reason": capture_id,
                    **self._interaction_api_fields(),
                },
                user_id=user_id,
                meta=meta,
            )

        if use_memory:
            prefetch = meta.get("recall_prefetch")
            if isinstance(prefetch, str) and prefetch.strip():
                context = prefetch
            else:
                recall_k = int(self.config.get("chat_recall_top_k", 6)) if chat_mode else None
                context = self.recall(text, top_k=recall_k, mutate_state=True)
        else:
            context = ""
        if chat_mode and context:
            max_ctx = int(self.config.get("chat_max_context_chars", 4000))
            if len(context) > max_ctx:
                context = context[:max_ctx] + "\n…"
        self._trace_interaction_step("recall_context", chars=len(context), use_memory=use_memory)
        llm_reply: Optional[str] = None
        governance_injection = ""
        if chat_mode and assistant_output is None:
            governance_injection = self._build_chat_governance_injection(
                text, chat_governance_notes, persist_alignment=True
            )

        if assistant_output is not None:
            response = assistant_output
        else:
            response = self._generate_llm_response(
                text,
                context,
                temperature=temperature,
                llm_client=llm_client,
                llm_profile=llm_profile,
                extra_system=governance_injection or None,
            )
            llm_reply = response
        self._trace_interaction_step(
            "llm_infer",
            has_client=llm_client is not None,
            has_profile=llm_profile is not None,
            assistant_prefilled=assistant_output is not None,
        )

        gov_pre = self.governance_pipeline.check_output(
            response, self.working_self, self.dna_engine.dna
        )
        intercepted = False
        if chat_mode and llm_reply is not None:
            llm_reply, intercepted = self._maybe_intercept_chat_reply(
                gov_pre, llm_reply, chat_governance_notes
            )
            response = llm_reply
        elif not gov_pre.approved:
            safe_response = gov_pre.safe_text or self.governance_pipeline.safe_fallback(
                gov_pre.reason, response
            )
            return self._finalize_interaction_result(
                {
                    "ok": False,
                    "reason": gov_pre.reason,
                    "context": context,
                    "response": safe_response,
                    "reply": safe_response,
                    "governance_decision": gov_pre.to_dict(),
                    "working_self": self.working_self.to_dict(),
                    "self_model": self.self_model.to_dict(),
                    **self._interaction_api_fields(),
                },
                user_id=user_id,
                meta=meta,
            )

        chat_defer = (
            chat_mode
            and llm_reply is not None
            and self.config.get("chat_defer_cognition", True)
            and not meta.get("full_cognitive_loop")
        )
        if chat_defer:
            quick: Dict[str, Any] = {
                "ok": True,
                "response": llm_reply,
                "reply": llm_reply,
                "capture_id": capture_id,
                "context": context,
                "chat_mode": True,
                "intercepted": intercepted,
                "llm_reply_pristine": not intercepted,
                "cognition_deferred": True,
                **self._interaction_api_fields(),
            }
            if governance_injection:
                quick["governance_injection_chars"] = len(governance_injection)
            if chat_governance_notes:
                quick["chat_governance_notes"] = list(chat_governance_notes)
            if not gov_pre.approved:
                quick["governance_decision"] = gov_pre.to_dict()

            self._schedule_chat_deferred_cognition(
                lambda: self._finish_chat_cognition_background(
                    text=text,
                    response=response,
                    llm_reply=llm_reply,
                    context=context,
                    capture_id=capture_id,
                    chat_governance_notes=list(chat_governance_notes),
                    grounding_event_id=grounding_event_id,
                    pre_state=pre_state,
                    meta=dict(meta),
                    user_id=user_id,
                    allow_proactive=allow_proactive,
                )
            )
            self._trace_interaction_step("cognition_deferred")
            return self._finalize_interaction_result(quick, user_id=user_id, meta=meta)

        pred_ckpt = self._predictive_checkpoint()
        error = self.predictive.predict_and_update(
            text, response, self.working_self, self.self_model
        )
        reflection = f"本次交互预测误差 {error:.2f}，"
        reflection += "触发自我校正。" if error > 0.4 else "维持稳定性身份。"

        value_alignment = self.intent_engine.check_value_alignment(self.values_governance)
        value_alignment_payload = (
            value_alignment.model_dump(mode="json") if value_alignment else None
        )

        values_mode = str((self.config.get("governance") or {}).get("values_mode", "OBSERVE"))
        values_decision = self.governance_pipeline.apply_values_enforcement(
            values_mode, response, value_alignment
        )
        if values_decision.action == "BLOCK":
            if chat_mode:
                logger.info("Chat: values block noted (not intercepting): %s", values_decision.reason)
                chat_governance_notes.append(
                    {
                        "stage": "values",
                        "action": "BLOCK",
                        "reason": values_decision.reason,
                        "decision": values_decision.to_dict(),
                    }
                )
            else:
                safe = values_decision.safe_text or response
                return self._finalize_interaction_result(
                    {
                        "ok": False,
                        "reason": values_decision.reason,
                        "response": safe,
                        "reply": safe,
                        "governance_decision": values_decision.to_dict(),
                        "value_alignment": value_alignment_payload,
                        **self._interaction_api_fields(),
                    },
                    user_id=user_id,
                    meta=meta,
                )
        if values_decision.action == "REWRITE" and values_decision.safe_text:
            if chat_mode:
                chat_governance_notes.append(
                    {
                        "stage": "values",
                        "action": "REWRITE",
                        "reason": values_decision.reason,
                        "decision": values_decision.to_dict(),
                    }
                )
            else:
                response = values_decision.safe_text

        capture_ids = [capture_id] if isinstance(capture_id, str) and not capture_id.startswith("denied") else []
        proposed_state = snapshot_cdg_state(
            self,
            user_input=text,
            response=response,
            capture_ids=capture_ids,
            grounding_event_id=grounding_event_id,
        )
        cdg_result = self._run_cdg_cycle(pre_state, proposed_state, phase="interaction")
        if not cdg_result.get("approved", True):
            if chat_mode:
                logger.info(
                    "Chat: CDG note (not intercepting): %s",
                    cdg_result.get("reason"),
                )
                chat_governance_notes.append(
                    {
                        "stage": "cdg",
                        "action": "BLOCK",
                        "reason": cdg_result.get("reason"),
                        "decision": cdg_result,
                    }
                )
            else:
                self._restore_predictive_checkpoint(pred_ckpt)
                safe_response = (
                    cdg_result.get("safe_response")
                    or self.governance_pipeline.safe_fallback(
                        str(cdg_result.get("reason") or "cdg_blocked"), response
                    )
                )
                return self._finalize_interaction_result(
                    {
                        "ok": False,
                        "reason": cdg_result.get("reason"),
                        "response": safe_response,
                        "reply": safe_response,
                        "cdg": cdg_result,
                        "governance_decision": {
                            "action": "REWRITE",
                            "reason": cdg_result.get("reason"),
                            "safe_text": safe_response,
                            "cdg": cdg_result,
                        },
                        "rcs": cdg_result.get("rcs"),
                        "working_self": self.working_self.to_dict(),
                        "self_model": self.self_model.to_dict(),
                        "reflection_triggered": False,
                        **self._interaction_api_fields(cdg_result),
                    },
                    user_id=user_id,
                    meta=meta,
                )

        integration, meta_reflection_payload, reflection_triggered = (
            self._apply_post_cdg_interaction_updates(
                text=text,
                response=response,
                reflection=reflection,
                error=error,
                context=context,
                chat_mode=chat_mode,
            )
        )

        self.working_self.update_prediction_error()
        self.working_self.add_reflection(reflection)
        self.deliberation.regulate_homeostasis(self.working_self)
        self.working_self.sync_to_legacy(self.state)

        post_snap = snapshot_cdg_state(
            self,
            user_input=text,
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

        final_reply, proactive_info = self._apply_proactive_loop(
            response,
            allow_proactive=allow_proactive,
            inject_into_reply=not chat_mode,
        )
        if chat_mode and llm_reply is not None:
            final_reply = llm_reply

        gov = self.run_governance_cycle()
        assistant_capture_text = llm_reply if llm_reply is not None else final_reply
        assistant_capture_id = self.capture(
            "assistant", assistant_capture_text, importance=0.55, **meta
        )

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
            "meta_reflection": meta_reflection_payload,
            "value_alignment": value_alignment_payload,
            "proactive": proactive_info,
            "governance": gov.get("stability_metrics"),
            "cdg": cdg_result,
            "rcs": cdg_result.get("rcs"),
            "potential_v": cdg_result.get("potential_v"),
            "control_phase": cdg_result.get("control_phase"),
            "d_v": cdg_result.get("d_v"),
            "interventions": cdg_result.get("interventions", []),
            "user_id": user_id,
            "session_id": meta.get("session_id"),
            "attention_state": self._interaction_attention_state(),
            "reflection_triggered": reflection_triggered,
            **self._interaction_api_fields(cdg_result),
        }
        if chat_mode:
            result["chat_mode"] = True
            result["intercepted"] = False
            result["llm_reply_pristine"] = True
            if governance_injection:
                result["governance_injection_chars"] = len(governance_injection)
            if not gov_pre.approved:
                result["governance_decision"] = gov_pre.to_dict()
            if chat_governance_notes:
                result["chat_governance_notes"] = chat_governance_notes
        if gtbs_shadow is not None:
            result["gtbs_shadow"] = gtbs_shadow
        return self._finalize_interaction_result(result, user_id=user_id, meta=meta)

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
        with runtime_write_context():
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
        with runtime_write_context():
            from core.governance.gtbs.adapters.governance_adapter import (
                maybe_emit_governance_cycle_shadow,
            )

            self.belief_engine.decay_confidence()
            recent = self.cdg.reality_bus.window(1)
            grounding_event_id = recent[-1].event_id if recent else None
            pre_state = snapshot_cdg_state(self, grounding_event_id=grounding_event_id)
            maybe_emit_governance_cycle_shadow(
                self,
                phase="background",
                pre_state=pre_state,
            )
            proposed_state = snapshot_cdg_state(self, grounding_event_id=grounding_event_id)
            cdg_snapshot = self._run_cdg_cycle(pre_state, proposed_state, phase="background")
            result = self.stability.run_governance_cycle()
            result["cdg"] = cdg_snapshot
            result["cdg_trajectory"] = self.cdg.trajectory_report()
            result["goal_layer"] = self.goal_manager.reconcile_governance(self.values_governance)
            if self.goal_manager.cse_mode in ("batch", "idle"):
                self.goal_manager.flush_synthesis()
            if self.config.get("enable_metabolic", True):
                result["memory_maintenance"] = self.maintain_memory()
        self._last_governance_at = datetime.now().isoformat()
        return result

    def process_capture_cognition(
        self,
        content: str,
        *,
        layer: str = "episodic",
        memory_id: Optional[str] = None,
        trigger_governance: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Post-import cognition — reflection pipeline with optional governance."""
        snippet = (content or "").strip()
        if not snippet:
            return {"skipped": True, "reason": "empty_content"}

        should_govern = (
            trigger_governance
            if trigger_governance is not None
            else bool(self.config.get("capture_cognize_default", True))
        )
        record = self.trait_based_reflection(
            snippet[:800],
            traits=None,
            trigger_governance=should_govern,
        )
        return {
            "reflection_id": record.reflection_id,
            "traits": list(record.traits),
            "trigger_governance": should_govern,
            "memory_id": memory_id,
            "layer": layer,
        }

    def memory_stats(self) -> Dict[str, Any]:
        return self._lifecycle.collect_stats().to_dict()

    def run_memory_maintenance(self, *, force: bool = False) -> Dict[str, Any]:
        """Metabolic cycle — block + episodic decay, forget, compression."""
        if not self.config.get("enable_metabolic", True) and not force:
            return {"skipped": True, "reason": "enable_metabolic=false"}
        with runtime_write_context():
            return self.memory_manager.run_maintenance(force=force)

    def maintain_memory(self, *, force: bool = False) -> Dict[str, Any]:
        """Block lifecycle + episodic maintenance + sleep-time consolidation."""
        if not self.config.get("enable_metabolic", True) and not force:
            return {"skipped": True, "reason": "enable_metabolic=false"}

        with runtime_write_context():
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

        with runtime_write_context():
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
        """后台治理循环 — never block the API event loop."""
        import asyncio

        while True:
            try:
                await asyncio.to_thread(self.run_governance_cycle)
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
        state = {
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
                "pending_reviews": self.reflection_pipeline.count_due_reviews(),
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
            "metrics": get_metrics().snapshot(),
            "last_recall_explain": getattr(self.recall_pipeline, "last_explain", {}),
            "governance_loop": {
                "background_enabled": bool(self.config.get("governance_background_enabled", True)),
                "interval_seconds": int(self.config.get("governance_interval_seconds", 3600)),
                "last_run_at": self._last_governance_at,
            },
        }
        state["goal_layer"] = self.goal_manager.observe_governance(self.values_governance)
        state["mind_overview"] = build_mind_overview(self, state)
        return state

    def get_control_plane_snapshot(self) -> Dict[str, Any]:
        """Fast read for health / WS / boot — no mind_overview, no governance side-effects."""
        from core.runtime.boot_protocol import get_boot_phase, BootPhase

        dna_metrics = self.dna_engine.get_stability_metrics()
        state_metrics = self.state.get_stability_metrics()
        return {
            "boot_phase": get_boot_phase().value,
            "runtime_mode": self.runtime_mode,
            "cognitive_state": self.state.get_full_state(),
            "working_memory_count": len(self.attention.working_memory_snapshot()),
            "stability_metrics": {
                **state_metrics,
                **dna_metrics,
                "overall_stability_score": dna_metrics.get("overall_stability", 0.85),
            },
            "reflective": {
                "active_count": len(self.reflection_pipeline.get_active_reflections()),
                "pending_reviews": self.reflection_pipeline.count_due_reviews(),
            },
            "governance_loop": {
                "background_enabled": bool(self.config.get("governance_background_enabled", True)),
                "interval_seconds": int(self.config.get("governance_interval_seconds", 3600)),
                "last_run_at": self._last_governance_at,
            },
            "timestamp": datetime.now().isoformat(),
            "control_plane": True,
        }

    def run_cognitive_warmup(self) -> None:
        """Detached cognitive warmup — L3 tick-driven (never on control-plane path)."""
        from core.runtime.boot_protocol import cognitive_disabled, mark_cognitive_warmup_done
        from core.runtime.cognitive_warmup_adapter import run_cognitive_warmup_ticks

        if cognitive_disabled():
            mark_cognitive_warmup_done(bypass_causal=True)
            return
        try:
            run_cognitive_warmup_ticks(self)
        except Exception as exc:
            logger.warning("Cognitive warmup failed — holding BOOT_3: %s", exc)

    def get_full_status(self) -> Dict[str, Any]:
        """全层状态摘要 — 供 UI / Agent / 监控使用"""
        state = self.get_current_state()
        return {
            "version": "1.0.0-g1",
            "layers": {
                "storage": {"base_dir": self.base_dir},
                "memory_blocks": self.memory_manager.block_stats(),
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

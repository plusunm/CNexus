import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.config_loader import ConfigLoader
from core.embedding import EmbeddingService
from core.governance.coordinator import StabilityCoordinator
from core.governance.safety.policy_engine import GovernancePolicyEngine
from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder
from core.validation.validation_orchestrator import StabilityValidationOrchestrator
from memory.filter import CaptureFilter
from memory.schema import Memory
from runtime.attention import DynamicAttentionField
from runtime.context import ContextAssemblyEngine
from runtime.router import HierarchicalRecallRouter
from runtime.state import CognitiveStateManager
from storage.manager import UnifiedStorageManager


class BrainMemoryRuntime:
    """Brain-Memory v5.0 — Persistent Cognitive Runtime for AI Agents"""

    def __init__(
        self,
        config_path: str = "config/default.json",
        base_dir: str = "memory",
        project_root: Optional[str] = None,
    ):
        self.project_root = Path(project_root or Path.cwd())
        config_dir = self.project_root / "config" if not Path(config_path).is_absolute() else Path(config_path).parent
        self.config = ConfigLoader(str(config_dir))
        cfg = self.config.config

        self.base_dir = str(self.project_root / base_dir)
        self.embedder = EmbeddingService(
            host=cfg.get("ollama_host", "http://localhost:11434"),
            model=cfg.get("embedding_model", "nomic-embed-text"),
            vector_dim=cfg.get("vector_dim", 768),
        )

        self.storage = UnifiedStorageManager(
            base_dir=self.base_dir,
            vector_dim=cfg.get("vector_dim", 768),
        )
        self.storage.set_embedder(self.embedder)

        self.router = HierarchicalRecallRouter(self.storage)
        self.attention = DynamicAttentionField()
        self.context_engine = ContextAssemblyEngine(self.attention)
        self.state = CognitiveStateManager()

        self.dna_engine = PersonalityDNAEngine()
        self.narrative = NarrativeBuilder(self.dna_engine)
        self.belief_engine = BeliefEngine(self.dna_engine, self.narrative)

        self.stability = StabilityCoordinator(self.dna_engine, self.narrative, self.belief_engine)
        self.policy = GovernancePolicyEngine()
        self.validation = StabilityValidationOrchestrator(self)

        self.recall_top_k = cfg.get("recall_top_k", 12)

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

        memory_id = str(uuid.uuid4())
        memory = Memory(
            memory_id=memory_id,
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

        return mid

    def recall(self, query: str, top_k: Optional[int] = None) -> str:
        top_k = top_k or self.recall_top_k
        recall_results = self.router.hybrid_recall(query, top_k=top_k)

        wm_scores = [m.get("attention_score", 0.5) for m in self.attention.working_memory_snapshot()]
        if wm_scores:
            self.state.calculate_attention_entropy(wm_scores)
        self.state.update_cognitive_load(0.65 if len(recall_results) > 5 else 0.3)

        context = self.context_engine.assemble(query, recall_results)
        identity_anchor = self.narrative.generate_identity_anchor()
        identity_block = (
            f"【Identity Context】\n"
            f"• {self.narrative.get_current_narrative_summary()}"
        )
        return f"{identity_anchor}\n\n{identity_block}\n\n{context}"

    def run_governance_cycle(self) -> Dict[str, Any]:
        self.belief_engine.decay_confidence()
        return self.stability.run_governance_cycle()

    def run_validation_suite(self, days: int = 90) -> Dict[str, Any]:
        return self.validation.run_full_validation_suite(simulation_days=days)

    def run_background_governance(self):
        """Placeholder for periodic governance — call run_governance_cycle() in a scheduler."""
        return self.run_governance_cycle()

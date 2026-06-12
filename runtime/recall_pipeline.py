"""RecallPipeline — single recall entry for BrainMemoryRuntime."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


class RecallPipeline:
    """
    Unified recall chain (delegates to runtime engines, single facade):
      1. Hierarchical / cognitive recall
      2. Attention competition
      3. Context assembly + personality blocks
    """

    def __init__(self, runtime: "BrainMemoryRuntime"):
        self.runtime = runtime

    def recall(
        self,
        query: str,
        *,
        top_k: Optional[int] = None,
        use_memory: bool = True,
    ) -> str:
        if not use_memory or not (query or "").strip():
            return ""

        rt = self.runtime
        k = top_k or rt.recall_top_k

        if rt.runtime_mode == "g2":
            recall_results = rt.recall_engine.activate(
                query, rt.working_self, rt.dna_engine.dna, top_k=k
            )
        else:
            recall_results = rt.router.hybrid_recall(query, top_k=k)

        activated = rt.attention.attention_competition(recall_results, query)
        rt.state.sync_from_attention(activated)
        rt.working_self.sync_to_legacy(rt.state)
        rt._sync_attention_snapshot()

        context = rt.context_engine.assemble(
            query, recall_results, memory_manager=rt.memory_manager
        )
        emotion_context = rt.emotion_engine.format_context_block()
        intent_context = rt.intent_engine.format_context_block()
        reflective_context = rt.reflective_engine.format_context_block(limit=2)
        values_context = rt.values_governance.format_context_block(limit=2)
        identity_anchor = rt.narrative.generate_identity_anchor()
        self_block = rt.self_model.to_prompt_block()
        state_block = (
            f"【Working Self】\n"
            f"• goal_focus={rt.working_self.goal_focus} "
            f"coherence={rt.working_self.cumulative_coherence:.2f} "
            f"prediction_error={rt.working_self.prediction_error:.2f}"
        )
        identity_block = (
            f"【Identity Context】\n"
            f"• {rt.narrative.get_current_narrative_summary()}"
        )
        return (
            f"{identity_anchor}\n\n{self_block}\n\n{state_block}\n\n"
            f"{emotion_context}\n\n{intent_context}\n\n{reflective_context}\n\n"
            f"{values_context}\n\n"
            f"{identity_block}\n\n{context}"
        )

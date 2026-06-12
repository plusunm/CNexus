"""RecallPipeline — single recall entry for BrainMemoryRuntime."""

from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


class RecallPipeline:
    """
    Unified recall chain:
      1. Hierarchical / cognitive recall
      2. Attention competition + score boost (P3-A)
      3. Context assembly + personality blocks
    """

    def __init__(self, runtime: "BrainMemoryRuntime"):
        self.runtime = runtime
        self.last_explain: Dict[str, Any] = {}

    def recall(
        self,
        query: str,
        *,
        top_k: Optional[int] = None,
        use_memory: bool = True,
        use_attention: bool = True,
    ) -> str:
        if not use_memory or not (query or "").strip():
            self.last_explain = {"query": query, "skipped": True}
            return ""

        from core.observability.metrics import get_metrics, timed

        rt = self.runtime
        k = top_k or rt.recall_top_k

        with timed("recall.total"):
            if rt.runtime_mode == "g2":
                recall_results: List[Dict[str, Any]] = rt.recall_engine.activate(
                    query, rt.working_self, rt.dna_engine.dna, top_k=k
                )
            else:
                recall_results = rt.router.hybrid_recall(query, top_k=k)

            if use_attention:
                activated = rt.attention.attention_competition(recall_results, query)
                recall_results = self._apply_attention_ranking(recall_results, query)
            else:
                activated = recall_results[:k]

            rt.state.sync_from_attention(activated if use_attention else [])
            rt.working_self.sync_to_legacy(rt.state)
            if use_attention:
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
            full = (
                f"{identity_anchor}\n\n{self_block}\n\n{state_block}\n\n"
                f"{emotion_context}\n\n{intent_context}\n\n{reflective_context}\n\n"
                f"{values_context}\n\n"
                f"{identity_block}\n\n{context}"
            )

        self.last_explain = {
            "query": query[:120],
            "use_attention": use_attention,
            "top_k": k,
            "candidate_count": len(recall_results),
            "top_labels": [
                r.get("_label") or r.get("label") or r.get("_layer")
                for r in recall_results[:5]
            ],
            "attention_focus": rt.attention.focus_scores_by_label() if use_attention else {},
            "ranking": [
                {
                    "label": r.get("_label") or r.get("label"),
                    "score": r.get("_final_score") or r.get("_cognitive_score"),
                    "attention_boost": r.get("_attention_boost"),
                }
                for r in recall_results[:5]
            ],
            "context_chars": len(full),
        }
        get_metrics().set_gauge("recall.context_chars", float(len(full)))
        return full

    def _apply_attention_ranking(
        self,
        recall_results: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """Boost recall scores using attention focus — makes attention affect ranking."""
        focus = self.runtime.attention.focus_scores_by_label()
        for item in recall_results:
            label = item.get("_label") or item.get("label") or item.get("_layer") or ""
            attn = float(item.get("attention_score", 0.0))
            focus_boost = float(focus.get(label, 0.0))
            combined_boost = min(1.0, focus_boost * 0.65 + attn * 0.35)
            base = (
                item.get("_cognitive_score")
                or item.get("_final_score")
                or item.get("_hybrid_score")
                or 0.5
            )
            item["_attention_boost"] = round(combined_boost, 4)
            item["_final_score"] = round(float(base) * (1.0 + combined_boost * 0.55), 5)

        recall_results.sort(
            key=lambda x: float(x.get("_final_score") or x.get("_cognitive_score") or 0.0),
            reverse=True,
        )
        return recall_results

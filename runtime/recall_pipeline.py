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
        mutate_state: bool = False,
    ) -> str:
        if not use_memory or not (query or "").strip():
            self.last_explain = {"query": query, "skipped": True}
            return ""

        from core.observability.metrics import get_metrics, timed

        rt = self.runtime
        k = top_k or rt.recall_top_k

        get_bus = getattr(rt, "_get_write_intent_bus", None)
        if callable(get_bus):
            try:
                get_bus()
            except Exception:
                pass

        with timed("recall.total"):
            if rt.runtime_mode == "g2":
                recall_results: List[Dict[str, Any]] = rt.recall_engine.activate(
                    query, rt.working_self, rt.dna_engine.dna, top_k=k
                )
            else:
                recall_results = rt.router.hybrid_recall(query, top_k=k)

            recall_results = self._apply_goal_ranking(recall_results, query)
            recall_results = self._apply_sigma_ranking(recall_results)

            if use_attention:
                activated = rt.attention.attention_competition(recall_results, query)
                recall_results = self._apply_attention_ranking(recall_results, query)
            else:
                activated = recall_results[:k]

            from core.spine.emit import emit_execution_recall

            exec_ev = emit_execution_recall(
                query=query,
                top_k=k,
                mutate_state=mutate_state,
                result_count=len(recall_results),
            )
            recall_event_id = exec_ev.event_id if exec_ev else None

            if mutate_state:
                from core.governance.gtbs.adapters.recall_adapter import (
                    maybe_emit_recall_side_effect,
                )
                from core.spine.state.track import (
                    commit_runtime_state_diff,
                    snapshot_runtime_tier_a,
                )

                before = snapshot_runtime_tier_a(rt)
                maybe_emit_recall_side_effect(
                    rt,
                    query=query,
                    top_k=k,
                    use_attention=use_attention,
                    activated=activated if use_attention else [],
                    recall_results=recall_results,
                )
                rt.state.sync_from_attention(activated if use_attention else [])
                rt.working_self.sync_to_legacy(rt.state)
                if use_attention:
                    rt._sync_attention_snapshot()
                commit_runtime_state_diff(
                    rt, before, label="recall_mutate_state", triggered_by=recall_event_id
                )

            context = rt.context_engine.assemble(
                query, recall_results, memory_manager=rt.memory_manager
            )
            emotion_context = rt.emotion_engine.format_context_block()
            intent_context = rt.intent_engine.format_context_block()
            reflective_context = rt.reflective_engine.format_context_block(limit=2)
            values_context = rt.values_governance.format_context_block(limit=2)
            identity_anchor = rt.narrative.generate_identity_anchor()
            self_block = rt.self_model.to_prompt_block()
            from core.personality.narrative.recent_context import load_recent_narrative_prompt_block

            recent_narrative_block = load_recent_narrative_prompt_block(
                str(getattr(rt, "base_dir", "") or ""),
                since_hours=24.0,
                limit=12,
            )
            state_block = (
                f"【Working Self】\n"
                f"• goal_focus={rt.working_self.goal_focus} "
                f"coherence={rt.working_self.cumulative_coherence:.2f} "
                f"prediction_error={rt.working_self.prediction_error:.2f}"
            )
            identity_block = (
                f"【Identity Context — long-term narrative self】\n"
                f"• {rt.narrative.get_current_narrative_summary()}"
            )
            recent_section = f"{recent_narrative_block}\n\n" if recent_narrative_block else ""
            full = (
                f"{identity_anchor}\n\n{self_block}\n\n{state_block}\n\n"
                f"{emotion_context}\n\n{intent_context}\n\n{reflective_context}\n\n"
                f"{values_context}\n\n"
                f"{recent_section}"
                f"{identity_block}\n\n{context}"
            )

        self.last_explain = {
            "query": query[:120],
            "use_attention": use_attention,
            "mutate_state": mutate_state,
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
            "recent_narrative_chars": len(recent_narrative_block),
            "recent_narrative_present": bool(recent_narrative_block),
        }
        get_metrics().set_gauge("recall.context_chars", float(len(full)))
        return full

    def _apply_goal_ranking(
        self,
        recall_results: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """Boost recall items aligned with the top active goal."""
        boost = self.runtime.goal_manager.motivation_boost()
        goals = self.runtime.goal_manager.active_goals(top_k=1)
        if boost <= 0 or not goals:
            return recall_results

        goal_text = (goals[0].description or "").lower()
        query_lower = (query or "").lower()
        tokens = [
            token
            for token in goal_text.replace("，", " ").replace("。", " ").split()
            if len(token) >= 2
        ][:10]

        for item in recall_results:
            label = (item.get("_label") or item.get("label") or item.get("_layer") or "").lower()
            content = (item.get("content") or item.get("text") or "").lower()
            aligned = label == "intent" or any(token in content or token in query_lower for token in tokens)
            if not aligned:
                continue
            base = (
                item.get("_final_score")
                or item.get("_cognitive_score")
                or item.get("_hybrid_score")
                or 0.5
            )
            item["_goal_boost"] = round(boost, 4)
            item["_final_score"] = round(float(base) * (1.0 + boost), 5)

        recall_results.sort(
            key=lambda x: float(x.get("_final_score") or x.get("_cognitive_score") or 0.0),
            reverse=True,
        )
        return recall_results

    def _apply_sigma_ranking(self, recall_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Layer 4 — boost blocks with persisted Σ.M metadata (importance_snapshot)."""
        mm = getattr(self.runtime, "memory_manager", None)
        if mm is None:
            return recall_results
        blocks = mm.blocks.list_blocks(active_only=True)
        sigma_importance: Dict[str, float] = {}
        for block in blocks:
            meta = block.metadata or {}
            if meta.get("sigma_slot") != "Σ.M":
                continue
            snap = meta.get("block_importance_snapshot", block.importance)
            sigma_importance[block.label] = float(snap)

        if not sigma_importance:
            return recall_results

        for item in recall_results:
            label = item.get("_label") or item.get("label") or item.get("_layer") or ""
            snap = sigma_importance.get(label)
            if snap is None:
                continue
            base = (
                item.get("_final_score")
                or item.get("_cognitive_score")
                or item.get("_hybrid_score")
                or 0.5
            )
            item["_sigma_boost"] = round(snap * 0.15, 4)
            item["_final_score"] = round(float(base) * (1.0 + snap * 0.15), 5)

        recall_results.sort(
            key=lambda x: float(x.get("_final_score") or x.get("_cognitive_score") or 0.0),
            reverse=True,
        )
        return recall_results

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

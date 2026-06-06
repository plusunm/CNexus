"""G2 — Cognitive Recall: state-conditioned activation + spreading activation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.personality.dna_schema import PersonalityDNA
    from runtime.cognitive_state import PersistentCognitiveState
    from runtime.router import HierarchicalRecallRouter
    from storage.manager import UnifiedStorageManager


class CognitiveRecallEngine:
    """
    Memory is State, Retrieval is Cognition.

    Pipeline: hierarchical seed recall → graph spreading activation →
    state/DNA-conditioned rescore → narrative causality boost.
    """

    LAYER_CAUSALITY = {
        "identity": 1.0,
        "goal": 0.92,
        "belief": 0.88,
        "relationship": 0.85,
        "narrative": 0.8,
        "semantic": 0.65,
        "episodic": 0.5,
    }

    def __init__(
        self,
        storage: "UnifiedStorageManager",
        router: "HierarchicalRecallRouter",
        spread_hops: int = 2,
        spread_limit: int = 8,
    ):
        self.storage = storage
        self.router = router
        self.spread_hops = spread_hops
        self.spread_limit = spread_limit

    def activate(
        self,
        query: str,
        state: "PersistentCognitiveState",
        dna: "PersonalityDNA",
        top_k: int = 12,
    ) -> List[Dict[str, Any]]:
        seeds = self.router.hybrid_recall(query, top_k=max(top_k * 2, 20))
        spread = self._spreading_activation(seeds[:4])
        merged = self._merge_results(seeds, spread)
        scored = [self._score_memory(m, state, dna) for m in merged]
        scored.sort(key=lambda x: x.get("_cognitive_score", 0.0), reverse=True)
        return scored[:top_k]

    def _spreading_activation(self, seeds: List[Dict]) -> List[Dict]:
        graph = self.storage.graph
        if not hasattr(graph, "find_related_memories"):
            return []

        activated: List[Dict] = []
        seen = set()
        for seed in seeds:
            mid = seed.get("memory_id") or seed.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            try:
                related = graph.find_related_memories(
                    mid, max_hops=self.spread_hops, limit=self.spread_limit
                )
            except Exception:
                continue
            for row in related:
                rid = row.get("id")
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                activated.append(
                    {
                        "memory_id": rid,
                        "content": row.get("content", ""),
                        "layer": row.get("layer", "semantic"),
                        "importance": float(row.get("importance", 0.55)),
                        "_spread_from": mid,
                        "_spread_weight": float(row.get("path_weight", 0.5)),
                        "_distance": 1.0 - float(row.get("path_weight", 0.5)),
                    }
                )
        return activated

    def _merge_results(self, primary: List[Dict], spread: List[Dict]) -> List[Dict]:
        merged: Dict[str, Dict] = {}
        for item in primary + spread:
            mid = item.get("memory_id") or item.get("id")
            if not mid:
                continue
            if mid not in merged:
                merged[mid] = dict(item)
            else:
                merged[mid]["_spread_weight"] = max(
                    merged[mid].get("_spread_weight", 0.0),
                    item.get("_spread_weight", 0.0),
                )
        return list(merged.values())

    def _score_memory(
        self,
        mem: Dict[str, Any],
        state: "PersistentCognitiveState",
        dna: "PersonalityDNA",
    ) -> Dict[str, Any]:
        score = mem.get("_final_score") or mem.get("_hybrid_score", 0.5)
        layer = mem.get("layer") or mem.get("_layer", "episodic")
        tags = mem.get("tags") or []

        if state.goal_focus in tags or state.goal_focus == layer:
            score *= 1.6
        if state.identity_threat > 0.5 and layer in ("identity", "belief", "goal"):
            score *= 1.8
        rel = mem.get("relation_score", state.relationship_tone)
        if abs(state.relationship_tone - float(rel)) < 0.2:
            score *= 1.35

        score += self.LAYER_CAUSALITY.get(layer, 0.4) * 0.12 * state.cumulative_coherence

        if dna.openness > 0.7:
            score += float(mem.get("novelty", mem.get("emotional_weight", 0.0))) * 0.25
        if dna.self_consistency > 0.85 and layer in ("identity", "belief"):
            score *= 1.1

        spread_w = mem.get("_spread_weight", 0.0)
        if spread_w > 0:
            score += spread_w * 0.35

        mem["_cognitive_score"] = round(score, 5)
        return mem

    def build_context(self, activated: List[Dict], query: str) -> str:
        return self.router.inject_context(activated)

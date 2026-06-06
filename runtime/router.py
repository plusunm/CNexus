from typing import Any, Dict, List

from storage.manager import UnifiedStorageManager


class HierarchicalRecallRouter:
    """
    Hierarchical Recall Router — 持久认知激活核心
    严格优先级：Identity > Goal > Belief > Relationship > Narrative > Semantic > Episodic > Working
    """

    LAYER_PRIORITY = {
        "identity": 1.0,
        "goal": 0.9,
        "belief": 0.85,
        "relationship": 0.8,
        "narrative": 0.75,
        "semantic": 0.6,
        "episodic": 0.45,
        "working": 0.9,
    }

    def __init__(self, storage: UnifiedStorageManager):
        self.storage = storage

    def detect_intent(self, query: str) -> Dict[str, float]:
        q = query.lower()
        intent_scores = {
            "identity": 0.0,
            "goal": 0.0,
            "belief": 0.0,
            "relationship": 0.0,
            "narrative": 0.0,
            "semantic": 0.0,
        }

        if any(k in q for k in ["我是谁", "你是谁", "我的性格", "我的风格", "identity", "personality", "自我"]):
            intent_scores["identity"] = 1.0

        if any(k in q for k in ["目标", "计划", "想要", "希望", "goal", "plan", "长期"]):
            intent_scores["goal"] = 0.95

        if any(k in q for k in ["相信", "认为", "价值观", "原则", "belief", "value"]):
            intent_scores["belief"] = 0.9

        if any(k in q for k in ["我们", "关系", "对你", "对你来说", "信任", "relationship"]):
            intent_scores["relationship"] = 0.85

        if any(k in q for k in ["经历", "故事", "过去", "曾经", "narrative", "history"]):
            intent_scores["narrative"] = 0.8

        intent_scores["semantic"] = 0.5
        return intent_scores

    def select_memory_layers(self, query: str, intent_scores: Dict[str, float]) -> List[str]:
        layers = []
        for layer, base_priority in self.LAYER_PRIORITY.items():
            boost = intent_scores.get(layer, 0.0)
            final_priority = base_priority + boost * 1.2
            layers.append((layer, final_priority))

        layers.sort(key=lambda x: x[1], reverse=True)
        return [layer for layer, _ in layers[:6]]

    def hybrid_recall(self, query: str, top_k: int = 12) -> List[Dict]:
        intent_scores = self.detect_intent(query)
        selected_layers = self.select_memory_layers(query, intent_scores)

        all_results = []
        seen = set()

        for layer in selected_layers:
            layer_results = self.storage.recall(query, top_k=top_k * 2, layer=layer)
            for r in layer_results:
                mid = r.get("memory_id") or r.get("id")
                if mid and mid not in seen:
                    seen.add(mid)
                    r["_layer"] = layer
                    r["_intent_boost"] = intent_scores.get(layer, 0.0)
                    all_results.append(r)

        return self.rerank(all_results, top_k)

    def rerank(self, results: List[Dict], top_k: int) -> List[Dict]:
        for r in results:
            base_sim = 1.0 - r.get("_distance", 0.5)
            layer_boost = self.LAYER_PRIORITY.get(r.get("_layer", "episodic"), 0.4)
            intent_boost = r.get("_intent_boost", 0.0)

            r["_final_score"] = (
                base_sim * 0.45
                + layer_boost * 0.25
                + intent_boost * 0.20
                + r.get("importance", 0.5) * 0.10
            )

        results.sort(key=lambda x: x["_final_score"], reverse=True)
        return results[:top_k]

    def inject_context(self, results: List[Dict]) -> str:
        grouped: Dict[str, List] = {}
        for r in results:
            layer = r.get("_layer", "episodic")
            grouped.setdefault(layer, []).append(r)

        context_parts = []
        if "identity" in grouped:
            context_parts.append("【Identity Context】")
            for r in grouped["identity"][:3]:
                context_parts.append(f"- {r['content']}")

        for layer, items in grouped.items():
            if layer == "identity":
                continue
            context_parts.append(f"【{layer.capitalize()} Context】")
            for r in items[:4]:
                context_parts.append(f"- {r['content'][:280]}")

        return "\n\n".join(context_parts)

    def route(self, query: str, top_k: int = 12) -> Dict[str, Any]:
        results = self.hybrid_recall(query, top_k)
        context = self.inject_context(results)

        return {
            "context": context,
            "results": results,
            "used_layers": list({r.get("_layer") for r in results}),
            "intent_scores": self.detect_intent(query),
        }

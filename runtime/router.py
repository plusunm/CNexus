"""Hierarchical Recall Engine — label-priority block recall + episodic fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from memory.block import BLOCK_SPECS, LABEL_PRIORITY
from storage.manager import UnifiedStorageManager

if TYPE_CHECKING:
    from memory.block import MemoryBlock
    from memory.manager import MemoryManager

# Backward-compat: block label → legacy episodic layer
LABEL_TO_LAYER: Dict[str, str] = {
    "persona": "identity",
    "intent": "goal",
    "user_profile": "relationship",
    "emotion": "narrative",
    "working_memory": "working",
    "archival_facts": "semantic",
}

# Legacy layer priority (episodic vector recall)
LAYER_PRIORITY: Dict[str, float] = {
    "identity": 1.0,
    "goal": 0.9,
    "belief": 0.85,
    "relationship": 0.8,
    "narrative": 0.75,
    "semantic": 0.6,
    "episodic": 0.45,
    "working": 0.9,
}

LABEL_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "persona": ["我是谁", "你是谁", "性格", "人格", "personality", "identity", "自我"],
    "intent": ["目标", "计划", "想要", "希望", "goal", "plan", "长期", "动机"],
    "emotion": ["感觉", "情绪", "心情", "emotion", "feeling", "情感"],
    "user_profile": ["偏好", "喜欢", "用户", "profile", "关系", "信任", "对你"],
    "working_memory": ["当前", "任务", "正在", "working", "现在", "进行中"],
    "archival_facts": ["事实", "经验", "知识", "fact", "历史", "记得"],
}


class HierarchicalRecallEngine:
    """
    Hierarchical Recall — structured MemoryBlock.label priority + episodic fallback.

    Block priority: persona > intent > user_profile > emotion > working_memory > archival_facts
    Episodic layers remain for historical trace recall (backward compatible).
    """

    LABEL_PRIORITY = LABEL_PRIORITY
    LAYER_PRIORITY = LAYER_PRIORITY

    def __init__(
        self,
        storage: UnifiedStorageManager,
        memory_manager: Optional["MemoryManager"] = None,
    ):
        self.storage = storage
        self.memory_manager = memory_manager

    def set_memory_manager(self, memory_manager: "MemoryManager") -> None:
        self.memory_manager = memory_manager

    # ── intent detection ───────────────────────────────────────────────

    def detect_label_intent(self, query: str) -> Dict[str, float]:
        q = query.lower()
        scores = {label: 0.0 for label in LABEL_PRIORITY}
        for label, keywords in LABEL_INTENT_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                scores[label] = 0.95
        scores["archival_facts"] = max(scores.get("archival_facts", 0.0), 0.35)
        return scores

    def detect_intent(self, query: str) -> Dict[str, float]:
        """Legacy layer intent — kept for episodic recall compatibility."""
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

    def select_block_labels(self, query: str, label_intent: Dict[str, float]) -> List[str]:
        labels = []
        for label, base_priority in LABEL_PRIORITY.items():
            boost = label_intent.get(label, 0.0)
            spec = BLOCK_SPECS.get(label, {})
            always = spec.get("always_in_context", False)
            final = base_priority + boost * 1.2
            if always:
                final += 0.5
            labels.append((label, final))

        labels.sort(key=lambda x: x[1], reverse=True)
        return [label for label, _ in labels]

    def select_memory_layers(self, query: str, intent_scores: Dict[str, float]) -> List[str]:
        layers = []
        for layer, base_priority in LAYER_PRIORITY.items():
            boost = intent_scores.get(layer, 0.0)
            final_priority = base_priority + boost * 1.2
            layers.append((layer, final_priority))

        layers.sort(key=lambda x: x[1], reverse=True)
        return [layer for layer, _ in layers[:6]]

    # ── block recall ───────────────────────────────────────────────────

    def recall_blocks(self, query: str, labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if not self.memory_manager:
            return []

        label_intent = self.detect_label_intent(query)
        selected = labels or self.select_block_labels(query, label_intent)
        results: List[Dict[str, Any]] = []

        for label in selected:
            block = self.memory_manager.get_active_block(label)
            if not block:
                continue
            results.append(self._block_to_result(block, query, label_intent))

        results.sort(
            key=lambda x: (
                LABEL_PRIORITY.get(x.get("_label", ""), 0.0),
                x.get("_final_score", 0.0),
            ),
            reverse=True,
        )
        return results

    def _block_to_result(
        self,
        block: "MemoryBlock",
        query: str,
        label_intent: Dict[str, float],
    ) -> Dict[str, Any]:
        base = LABEL_PRIORITY.get(block.label, 0.5)
        intent_boost = label_intent.get(block.label, 0.0)
        q_words = set(query.lower().split())
        c_words = set(block.content.lower().split())
        overlap = len(q_words & c_words) / max(len(q_words), 1) if q_words else 0.0

        final_score = (
            base * 0.45
            + intent_boost * 0.25
            + overlap * 0.15
            + block.importance * 0.15
        )

        legacy_layer = LABEL_TO_LAYER.get(block.label, "episodic")
        return {
            "memory_id": block.block_id,
            "block_id": block.block_id,
            "content": block.content,
            "label": block.label,
            "_label": block.label,
            "_layer": legacy_layer,
            "_source": "block",
            "importance": block.importance,
            "governance_status": block.governance_status,
            "version": block.version,
            "_intent_boost": intent_boost,
            "_relevance_overlap": round(overlap, 3),
            "_final_score": round(final_score, 5),
        }

    # ── episodic recall (legacy) ───────────────────────────────────────

    def recall_episodic(self, query: str, top_k: int = 12) -> List[Dict]:
        intent_scores = self.detect_intent(query)
        selected_layers = self.select_memory_layers(query, intent_scores)

        all_results: List[Dict] = []
        seen: set = set()

        for layer in selected_layers:
            layer_results = self.storage.recall(query, top_k=top_k * 2, layer=layer)
            for r in layer_results:
                mid = r.get("memory_id") or r.get("id")
                if mid and mid not in seen:
                    seen.add(mid)
                    r["_layer"] = layer
                    r["_source"] = "episodic"
                    r["_intent_boost"] = intent_scores.get(layer, 0.0)
                    all_results.append(r)

        return self.rerank_episodic(all_results, top_k)

    def rerank_episodic(self, results: List[Dict], top_k: int) -> List[Dict]:
        for r in results:
            base_sim = 1.0 - r.get("_distance", 0.5)
            layer_boost = LAYER_PRIORITY.get(r.get("_layer", "episodic"), 0.4)
            intent_boost = r.get("_intent_boost", 0.0)

            r["_final_score"] = (
                base_sim * 0.45
                + layer_boost * 0.25
                + intent_boost * 0.20
                + r.get("importance", 0.5) * 0.10
            )

        results.sort(key=lambda x: x["_final_score"], reverse=True)
        return results[:top_k]

    # ── hybrid recall (blocks + episodic) ──────────────────────────────

    def hybrid_recall(self, query: str, top_k: int = 12) -> List[Dict]:
        block_results = self.recall_blocks(query)
        episodic_budget = max(top_k - len(block_results), top_k // 2)
        episodic_results = self.recall_episodic(query, top_k=episodic_budget)

        seen_ids: set = set()
        merged: List[Dict] = []

        for r in block_results:
            mid = r.get("memory_id") or r.get("block_id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                merged.append(r)

        for r in episodic_results:
            mid = r.get("memory_id") or r.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                merged.append(r)

        merged.sort(key=lambda x: x.get("_final_score", 0.0), reverse=True)
        return merged[:top_k]

    def rerank(self, results: List[Dict], top_k: int) -> List[Dict]:
        """Unified rerank — blocks naturally rank higher via _final_score."""
        results.sort(key=lambda x: x.get("_final_score", 0.0), reverse=True)
        return results[:top_k]

    # ── context injection ──────────────────────────────────────────────

    def inject_context(self, results: List[Dict]) -> str:
        blocks = [r for r in results if r.get("_source") == "block"]
        episodic = [r for r in results if r.get("_source") != "block"]

        parts: List[str] = []

        if blocks:
            parts.append("【Structured Memory Blocks】")
            grouped_blocks: Dict[str, List] = {}
            for r in blocks:
                grouped_blocks.setdefault(r.get("_label", "unknown"), []).append(r)
            for label in sorted(
                grouped_blocks.keys(),
                key=lambda lb: LABEL_PRIORITY.get(lb, 0.0),
                reverse=True,
            ):
                items = grouped_blocks[label]
                parts.append(f"  [{label}]")
                for r in items[:2]:
                    parts.append(f"  • {r.get('content', '')[:280]}")

        if episodic:
            grouped_ep: Dict[str, List] = {}
            for r in episodic:
                layer = r.get("_layer", "episodic")
                grouped_ep.setdefault(layer, []).append(r)

            if "identity" in grouped_ep:
                parts.append("【Identity Context】")
                for r in grouped_ep["identity"][:3]:
                    parts.append(f"- {r['content']}")

            for layer, items in grouped_ep.items():
                if layer == "identity":
                    continue
                parts.append(f"【{layer.capitalize()} Context】")
                for r in items[:4]:
                    parts.append(f"- {r.get('content', '')[:280]}")

        return "\n\n".join(parts)

    def route(self, query: str, top_k: int = 12) -> Dict[str, Any]:
        results = self.hybrid_recall(query, top_k)
        context = self.inject_context(results)

        return {
            "context": context,
            "results": results,
            "used_labels": list({r.get("_label") for r in results if r.get("_source") == "block"}),
            "used_layers": list({r.get("_layer") for r in results if r.get("_source") != "block"}),
            "label_intent": self.detect_label_intent(query),
            "intent_scores": self.detect_intent(query),
            "block_count": sum(1 for r in results if r.get("_source") == "block"),
            "episodic_count": sum(1 for r in results if r.get("_source") != "block"),
        }


# Backward-compatible alias
HierarchicalRecallRouter = HierarchicalRecallEngine

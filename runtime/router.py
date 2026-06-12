"""CNexus L1/L2 HierarchicalRecallEngine — Option 2 integrated.

Level 1-2: MemoryBlockStore (recall_by_priority + recall_episodic)
Level 3-8: UnifiedStorageManager (Lance vector + Kuzu graph + legacy layers)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from memory.block import BLOCK_SPECS, LABEL_PRIORITY
from memory.block import EpisodicMemoryBlock
from storage.manager import UnifiedStorageManager

if TYPE_CHECKING:
    from memory.block import MemoryBlock
    from memory.block_store import MemoryBlockStore
    from memory.manager import MemoryManager

LABEL_TO_LAYER: Dict[str, str] = {
    "persona": "identity",
    "intent": "goal",
    "user_profile": "relationship",
    "emotion": "narrative",
    "working_memory": "working",
    "attention_state": "working",
    "archival_facts": "semantic",
    "belief_store": "belief",
    "episodic_event": "episodic",
    "episodic_dialogue": "episodic",
    "episodic_decision": "episodic",
}

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
    "attention_state": ["注意力", "关注", "焦点", "attention", "focus", "优先"],
    "archival_facts": ["事实", "经验", "知识", "fact", "历史", "记得"],
    "episodic_event": ["事件", "发生", "经历", "event", "action", "outcome"],
    "episodic_dialogue": ["对话", "说过", "聊天", "dialogue", "utterance", "交流"],
    "episodic_decision": ["决策", "选择", "决定", "decision", "rationale", "选项"],
    "belief_store": ["相信", "认为", "信念", "belief", "价值观", "原则"],
}


@dataclass
class RecallResult:
    source: str
    label: Optional[str] = None
    content: Any = None
    score: float = 0.0
    priority: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)
    block_id: Optional[str] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "label": self.label,
            "content": self.content,
            "score": self.score,
            "priority": self.priority,
            "metadata": dict(self.metadata),
            "block_id": self.block_id,
            "version": self.version,
        }


class HierarchicalRecallEngine:
    """
    8-level hierarchical recall.

    Levels 1-2 delegate to MemoryBlockStore; levels 3-8 use vector/graph storage.
    """

    LABEL_PRIORITY = LABEL_PRIORITY
    LAYER_PRIORITY = LAYER_PRIORITY

    def __init__(
        self,
        storage: UnifiedStorageManager,
        memory_manager: Optional["MemoryManager"] = None,
        *,
        max_results: int = 20,
    ):
        self.storage = storage
        self.memory_manager = memory_manager
        self.max_results = max_results
        self._last_recall_stats: Dict[str, Any] = {}

    def set_memory_manager(self, memory_manager: "MemoryManager") -> None:
        self.memory_manager = memory_manager

    @property
    def block_store(self) -> Optional["MemoryBlockStore"]:
        if self.memory_manager is None:
            return None
        return self.memory_manager.blocks

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

    # ── unified recall (Option 2 primary entry) ────────────────────────

    def recall(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 8,
        include_episodic: bool = True,
        attention_boost: bool = True,
    ) -> List[RecallResult]:
        start = time.time()
        results: List[RecallResult] = []
        context = context or {}
        label_intent = self.detect_label_intent(query)

        results.extend(self._recall_core_block_results(query, label_intent))
        if include_episodic:
            results.extend(self._recall_episodic_block_results())

        exclude_labels = {r.label for r in results if r.label}
        results.extend(
            self._recall_from_storage_layers(
                query=query,
                context=context,
                exclude_labels=exclude_labels,
                top_k=max(top_k * 2, self.max_results),
            )
        )

        if attention_boost:
            self._apply_attention_boost(results)

        unique = self._dedupe_and_rank(results, top_k)
        self._last_recall_stats = {
            "query": query[:100],
            "total_candidates": len(results),
            "returned": len(unique),
            "latency_ms": round((time.time() - start) * 1000, 2),
            "sources": {
                source: sum(1 for item in unique if item.source == source)
                for source in {item.source for item in unique}
            },
        }
        return unique

    def _recall_core_block_results(
        self,
        query: str,
        label_intent: Dict[str, float],
    ) -> List[RecallResult]:
        store = self.block_store
        if store is None:
            return []

        selected = set(self.select_block_labels(query, label_intent))
        blocks = store.recall_by_priority(top_k=8, include_episodic=False)
        results: List[RecallResult] = []
        for block in blocks:
            if block.label not in selected:
                continue
            intent_boost = label_intent.get(block.label, 0.0)
            score = (1.0 - block.priority * 0.08) + intent_boost * 0.2
            results.append(
                RecallResult(
                    source="block",
                    label=block.label,
                    content=block.content,
                    score=round(score, 5),
                    priority=block.priority,
                    block_id=block.block_id,
                    version=block.version,
                    metadata={
                        "last_access": block.last_access.isoformat(),
                        "decay_factor": block.decay(0),
                        "importance": block.importance,
                        "governance_status": block.governance_status,
                    },
                )
            )
        return results

    def _recall_episodic_block_results(self) -> List[RecallResult]:
        store = self.block_store
        if store is None:
            return []

        results: List[RecallResult] = []
        for block in store.recall_episodic(limit=5):
            recent = block.get_recent(3) if isinstance(block, EpisodicMemoryBlock) else []
            content = recent or block.payload if isinstance(block, EpisodicMemoryBlock) else block.content
            results.append(
                RecallResult(
                    source="episodic",
                    label=block.label,
                    content=content,
                    score=0.85,
                    priority=block.priority,
                    block_id=block.block_id,
                    version=block.version,
                    metadata={
                        "episodic_type": getattr(block, "episodic_type", "event"),
                        "timestamp": block.timestamp.isoformat()
                        if isinstance(block, EpisodicMemoryBlock)
                        else block.updated_at.isoformat(),
                        "entry_count": len(block.payload)
                        if isinstance(block, EpisodicMemoryBlock)
                        else 0,
                    },
                )
            )
        return results

    def _recall_from_storage_layers(
        self,
        query: str,
        context: Dict[str, Any],
        exclude_labels: Set[str],
        top_k: int,
    ) -> List[RecallResult]:
        del context
        vector_hits = self.recall_vector_episodic(query, top_k=top_k)
        results: List[RecallResult] = []
        for hit in vector_hits:
            layer = hit.get("_layer", "episodic")
            label = hit.get("_label") or layer
            if label in exclude_labels:
                continue
            results.append(
                RecallResult(
                    source="vector",
                    label=label,
                    content=hit.get("content", ""),
                    score=float(hit.get("_final_score", hit.get("importance", 0.5))),
                    priority=10,
                    block_id=hit.get("memory_id") or hit.get("block_id"),
                    metadata={
                        "layer": layer,
                        "intent_boost": hit.get("_intent_boost", 0.0),
                        "distance": hit.get("_distance"),
                    },
                )
            )
        return results

    def _apply_attention_boost(self, results: List[RecallResult]) -> None:
        store = self.block_store
        if store is None:
            return
        snapshot = store.get_attention_snapshot()
        if snapshot is None:
            return
        focus_scores = snapshot.read_snapshot().get("focus_scores") or {}
        for result in results:
            if result.label and result.label in focus_scores:
                result.score = round(result.score * (1.0 + focus_scores[result.label] * 0.3), 5)
                result.metadata["attention_boost"] = True

    @staticmethod
    def _dedupe_and_rank(results: List[RecallResult], top_k: int) -> List[RecallResult]:
        seen: Set[tuple] = set()
        unique: List[RecallResult] = []
        for result in sorted(results, key=lambda item: (-item.score, item.priority)):
            content_key = result.content
            if isinstance(content_key, list):
                content_key = json.dumps(content_key, ensure_ascii=False)[:50]
            elif not isinstance(content_key, str):
                content_key = str(content_key)[:50]
            key = (result.source, result.label or result.block_id or content_key)
            if key in seen:
                continue
            seen.add(key)
            unique.append(result)
            if len(unique) >= top_k:
                break
        return unique

    def recall_episodic_only(
        self,
        episodic_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[RecallResult]:
        store = self.block_store
        if store is None:
            return []
        blocks = store.recall_episodic(episodic_type, limit)
        return [
            RecallResult(
                source="episodic",
                label=block.label,
                content=block.payload if isinstance(block, EpisodicMemoryBlock) else block.content,
                score=0.9,
                priority=block.priority,
                block_id=block.block_id,
                version=block.version,
                metadata={
                    "episodic_type": getattr(block, "episodic_type", episodic_type or "event"),
                    "timestamp": block.timestamp.isoformat()
                    if isinstance(block, EpisodicMemoryBlock)
                    else block.updated_at.isoformat(),
                },
            )
            for block in blocks
        ]

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._last_recall_stats)

    def warm_up(self) -> None:
        store = self.block_store
        if store is not None:
            store.recall_by_priority(top_k=10)

    # ── legacy dict API (backward compatible) ──────────────────────────

    def recall_blocks(self, query: str, labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if self.block_store is not None:
            label_intent = self.detect_label_intent(query)
            core_results = self._recall_core_block_results(query, label_intent)
            if labels:
                allowed = set(labels)
                core_results = [r for r in core_results if r.label in allowed]
            converted = [self._recall_result_to_legacy_dict(r, query, label_intent) for r in core_results]
            converted.sort(
                key=lambda x: (
                    LABEL_PRIORITY.get(x.get("_label", ""), 0.0),
                    x.get("_final_score", 0.0),
                ),
                reverse=True,
            )
            return converted

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

    def _recall_result_to_legacy_dict(
        self,
        result: RecallResult,
        query: str,
        label_intent: Dict[str, float],
    ) -> Dict[str, Any]:
        content = result.content
        if isinstance(content, list):
            text = json.dumps(content, ensure_ascii=False)
        elif isinstance(content, dict):
            text = json.dumps(content, ensure_ascii=False)
        else:
            text = str(content or "")

        q_words = set(query.lower().split())
        c_words = set(text.lower().split())
        overlap = len(q_words & c_words) / max(len(q_words), 1) if q_words else 0.0
        intent_boost = label_intent.get(result.label or "", 0.0)
        legacy_layer = LABEL_TO_LAYER.get(result.label or "", "episodic")

        return {
            "memory_id": result.block_id,
            "block_id": result.block_id,
            "content": text,
            "label": result.label,
            "_label": result.label,
            "_layer": legacy_layer,
            "_source": result.source if result.source in {"block", "episodic"} else "episodic",
            "importance": result.metadata.get("importance", 0.5),
            "governance_status": result.metadata.get("governance_status", "approved"),
            "version": result.version,
            "_intent_boost": intent_boost,
            "_relevance_overlap": round(overlap, 3),
            "_final_score": round(result.score, 5),
            **{k: v for k, v in result.metadata.items() if not k.startswith("_")},
        }

    def recall_vector_episodic(self, query: str, top_k: int = 12) -> List[Dict]:
        intent_scores = self.detect_intent(query)
        selected_layers = self.select_memory_layers(query, intent_scores)

        all_results: List[Dict] = []
        seen: set = set()

        for layer in selected_layers:
            layer_results = self.storage.recall(query, top_k=top_k * 2, layer=layer)
            for row in layer_results:
                mid = row.get("memory_id") or row.get("id")
                if mid and mid not in seen:
                    seen.add(mid)
                    row["_layer"] = layer
                    row["_source"] = "episodic"
                    row["_intent_boost"] = intent_scores.get(layer, 0.0)
                    all_results.append(row)

        return self.rerank_episodic(all_results, top_k)

    def recall_episodic(self, query: str, top_k: int = 12) -> List[Dict]:
        """Backward-compatible vector episodic recall."""
        return self.recall_vector_episodic(query, top_k=top_k)

    def rerank_episodic(self, results: List[Dict], top_k: int) -> List[Dict]:
        for row in results:
            base_sim = 1.0 - row.get("_distance", 0.5)
            layer_boost = LAYER_PRIORITY.get(row.get("_layer", "episodic"), 0.4)
            intent_boost = row.get("_intent_boost", 0.0)

            row["_final_score"] = (
                base_sim * 0.45
                + layer_boost * 0.25
                + intent_boost * 0.20
                + row.get("importance", 0.5) * 0.10
            )

        results.sort(key=lambda x: x["_final_score"], reverse=True)
        return results[:top_k]

    def hybrid_recall(self, query: str, top_k: int = 12) -> List[Dict]:
        unified = self.recall(
            query,
            top_k=top_k,
            include_episodic=True,
            attention_boost=True,
        )
        legacy = [self._recall_result_to_legacy_dict(r, query, self.detect_label_intent(query)) for r in unified]
        legacy.sort(key=lambda x: x.get("_final_score", 0.0), reverse=True)
        return legacy[:top_k]

    def rerank(self, results: List[Dict], top_k: int) -> List[Dict]:
        results.sort(key=lambda x: x.get("_final_score", 0.0), reverse=True)
        return results[:top_k]

    def inject_context(self, results: List[Dict]) -> str:
        blocks = [r for r in results if r.get("_source") == "block"]
        episodic = [r for r in results if r.get("_source") != "block"]

        parts: List[str] = []

        if blocks:
            parts.append("【Structured Memory Blocks】")
            grouped_blocks: Dict[str, List] = {}
            for row in blocks:
                grouped_blocks.setdefault(row.get("_label", "unknown"), []).append(row)
            for label in sorted(
                grouped_blocks.keys(),
                key=lambda lb: LABEL_PRIORITY.get(lb, 0.0),
                reverse=True,
            ):
                items = grouped_blocks[label]
                parts.append(f"  [{label}]")
                for row in items[:2]:
                    content = row.get("content", "")
                    if isinstance(content, list):
                        content = json.dumps(content, ensure_ascii=False)
                    parts.append(f"  • {str(content)[:280]}")

        if episodic:
            grouped_ep: Dict[str, List] = {}
            for row in episodic:
                layer = row.get("_layer", "episodic")
                grouped_ep.setdefault(layer, []).append(row)

            if "identity" in grouped_ep:
                parts.append("【Identity Context】")
                for row in grouped_ep["identity"][:3]:
                    parts.append(f"- {row['content']}")

            for layer, items in grouped_ep.items():
                if layer == "identity":
                    continue
                parts.append(f"【{layer.capitalize()} Context】")
                for row in items[:4]:
                    content = row.get("content", "")
                    if isinstance(content, list):
                        content = json.dumps(content, ensure_ascii=False)
                    parts.append(f"- {str(content)[:280]}")

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
            "recall_stats": self.get_stats(),
        }


HierarchicalRecallRouter = HierarchicalRecallEngine


if __name__ == "__main__":
    print("HierarchicalRecallEngine Option 2 integrated")
    print("- Level 1-2: MemoryBlockStore.recall_by_priority / recall_episodic")
    print("- Level 3-8: UnifiedStorageManager vector recall")

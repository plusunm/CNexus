import math
import time
from collections import OrderedDict
from typing import Any, Dict, List


class DynamicAttentionField:
    """
    竞争性注意力场 — 模拟前额叶 + 杏仁核动态激活机制
    Working Memory 容量严格限制在 7±2 条（Miller's Law）
    """

    MAX_ACTIVE_MEMORY = 9

    def __init__(self):
        self.working_memory: OrderedDict[str, Dict] = OrderedDict()
        self.last_decay_time = time.time()
        self._last_focus_scores: Dict[str, float] = {}

    def _compute_attention_score(self, memory: Dict, current_context: str = "") -> float:
        recency = memory.get("recency_weight", 1.0)
        identity = memory.get("identity_weight", 0.0)
        goal = memory.get("goal_weight", 0.0)
        emotional = memory.get("emotional_weight", 0.5)
        relationship = memory.get("relationship_weight", 0.0)
        novelty = memory.get("novelty_weight", 0.4)
        conflict = memory.get("conflict_weight", 0.0)

        context_boost = 0.3
        if current_context and "content" in memory:
            if any(word in current_context.lower() for word in memory["content"].lower().split()[:10]):
                context_boost = 0.8

        score = (
            recency * 0.25
            + identity * 0.22
            + goal * 0.18
            + emotional * 0.15
            + relationship * 0.10
            + novelty * 0.05
            + conflict * 0.03
            + context_boost * 0.02
        )
        return max(0.05, min(1.0, score))

    def activate(self, memory: Dict, current_context: str = "") -> Dict:
        mem_id = memory.get("memory_id") or memory.get("id")
        if not mem_id:
            return memory

        memory["attention_score"] = self._compute_attention_score(memory, current_context)
        memory["last_activated"] = time.time()
        memory["access_count"] = memory.get("access_count", 0) + 1

        if mem_id in self.working_memory:
            self.working_memory.move_to_end(mem_id)
        else:
            self.working_memory[mem_id] = memory

        if len(self.working_memory) > self.MAX_ACTIVE_MEMORY:
            weakest = min(self.working_memory.items(), key=lambda x: x[1].get("attention_score", 0))
            self.working_memory.pop(weakest[0])

        self._decay()
        return memory

    def decay(self):
        now = time.time()
        for mem_id, mem in list(self.working_memory.items()):
            delta = now - mem.get("last_activated", now)
            decay_factor = math.exp(-delta / 7200)
            mem["attention_score"] = mem.get("attention_score", 1.0) * decay_factor

            if mem["attention_score"] < 0.1:
                self.working_memory.pop(mem_id)

    def _decay(self):
        if time.time() - self.last_decay_time > 30:
            self.decay()
            self.last_decay_time = time.time()

    def reinforce(self, memory_id: str, boost: float = 0.25):
        if memory_id in self.working_memory:
            mem = self.working_memory[memory_id]
            mem["attention_score"] = min(1.0, mem.get("attention_score", 0.5) + boost)
            self.working_memory.move_to_end(memory_id)

    def suppress(self, memory_id: str, suppress_factor: float = 0.4):
        if memory_id in self.working_memory:
            mem = self.working_memory[memory_id]
            mem["attention_score"] *= 1 - suppress_factor

    def working_memory_snapshot(self) -> List[Dict]:
        self._decay()
        items = list(self.working_memory.values())
        items.sort(key=lambda x: x.get("attention_score", 0), reverse=True)
        return items

    def attention_competition(self, candidates: List[Dict], current_context: str = "") -> List[Dict]:
        for mem in candidates:
            self.activate(mem, current_context)
        return self.working_memory_snapshot()

    def focus_scores_by_label(self) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for mem in self.working_memory.values():
            label = (
                mem.get("block_label")
                or mem.get("_label")
                or mem.get("label")
                or mem.get("_layer")
                or "working_memory"
            )
            scores[label] = scores.get(label, 0.0) + float(mem.get("attention_score", 0.0))
        total = sum(scores.values()) or 1.0
        return {label: round(score / total, 4) for label, score in scores.items()}

    def top_focus_labels(self, n: int = 5) -> List[str]:
        ranked = sorted(self.focus_scores_by_label().items(), key=lambda item: item[1], reverse=True)
        return [label for label, _ in ranked[:n]]

    def hydrate_from_snapshot(self, snapshot: Dict[str, Any]) -> None:
        focus_scores = snapshot.get("focus_scores") or {}
        if not focus_scores:
            return
        for label, weight in focus_scores.items():
            self.working_memory[label] = {
                "memory_id": label,
                "block_label": label,
                "_label": label,
                "content": f"attention snapshot for {label}",
                "attention_score": float(weight),
                "last_activated": time.time(),
            }
        self._last_focus_scores = dict(focus_scores)

    def detect_drift(self, current_scores: Dict[str, float]) -> float:
        if not self._last_focus_scores:
            return 0.0
        keys = set(current_scores) | set(self._last_focus_scores)
        if not keys:
            return 0.0
        delta = sum(
            abs(float(current_scores.get(key, 0.0)) - float(self._last_focus_scores.get(key, 0.0)))
            for key in keys
        )
        return round(delta / len(keys), 4)

    def sync_and_persist(self, memory_manager, turn: int) -> Dict[str, Any]:
        """Hybrid sync: dynamic field → AttentionStateBlock via MemoryManager."""
        focus_scores = self.focus_scores_by_label()
        top_focus = self.top_focus_labels()
        drift_score = self.detect_drift(focus_scores)
        block = memory_manager.sync_attention_block(focus_scores, top_focus, turn)
        self._last_focus_scores = dict(focus_scores)
        return {
            "drift_score": drift_score,
            "focus_scores": focus_scores,
            "top_focus": top_focus,
            "block_id": getattr(block, "block_id", None),
        }

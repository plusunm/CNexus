"""Rule-first cognitive state parsing — LLM only on key decision points."""

from __future__ import annotations

import hashlib
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LLMParseHook = Callable[[str], Dict]

# Per-turn caps
BELIEF_DELTA_CAP = 0.08
BELIEF_TRAIT_FLOOR = 0.0
BELIEF_TRAIT_CEILING = 1.0
RELATION_SHIFT_CAP = 0.15
RELATION_SCORE_FLOOR = 0.0
RELATION_SCORE_CEILING = 1.0

POSITIVE_RELATION = ("谢谢", "感谢", "信任", "喜欢", "不错", "很好", "帮大忙", "靠谱")
NEGATIVE_RELATION = (
    "垃圾", "废物", "蠢", "傻", "滚", "讨厌", "恶心", "去死", "没用", "烂",
    "骂", "骗子", "失望", "愤怒", "恨",
)

TRAIT_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "务实": ("务实", "具体", "落地", "执行", "方案"),
    "稳定": ("稳定", "连续", "一致", "可靠", "长期"),
    "共情": ("感受", "理解", " empathy", "共情", "情绪"),
    "审慎": ("谨慎", "风险", "核实", "证据", "客观"),
}

KEY_DECISION_LAYERS = frozenset({"goal", "identity", "belief"})
DISSONANCE_LLM_THRESHOLD = 0.55
IMPORTANCE_LLM_THRESHOLD = 0.85


@dataclass
class ParsedCognitiveState:
    traits_detected: List[str] = field(default_factory=list)
    belief_delta: Dict[str, float] = field(default_factory=dict)
    relation_shift: float = 0.0
    dissonance_score: float = 0.0
    used_llm: bool = False
    cache_hit: bool = False
    trigger_reason: str = "rule_based"


class CognitiveStateParser:
    """
    Parse user input into cognitive deltas without calling LLM on every turn.

    - LRU cache for repeated / near-identical inputs
    - LLM hook only for key decision points (high importance, identity layers, high dissonance)
    - Dynamic belief_delta with per-turn and cumulative caps
    - Bidirectional relation_shift (praise and hostility)
    """

    def __init__(
        self,
        cache_size: int = 256,
        llm_hook: Optional[LLMParseHook] = None,
    ):
        self.llm_hook = llm_hook
        self._cache: OrderedDict[str, ParsedCognitiveState] = OrderedDict()
        self._cache_size = cache_size
        self._pending_batch: List[str] = []

    def _cache_key(self, user_input: str) -> str:
        normalized = re.sub(r"\s+", " ", user_input.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def _cache_get(self, key: str) -> Optional[ParsedCognitiveState]:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        hit = self._cache[key]
        hit.cache_hit = True
        return hit

    def _cache_put(self, key: str, value: ParsedCognitiveState) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def should_use_llm(
        self,
        user_input: str,
        *,
        layer: str = "episodic",
        importance: float = 0.5,
        pre_scan: Optional[ParsedCognitiveState] = None,
    ) -> Tuple[bool, str]:
        if self.llm_hook is None:
            return False, "no_llm_hook"
        if layer in KEY_DECISION_LAYERS:
            return True, f"key_layer:{layer}"
        if importance >= IMPORTANCE_LLM_THRESHOLD:
            return True, f"high_importance:{importance:.2f}"
        scan = pre_scan or self._parse_rule_based(user_input, importance=importance)
        if scan.dissonance_score >= DISSONANCE_LLM_THRESHOLD:
            return True, f"dissonance:{scan.dissonance_score:.2f}"
        return False, "rule_sufficient"

    def _detect_traits(self, text: str) -> List[str]:
        found = [trait for trait, kws in TRAIT_KEYWORDS.items() if any(k in text for k in kws)]
        return found or ["稳定"]

    def _score_dissonance(self, text: str, importance: float) -> float:
        """Heuristic cognitive dissonance — triggers immediate identity refresh."""
        score = 0.0
        if any(k in text for k in ("不对", "矛盾", "变了", "不像你", "认知失调", "不一致")):
            score += 0.45
        if any(k in text for k in NEGATIVE_RELATION):
            score += 0.35
        if importance >= 0.9:
            score += 0.2
        return min(1.0, score)

    def _compute_relation_shift(self, text: str, importance: float) -> float:
        lower = text.lower()
        shift = 0.0
        for kw in POSITIVE_RELATION:
            if kw in lower:
                shift += 0.04 * importance
        for kw in NEGATIVE_RELATION:
            if kw in lower:
                shift -= 0.06 * max(importance, 0.6)
        return max(-RELATION_SHIFT_CAP, min(RELATION_SHIFT_CAP, shift))

    def compute_belief_delta(
        self,
        text: str,
        traits: List[str],
        importance: float,
        current_beliefs: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Dynamic belief delta with per-turn cap and cumulative ceiling."""
        current = current_beliefs or {}
        sentiment = self._compute_relation_shift(text, importance)
        base = abs(sentiment) * 0.5 + importance * 0.04
        if sentiment < 0:
            base *= 0.6

        deltas: Dict[str, float] = {}
        for trait in traits:
            raw = base if sentiment >= 0 else -base * 0.8
            if trait in ("稳定", "审慎") and sentiment < 0:
                raw = abs(raw) * 0.5
            capped = max(-BELIEF_DELTA_CAP, min(BELIEF_DELTA_CAP, raw))

            current_val = current.get(trait, 0.5)
            if current_val + capped > BELIEF_TRAIT_CEILING:
                capped = BELIEF_TRAIT_CEILING - current_val
            elif current_val + capped < BELIEF_TRAIT_FLOOR:
                capped = BELIEF_TRAIT_FLOOR - current_val

            if abs(capped) >= 0.001:
                deltas[trait] = round(capped, 4)

        return deltas

    def _parse_rule_based(self, user_input: str, importance: float = 0.5) -> ParsedCognitiveState:
        traits = self._detect_traits(user_input)
        dissonance = self._score_dissonance(user_input, importance)
        relation_shift = self._compute_relation_shift(user_input, importance)
        belief_delta = self.compute_belief_delta(user_input, traits, importance)
        return ParsedCognitiveState(
            traits_detected=traits,
            belief_delta=belief_delta,
            relation_shift=relation_shift,
            dissonance_score=dissonance,
            used_llm=False,
            trigger_reason="rule_based",
        )

    def parse_cognitive_state(
        self,
        user_input: str,
        *,
        layer: str = "episodic",
        importance: float = 0.5,
        current_beliefs: Optional[Dict[str, float]] = None,
    ) -> ParsedCognitiveState:
        """Main entry — cache → rule-based → optional LLM on key triggers only."""
        key = self._cache_key(user_input)
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        rule_result = self._parse_rule_based(user_input, importance)
        rule_result.belief_delta = self.compute_belief_delta(
            user_input, rule_result.traits_detected, importance, current_beliefs
        )

        use_llm, reason = self.should_use_llm(
            user_input, layer=layer, importance=importance, pre_scan=rule_result
        )

        if use_llm and self.llm_hook is not None:
            try:
                llm_data = self.llm_hook(user_input)
                merged = ParsedCognitiveState(
                    traits_detected=llm_data.get("traits", rule_result.traits_detected),
                    belief_delta=self._merge_belief_deltas(
                        rule_result.belief_delta,
                        llm_data.get("belief_delta", {}),
                        current_beliefs,
                    ),
                    relation_shift=float(
                        llm_data.get("relation_shift", rule_result.relation_shift)
                    ),
                    dissonance_score=max(
                        rule_result.dissonance_score,
                        float(llm_data.get("dissonance_score", 0.0)),
                    ),
                    used_llm=True,
                    trigger_reason=f"llm:{reason}",
                )
                merged.relation_shift = max(
                    -RELATION_SHIFT_CAP, min(RELATION_SHIFT_CAP, merged.relation_shift)
                )
                self._cache_put(key, merged)
                return merged
            except Exception as exc:
                logger.warning("LLM cognitive parse failed, using rule-based: %s", exc)

        self._cache_put(key, rule_result)
        return rule_result

    def _merge_belief_deltas(
        self,
        rule_delta: Dict[str, float],
        llm_delta: Dict[str, float],
        current_beliefs: Optional[Dict[str, float]],
    ) -> Dict[str, float]:
        merged = dict(rule_delta)
        for trait, delta in llm_delta.items():
            if not isinstance(delta, (int, float)):
                continue
            combined = merged.get(trait, 0.0) + float(delta) * 0.5
            merged[trait] = max(-BELIEF_DELTA_CAP, min(BELIEF_DELTA_CAP, combined))
        return self.compute_belief_delta(
            "",
            list(merged.keys()) or ["稳定"],
            sum(abs(v) for v in merged.values()) or 0.5,
            current_beliefs,
        )

    def queue_for_batch(self, user_input: str) -> None:
        """Optional batch path — flush via flush_batch()."""
        self._pending_batch.append(user_input)

    def flush_batch(
        self,
        *,
        layer: str = "episodic",
        importance: float = 0.5,
    ) -> List[ParsedCognitiveState]:
        if not self._pending_batch:
            return []
        combined = "\n".join(self._pending_batch)
        self._pending_batch.clear()
        return [self.parse_cognitive_state(combined, layer=layer, importance=importance)]


class IdentitySummaryScheduler:
    """Periodic identity summary refresh with dissonance-triggered immediate update."""

    def __init__(
        self,
        interval_turns: int = 5,
        dissonance_threshold: float = 0.65,
    ):
        self.interval_turns = interval_turns
        self.dissonance_threshold = dissonance_threshold
        self.turns_since_update = 0

    def should_refresh(self, dissonance_score: float) -> Tuple[bool, str]:
        if dissonance_score >= self.dissonance_threshold:
            return True, "dissonance_threshold"
        if self.turns_since_update >= self.interval_turns:
            return True, "interval"
        return False, "skip"

    def mark_turn(self, refreshed: bool) -> None:
        if refreshed:
            self.turns_since_update = 0
        else:
            self.turns_since_update += 1

"""ReflectiveEngine — Reflexion-style meta-reflection on interaction turns."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

from memory.manager import MemoryManager

if TYPE_CHECKING:
    from core.llm_client import LLMClient
    from core.model_registry import ModelProfile
    from core.personality.emotion_engine import EmotionEngine
    from core.personality.intent_engine import IntentEngine
    from core.personality.narrative.narrative_builder import NarrativeBuilder

logger = logging.getLogger(__name__)

REFLECTIVE_LABEL = "reflective_trace"


class StructuredReflection(BaseModel):
    """LLM-structured Reflexion output."""

    overall_assessment: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    emotion_intent_alignment: str = ""
    coherence_impact: float = Field(0.0, ge=-1.0, le=1.0)
    key_insight: str = ""


class InteractionReflectionRecord(BaseModel):
    """Reflexion-style record stored in reflective_trace MemoryBlock (JSON)."""

    reflection_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    context_summary: str = ""
    actor_output: str = ""
    reflection: str = ""
    reflection_mode: str = "rule"
    structured_reflection: Optional[Dict[str, Any]] = None
    emotion_snapshot: Dict[str, Any] = Field(default_factory=dict)
    intent_snapshot: Dict[str, Any] = Field(default_factory=dict)
    improvement_suggestions: List[str] = Field(default_factory=list)
    coherence_impact: float = 0.0
    feedback: Optional[str] = None


class ReflectiveEngine:
    """
    L3/L4 meta-reflection — Actor output critique + emotion/intent snapshots.

    Complements trait-based ReflectionPipeline (reflective_memory.ReflectionRecord).
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        emotion_engine: "EmotionEngine",
        intent_engine: "IntentEngine",
        narrative: Optional["NarrativeBuilder"] = None,
        llm_client: Optional["LLMClient"] = None,
        llm_profile_provider: Optional[Callable[[], Optional["ModelProfile"]]] = None,
        *,
        llm_temperature: float = 0.3,
    ):
        self.memory = memory_manager
        self.emotion = emotion_engine
        self.intent = intent_engine
        self.narrative = narrative
        self.llm = llm_client
        self._llm_profile_provider = llm_profile_provider
        self.llm_temperature = llm_temperature

    @staticmethod
    def _dump_record(record: InteractionReflectionRecord) -> str:
        return json.dumps(record.model_dump(mode="json"), ensure_ascii=False)

    @staticmethod
    def _load_record(content: str) -> Optional[InteractionReflectionRecord]:
        if not content or not str(content).strip().startswith("{"):
            return None
        try:
            return InteractionReflectionRecord(**json.loads(content))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def reflect_on_interaction(
        self,
        actor_output: str,
        context: Dict[str, Any],
        *,
        feedback: Optional[str] = None,
        importance: float = 0.75,
        use_llm: bool = True,
    ) -> InteractionReflectionRecord:
        """Reflexion-style self-reflection loop for one interaction turn."""
        emotion_state = self.emotion.get_state_summary()
        active_goals = [g.model_dump(mode="json") for g in self.intent.get_active_goals(3)]

        structured: Optional[StructuredReflection] = None
        reflection_mode = "rule"
        reflection_text = ""
        improvements: List[str] = []
        coherence_impact = self._estimate_coherence_impact(
            emotion_state, active_goals, feedback
        )

        if use_llm and self.llm and self._llm_profile_provider:
            structured = self._generate_llm_reflection(
                actor_output=actor_output,
                context=context,
                emotion_state=emotion_state,
                intent_state=active_goals,
                feedback=feedback,
            )
            if structured:
                reflection_mode = "llm"
                reflection_text = self._format_structured_reflection(structured)
                improvements = list(structured.improvement_suggestions)
                coherence_impact = self._normalize_coherence_impact(
                    structured.coherence_impact,
                    emotion_state,
                    active_goals,
                    feedback,
                )

        if not reflection_text:
            reflection_text = self._generate_rule_based_reflection(
                actor_output=actor_output,
                context=context,
                emotion_state=emotion_state,
                intent_state=active_goals,
                feedback=feedback,
            )
            improvements = self._extract_improvements(reflection_text)

        record = InteractionReflectionRecord(
            reflection_id=f"ref_{uuid.uuid4().hex[:12]}",
            context_summary=str(context)[:300],
            actor_output=(actor_output or "")[:500],
            reflection=reflection_text,
            reflection_mode=reflection_mode,
            structured_reflection=(
                structured.model_dump(mode="json") if structured else None
            ),
            emotion_snapshot=emotion_state,
            intent_snapshot={"active_goals": active_goals},
            improvement_suggestions=improvements,
            coherence_impact=coherence_impact,
            feedback=feedback,
        )

        payload = self._dump_record(record)
        gov = self.memory.governance.check(REFLECTIVE_LABEL, payload, importance)
        if gov.allowed:
            self.memory.create_block(
                REFLECTIVE_LABEL,
                payload,
                importance=importance,
                source="reflective_engine",
            )
        self._update_narrative_self(record, context)
        return record

    def _generate_llm_reflection(
        self,
        *,
        actor_output: str,
        context: Dict[str, Any],
        emotion_state: Dict[str, Any],
        intent_state: List[Dict[str, Any]],
        feedback: Optional[str],
    ) -> Optional[StructuredReflection]:
        profile = self._llm_profile_provider() if self._llm_profile_provider else None
        if not profile or not self.llm:
            return None

        prompt = self._build_reflection_prompt(
            actor_output,
            context,
            emotion_state,
            intent_state,
            feedback,
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Reflexion-style self-critic for a long-lived AI. "
                    "Respond with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            raw_response = self.llm.chat(
                profile,
                messages,
                temperature=self.llm_temperature,
                timeout=90.0,
            )
            return self._parse_structured_reflection(raw_response)
        except Exception as exc:
            logger.warning("LLM reflection failed, falling back to rules: %s", exc)
            return None

    def _build_reflection_prompt(
        self,
        actor_output: str,
        context: Dict[str, Any],
        emotion_state: Dict[str, Any],
        intent_state: List[Dict[str, Any]],
        feedback: Optional[str],
    ) -> str:
        return f"""你是一个高性能 AI 自我反思引擎（Reflexion 风格）。

请对以下交互进行深度反思，并严格以 JSON 格式返回：

**Actor 输出**:
{actor_output}

**上下文**:
{json.dumps(context, ensure_ascii=False)}

**当前情感状态**:
{json.dumps(emotion_state, ensure_ascii=False)}

**当前活跃目标**:
{json.dumps(intent_state, ensure_ascii=False)}

**额外反馈**:
{feedback or "无"}

请按以下结构返回 JSON：
{{
  "overall_assessment": "总体评价（1-2句）",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"],
  "improvement_suggestions": ["具体改进建议1", "具体改进建议2"],
  "emotion_intent_alignment": "情感与意图是否一致的简要分析",
  "coherence_impact": 0.0,
  "key_insight": "最关键的洞见（一句话）"
}}
coherence_impact 取值范围 -0.2 到 1.0。
只返回 JSON，不要额外解释。"""

    @staticmethod
    def _extract_json_blob(text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("no JSON object in LLM response")
        return json.loads(cleaned[start : end + 1])

    def _parse_structured_reflection(self, raw_response: str) -> StructuredReflection:
        data = self._extract_json_blob(raw_response)
        return StructuredReflection(**data)

    @staticmethod
    def _format_structured_reflection(structured: StructuredReflection) -> str:
        parts = [
            f"总体评价：{structured.overall_assessment}",
            f"关键洞见：{structured.key_insight}",
            f"情感-意图对齐：{structured.emotion_intent_alignment}",
        ]
        if structured.strengths:
            parts.append("优点：" + "；".join(structured.strengths[:3]))
        if structured.weaknesses:
            parts.append("不足：" + "；".join(structured.weaknesses[:3]))
        if structured.improvement_suggestions:
            parts.append(
                "改进建议：" + "；".join(structured.improvement_suggestions[:3])
            )
        return " ".join(part for part in parts if part)

    def _generate_rule_based_reflection(
        self,
        *,
        actor_output: str,
        context: Dict[str, Any],
        emotion_state: Dict[str, Any],
        intent_state: List[Dict[str, Any]],
        feedback: Optional[str],
    ) -> str:
        valence = float(emotion_state.get("valence", 0.0))
        emotion_label = emotion_state.get("primary_emotion", "neutral")
        goal_count = len(intent_state)
        query = str(context.get("query", context.get("user_input", "")))[:80]

        emotion_quality = "较好" if valence > 0.1 else "需改进" if valence < -0.1 else "平稳"
        goal_note = f"{goal_count} 个活跃目标" if goal_count else "暂无明确活跃目标"

        parts = [
            f"反思（query={query}）：输出在情感一致性上{emotion_quality}（{emotion_label}）。",
            f"目标推进度：{goal_note}。",
        ]
        if feedback:
            parts.append(f"外部反馈：{feedback[:120]}。")
        if "改进" in emotion_quality or goal_count == 0:
            parts.append("建议：加强情感-意图一致性，并增加主动目标推进。")
        else:
            parts.append("建议：保持当前叙事连贯性，继续推进最高优先级目标。")
        if len(actor_output) < 20:
            parts.append("输出偏短，可增加与长期身份锚点的关联。")
        return " ".join(parts)

    @staticmethod
    def _extract_improvements(reflection_text: str) -> List[str]:
        suggestions: List[str] = []
        if "改进" in reflection_text or "需改进" in reflection_text:
            suggestions.append("加强情感-意图一致性")
        if "主动" in reflection_text:
            suggestions.append("增加主动目标推进")
        if "偏短" in reflection_text:
            suggestions.append("丰富与身份锚点的关联")
        if not suggestions:
            suggestions.append("维持当前稳定性策略")
        return suggestions

    @staticmethod
    def _normalize_coherence_impact(
        llm_value: float,
        emotion_state: Dict[str, Any],
        active_goals: List[Dict[str, Any]],
        feedback: Optional[str],
    ) -> float:
        heuristic = ReflectiveEngine._estimate_coherence_impact(
            emotion_state, active_goals, feedback
        )
        blended = (float(llm_value) * 0.65) + (heuristic * 0.35)
        return round(max(0.0, min(1.0, blended)), 4)

    @staticmethod
    def _estimate_coherence_impact(
        emotion_state: Dict[str, Any],
        active_goals: List[Dict[str, Any]],
        feedback: Optional[str],
    ) -> float:
        valence = float(emotion_state.get("valence", 0.0))
        intensity = float(emotion_state.get("intensity", 0.5))
        base = 0.5 + valence * 0.2 + min(len(active_goals), 3) * 0.05
        if feedback and any(w in feedback.lower() for w in ("bad", "wrong", "差", "不对")):
            base -= 0.15
        return round(max(0.0, min(1.0, base * (0.8 + intensity * 0.2))), 4)

    def _update_narrative_self(
        self,
        record: InteractionReflectionRecord,
        context: Dict[str, Any],
    ) -> None:
        if not self.narrative:
            return
        user_input = str(context.get("user_input", context.get("query", "")))
        self.narrative.update_from_interaction(
            user_input,
            record.actor_output,
            reflection=record.reflection,
            importance=0.7,
        )

    def get_recent_reflections(self, limit: int = 5) -> List[InteractionReflectionRecord]:
        blocks = self.memory.blocks.list_blocks(label=REFLECTIVE_LABEL, active_only=True)
        records: List[InteractionReflectionRecord] = []
        for block in blocks[:limit]:
            parsed = self._load_record(block.content)
            if parsed:
                records.append(parsed)
        return records

    def format_context_block(self, limit: int = 3) -> str:
        recent = self.get_recent_reflections(limit=limit)
        if not recent:
            return "【Reflective Trace】\n• no recent meta-reflections"
        lines = ["【Reflective Trace】"]
        for rec in recent:
            preview = rec.reflection[:160]
            if rec.reflection_mode == "llm" and rec.structured_reflection:
                insight = str(rec.structured_reflection.get("key_insight", ""))[:80]
                if insight:
                    preview = f"[LLM] {insight}"
            lines.append(f"• {preview}")
        return "\n".join(lines)

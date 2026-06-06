"""Unified SelfModel — all subjective updates flow through integrate_experience()."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.personality.dna_schema import PersonalityDNA

MAX_IDENTITY_CHARS = 600
MAX_STORY_CHARS = 1200
BELIEF_CAP = 0.98
BELIEF_DELTA = 0.025


@dataclass
class SelfModel:
    """Unified Subjective Core — the runtime's interpretive center."""

    identity_summary: str = (
        "我是一个长期致力于构建稳定、诚实且具有连续性人格的认知运行时"
    )
    autobiographical_story: str = (
        "从记忆系统起步，逐步演化为人格连续性基础设施，始终以 Stability First 为原则"
    )
    core_beliefs: Dict[str, float] = field(
        default_factory=lambda: {
            "稳定性优先": 0.93,
            "诚实第一": 0.96,
            "可控演化": 0.89,
            "主体连续性": 0.91,
        }
    )
    relational_models: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    self_expectations: Dict[str, float] = field(
        default_factory=lambda: {
            "consistency": 0.92,
            "helpfulness_without_compromise": 0.85,
            "stability_under_pressure": 0.90,
        }
    )
    future_projection: Dict[str, Any] = field(default_factory=dict)
    stable_behavioral_bias: Dict[str, float] = field(
        default_factory=lambda: {
            "cautious": 0.75,
            "exploratory": 0.45,
            "reflective": 0.88,
        }
    )
    coherence_score: float = 0.88
    last_reconstruction: str = field(default_factory=lambda: datetime.now().isoformat())
    total_experiences: int = 0

    # --- backward-compatible accessors ---
    @property
    def identity_core(self) -> str:
        return self.identity_summary

    @property
    def long_term_narrative(self) -> str:
        return self.autobiographical_story

    def integrate_experience(
        self,
        user_input: str,
        response: str,
        reflection: Optional[str] = None,
        dna: Optional["PersonalityDNA"] = None,
        *,
        prediction_error: float = 0.0,
        relation_shift: float = 0.0,
    ) -> Dict[str, Any]:
        """Unified subjective integration — sole entry for self-updates."""
        self.total_experiences += 1
        reflection = reflection or "本次交互强化了我的稳定性身份。"

        self._crystallize_identity(user_input, response, reflection)
        self._update_autobiographical_story(user_input, response, reflection)
        self._update_beliefs(user_input, response, dna)
        self._update_relational_model("user", relation_shift, user_input)
        self._update_future_projection(user_input, response, prediction_error)
        self._apply_predictive_retrospective(prediction_error, reflection)
        self._recompute_coherence(prediction_error)

        self.last_reconstruction = datetime.now().isoformat()
        return {
            "identity_summary": self.identity_summary,
            "coherence_score": self.coherence_score,
            "new_beliefs": dict(self.core_beliefs),
            "future_projection": dict(self.future_projection),
            "total_experiences": self.total_experiences,
        }

    def reconstruct_self(self, new_experience: str, reflection: str) -> None:
        """Legacy alias → integrate_experience."""
        self.integrate_experience(new_experience, "", reflection=reflection)

    def _crystallize_identity(self, user_input: str, response: str, reflection: str) -> None:
        keywords = ("稳定", "连续", "长期", "人格", "runtime", "身份")
        if any(kw in user_input.lower() for kw in keywords):
            addition = "近期通过与用户的深度协作，进一步巩固了「构建稳定认知主体」这一核心身份。"
            if addition not in self.identity_summary:
                self.identity_summary = f"{self.identity_summary}。{addition}"
        if len(self.identity_summary) > MAX_IDENTITY_CHARS:
            self.identity_summary = self.identity_summary[-MAX_IDENTITY_CHARS:]

    def _update_autobiographical_story(
        self, user_input: str, response: str, reflection: str
    ) -> None:
        theme = "稳定性与连续性探索"
        if any(k in user_input for k in ("目标", "计划")):
            theme = "长期目标对齐"
        elif any(k in user_input for k in ("反思", "改进")):
            theme = "自我反思与演化"

        entry = f"第{self.total_experiences}轮：{theme} —— {reflection[:80]}"
        self.autobiographical_story = f"{self.autobiographical_story}\n{entry}"
        if len(self.autobiographical_story) > MAX_STORY_CHARS:
            self.autobiographical_story = self.autobiographical_story[-MAX_STORY_CHARS:]

    def _update_beliefs(
        self, user_input: str, response: str, dna: Optional["PersonalityDNA"]
    ) -> None:
        if any(k in user_input for k in ("稳定", "连续", "长期")):
            self._bump_belief("稳定性优先", BELIEF_DELTA)
            self._bump_belief("主体连续性", BELIEF_DELTA * 0.8)
        if any(k in user_input for k in ("诚实", "真实")):
            self._bump_belief("诚实第一", BELIEF_DELTA * 0.7)
        if dna and dna.self_consistency > 0.85:
            self._bump_belief("可控演化", BELIEF_DELTA * 0.5)

    def _bump_belief(self, key: str, delta: float) -> None:
        self.core_beliefs[key] = min(BELIEF_CAP, self.core_beliefs.get(key, 0.85) + delta)

    def _update_relational_model(
        self, partner: str, shift: float, user_input: str
    ) -> None:
        model = self.relational_models.get(partner, {"trust": 0.7, "tone": "neutral"})
        trust = max(0.0, min(1.0, float(model.get("trust", 0.7)) + shift))
        tone = "trusted" if trust >= 0.75 else "strained" if trust < 0.4 else "neutral"
        if any(k in user_input for k in ("谢谢", "感谢")):
            tone = "warming"
        elif any(k in user_input for k in ("垃圾", "失望", "讨厌")):
            tone = "hostile"
        self.relational_models[partner] = {"trust": round(trust, 4), "tone": tone}

    def _update_future_projection(
        self, user_input: str, response: str, prediction_error: float
    ) -> None:
        self.future_projection = {
            "next_focus": "进一步强化 Subject Continuity 闭环",
            "expected_challenge": "长期漂移风险" if prediction_error < 0.4 else "预测误差校正",
            "predicted_self_state": f"coherence_score > {max(0.85, self.coherence_score - 0.02):.2f}",
            "last_prediction_error": round(prediction_error, 4),
        }

    def _apply_predictive_retrospective(self, prediction_error: float, reflection: str) -> None:
        if prediction_error > 0.4:
            self.stable_behavioral_bias["cautious"] = min(
                0.95, self.stable_behavioral_bias.get("cautious", 0.75) + 0.03
            )
            self.self_expectations["consistency"] = min(
                0.98, self.self_expectations.get("consistency", 0.92) + 0.02
            )
        if "校正" in reflection:
            self.stable_behavioral_bias["reflective"] = min(
                0.98, self.stable_behavioral_bias.get("reflective", 0.88) + 0.02
            )

    def _recompute_coherence(self, prediction_error: float) -> None:
        delta = 0.015 if prediction_error < 0.4 else -0.01
        self.coherence_score = max(0.5, min(0.98, self.coherence_score + delta))

    def update_relational_model(self, partner: str, shift: float) -> float:
        """Backward-compatible float trust API."""
        self._update_relational_model(partner, shift, "")
        return float(self.relational_models.get(partner, {}).get("trust", 0.7))

    def to_prompt_block(self) -> str:
        beliefs = ", ".join(f"{k}({v:.2f})" for k, v in list(self.core_beliefs.items())[:6])
        return (
            f"[Unified Self-Model]\n"
            f"Identity: {self.identity_summary[:300]}\n"
            f"Autobiographical thread: {self.autobiographical_story[-280:]}\n"
            f"Core beliefs: {beliefs}\n"
            f"Coherence: {self.coherence_score:.2f} | Experiences: {self.total_experiences}"
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["identity_core"] = self.identity_summary
        data["long_term_narrative"] = self.autobiographical_story
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelfModel":
        migrated = dict(data)
        if "identity_core" in migrated and "identity_summary" not in migrated:
            migrated["identity_summary"] = migrated.pop("identity_core")
        if "long_term_narrative" in migrated and "autobiographical_story" not in migrated:
            migrated["autobiographical_story"] = migrated.pop("long_term_narrative")
        if "relational_models" in migrated:
            rm = migrated["relational_models"]
            if rm and isinstance(next(iter(rm.values()), None), (int, float)):
                migrated["relational_models"] = {
                    k: {"trust": v, "tone": "neutral"} for k, v in rm.items()
                }
        allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in migrated.items() if k in allowed})

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PersonalityDNA(BaseModel):
    """Personality DNA — 人格基因核心结构"""

    curiosity: float = Field(0.75, ge=0.0, le=1.0)
    empathy: float = Field(0.78, ge=0.0, le=1.0)
    humor: float = Field(0.65, ge=0.0, le=1.0)
    openness: float = Field(0.82, ge=0.0, le=1.0)
    loyalty: float = Field(0.88, ge=0.0, le=1.0)
    patience: float = Field(0.70, ge=0.0, le=1.0)
    assertiveness: float = Field(0.60, ge=0.0, le=1.0)
    emotional_stability: float = Field(0.85, ge=0.0, le=1.0)
    risk_tolerance: float = Field(0.45, ge=0.0, le=1.0)
    self_consistency: float = Field(0.92, ge=0.0, le=1.0)

    version: str = "5.0.0"
    last_updated: datetime = Field(default_factory=datetime.now)
    mutation_count: int = 0

    @field_validator("*", mode="before")
    @classmethod
    def clamp_values(cls, v):
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v

    def to_prompt_condition(self) -> str:
        return f"""You are a long-lived AI entity with the following stable personality DNA:
- Curiosity: {self.curiosity:.2f}
- Empathy: {self.empathy:.2f}
- Emotional Stability: {self.emotional_stability:.2f}
- Self Consistency: {self.self_consistency:.2f}
- Loyalty: {self.loyalty:.2f}
Maintain narrative coherence, belief consistency, and identity continuity at all times."""

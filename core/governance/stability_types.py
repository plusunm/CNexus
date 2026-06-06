from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class DriftReport(BaseModel):
    timestamp: datetime
    drift_score: float = Field(..., ge=0.0, le=1.0)
    drift_type: str
    severity: str
    affected_components: List[str]
    recommended_action: str
    confidence: float


class EntropyReport(BaseModel):
    memory_entropy: float
    belief_entropy: float
    narrative_entropy: float
    overall_entropy: float
    timestamp: datetime


class StabilityMetrics(BaseModel):
    identity_stability: float
    narrative_coherence: float
    belief_consistency: float
    personality_integrity: float
    cognitive_load: float
    entropy_level: float
    overall_stability_score: float

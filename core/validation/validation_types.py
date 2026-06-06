from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class ValidationReport(BaseModel):
    validation_id: str
    timestamp: datetime
    test_type: str
    score: float = Field(..., ge=0.0, le=1.0)
    status: str
    details: Dict
    recommendations: List[str]


class LongTermSimulationResult(BaseModel):
    simulation_days: int
    final_identity_stability: float
    max_drift_score: float
    narrative_coherence_trend: List[float]
    belief_consistency_trend: List[float]
    overall_maturity_score: float

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ReflectionRecord(BaseModel):
    reflection_id: str
    timestamp: datetime
    traits: List[str]
    scene: str
    inner_thought: str
    suggested_methods: List[str]
    action_steps: List[str]
    next_review_date: datetime
    coherence_score: float = Field(0.85, ge=0.0, le=1.0)
    status: str = "active"  # active / reviewed / archived

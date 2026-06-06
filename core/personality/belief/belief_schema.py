from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Belief(BaseModel):
    belief_id: str
    content: str
    confidence: float = Field(0.75, ge=0.0, le=1.0)
    source_memory_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_verified: datetime = Field(default_factory=datetime.now)
    evidence_count: int = 1
    contradiction_score: float = Field(0.0, ge=0.0, le=1.0)


class BeliefGraph(BaseModel):
    beliefs: Dict[str, Belief] = Field(default_factory=dict)
    relations: List[Dict] = Field(default_factory=list)
    version: int = 1
    last_updated: datetime = Field(default_factory=datetime.now)

    def add_belief(self, belief: Belief):
        self.beliefs[belief.belief_id] = belief
        self.last_updated = datetime.now()
        self.version += 1

    def update_confidence(self, belief_id: str, new_confidence: float):
        if belief_id in self.beliefs:
            self.beliefs[belief_id].confidence = max(0.1, min(1.0, new_confidence))
            self.beliefs[belief_id].last_verified = datetime.now()

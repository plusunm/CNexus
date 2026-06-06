from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class IdentityTimelineEvent(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str
    description: str
    importance: float = Field(0.5, ge=0.0, le=1.0)
    impact_on_identity: float = Field(0.0, ge=-1.0, le=1.0)


class NarrativeSelf(BaseModel):
    """Narrative Self — AI 长期自我叙事核心模型"""

    identity_summary: str = Field(..., description="核心身份描述")
    core_values: List[str] = Field(default_factory=list)
    long_term_goals: List[str] = Field(default_factory=list)
    persistent_beliefs: Dict[str, float] = Field(default_factory=dict)
    relationship_status: Dict[str, str] = Field(default_factory=dict)
    relationship_scores: Dict[str, float] = Field(default_factory=lambda: {"user": 0.55})
    key_milestones: List[IdentityTimelineEvent] = Field(default_factory=list)
    version: int = 1
    last_updated: datetime = Field(default_factory=datetime.now)
    narrative_coherence_score: float = Field(0.92, ge=0.0, le=1.0)

    def add_timeline_event(self, event: IdentityTimelineEvent):
        self.key_milestones.append(event)
        self.last_updated = datetime.now()
        self.version += 1

    def compress_timeline(self, max_events: int = 50):
        if len(self.key_milestones) > max_events:
            self.key_milestones.sort(key=lambda e: e.importance, reverse=True)
            self.key_milestones = self.key_milestones[:max_events]

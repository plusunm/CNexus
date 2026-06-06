from datetime import datetime
from typing import Dict, List, Optional

from core.personality.reflective.reflective_memory import ReflectionRecord


class ReviewScheduler:
    """安排定期复盘"""

    def __init__(self):
        self.pending_reviews: List[ReflectionRecord] = []
        self.history: List[Dict] = []

    def schedule_review(self, record: ReflectionRecord):
        self.pending_reviews.append(record)
        self.history.append(
            {
                "reflection_id": record.reflection_id,
                "scheduled_at": datetime.now().isoformat(),
                "next_review_date": record.next_review_date.isoformat(),
                "traits": record.traits,
            }
        )

    def due_reviews(self, now: Optional[datetime] = None) -> List[ReflectionRecord]:
        now = now or datetime.now()
        due = [r for r in self.pending_reviews if r.next_review_date <= now and r.status == "active"]
        return due

    def mark_reviewed(self, reflection_id: str):
        for r in self.pending_reviews:
            if r.reflection_id == reflection_id:
                r.status = "reviewed"
                break

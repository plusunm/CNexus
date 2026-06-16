from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.deps import get_dispatcher

router = APIRouter(prefix="/reflective", tags=["reflective"])


class ReflectionRequest(BaseModel):
    content: str
    traits: Optional[List[str]] = None


class ReflectionResponse(BaseModel):
    reflection_id: str
    traits: List[str]
    scene: str
    inner_thought: str
    suggested_methods: List[str]
    action_steps: List[str]
    next_review_date: str
    coherence_score: float


@router.post("/reflect", response_model=ReflectionResponse)
async def trait_reflection(req: ReflectionRequest):
    record = get_dispatcher().reflect_review(content=req.content, traits=req.traits)
    if isinstance(record, dict):
        return ReflectionResponse(
            reflection_id=str(record.get("reflection_id", "")),
            traits=list(record.get("traits") or []),
            scene=str(record.get("scene", "")),
            inner_thought=str(record.get("inner_thought", "")),
            suggested_methods=list(record.get("suggested_methods") or []),
            action_steps=list(record.get("action_steps") or []),
            next_review_date=str(record.get("next_review_date", "")),
            coherence_score=float(record.get("coherence_score", 0.0)),
        )
    return ReflectionResponse(
        reflection_id=record.reflection_id,
        traits=record.traits,
        scene=record.scene,
        inner_thought=record.inner_thought,
        suggested_methods=record.suggested_methods,
        action_steps=record.action_steps,
        next_review_date=record.next_review_date.isoformat(),
        coherence_score=record.coherence_score,
    )


@router.get("/active")
async def active_reflections():
    return get_dispatcher().observe_read("active_reflections")


@router.get("/due-reviews")
async def due_reviews():
    return get_dispatcher().reflect_due_reviews()

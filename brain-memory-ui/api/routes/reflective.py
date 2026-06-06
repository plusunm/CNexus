from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.deps import get_runtime

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
    record = get_runtime().trait_based_reflection(req.content, req.traits)
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
    records = get_runtime().reflection_pipeline.get_active_reflections()
    return {"reflections": [r.model_dump(mode="json") for r in records]}


@router.get("/due-reviews")
async def due_reviews():
    records = get_runtime().reflection_pipeline.run_due_reviews()
    return {"due": [r.model_dump(mode="json") for r in records]}

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_llm, get_registry, get_runtime
from core.model_registry import ModelProfile, to_public

router = APIRouter(prefix="/memory", tags=["memory"])


class CaptureRequest(BaseModel):
    role: str = "user"
    content: str
    layer: str = "episodic"
    importance: float = Field(0.5, ge=0.0, le=1.0)


class CaptureResponse(BaseModel):
    memory_id: str
    status: str


class RecallResponse(BaseModel):
    context: str


@router.post("/capture", response_model=CaptureResponse)
async def capture(data: CaptureRequest):
    result = get_runtime().capture(
        data.role, data.content, layer=data.layer, importance=data.importance
    )
    if isinstance(result, str) and result.startswith("denied"):
        raise HTTPException(400, result)
    return CaptureResponse(memory_id=str(result), status="success")


@router.get("/recall", response_model=RecallResponse)
async def recall(query: str):
    return RecallResponse(context=get_runtime().recall(query))

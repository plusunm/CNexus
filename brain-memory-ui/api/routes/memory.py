from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_llm, get_registry, get_runtime
from api.runtime_log import runtime_log
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
        runtime_log("warn", "capture", "Write gate denied", reason=result)
        raise HTTPException(400, result)
    runtime_log("info", "capture", "Memory captured", layer=data.layer, id=str(result)[:16])
    return CaptureResponse(memory_id=str(result), status="success")


@router.get("/recall", response_model=RecallResponse)
async def recall(query: str):
    ctx = get_runtime().recall(query)
    runtime_log("debug", "recall", "Recall query", query=query[:60], chars=len(ctx))
    return RecallResponse(context=ctx)

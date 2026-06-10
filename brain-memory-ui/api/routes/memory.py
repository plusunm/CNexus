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


class MemoryStatsResponse(BaseModel):
    total: int
    by_layer: dict
    avg_importance: float
    avg_decay_factor: float
    high_access_count: int


class MaintenanceResponse(BaseModel):
    decayed: int
    forgotten: int
    evicted_capacity: int
    capped_access: int
    remaining: int
    details: list


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


@router.get("/stats", response_model=MemoryStatsResponse)
async def memory_stats():
    stats = get_runtime().memory_stats()
    runtime_log("info", "memory_mgmt", "Stats collected", total=stats.get("total", 0))
    return MemoryStatsResponse(**stats)


@router.post("/maintenance", response_model=MaintenanceResponse)
async def memory_maintenance(force: bool = False):
    report = get_runtime().run_memory_maintenance(force=force)
    if report.get("skipped"):
        raise HTTPException(400, report.get("reason", "metabolic disabled"))
    runtime_log(
        "info",
        "memory_mgmt",
        "Maintenance complete",
        forgotten=report.get("forgotten", 0),
        remaining=report.get("remaining", 0),
    )
    return MaintenanceResponse(**report)

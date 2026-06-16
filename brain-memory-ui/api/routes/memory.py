from typing import Any, Dict, List, Optional

import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from api.deps import get_dispatcher, get_runtime
from api.runtime_log import runtime_log
from core.document.ingest import DocumentParseError, parse_document_bytes

router = APIRouter(prefix="/memory", tags=["memory"])


class CaptureRequest(BaseModel):
    role: str = "user"
    content: str
    layer: str = "episodic"
    importance: float = Field(0.5, ge=0.0, le=1.0)
    cognize: Optional[bool] = None


class CaptureResponse(BaseModel):
    memory_id: str
    status: str
    cognition: Optional[Dict[str, Any]] = None


class IngestResponse(BaseModel):
    memory_id: str
    status: str
    filename: str
    format: str
    char_count: int
    preview: str
    truncated: bool = False
    keywords: List[str] = Field(default_factory=list)
    cognition: Optional[Dict[str, Any]] = None


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


class EmbeddingStatusResponse(BaseModel):
    configured_mode: str
    active_mode: str
    ollama_reachable: bool
    model: str
    host: str
    used_on: list[str]
    not_used_on: list[str]


def _resolve_capture_cognize(runtime, requested: Optional[bool]) -> bool:
    if requested is not None:
        return requested
    return bool(runtime.config.get("capture_cognize_default", True))


@router.get("/embedding-status", response_model=EmbeddingStatusResponse)
async def embedding_status():
    runtime = get_runtime()
    return EmbeddingStatusResponse(**runtime.embedder.status_payload())


@router.post("/capture", response_model=CaptureResponse)
async def capture(data: CaptureRequest):
    runtime = get_runtime()
    cognize = _resolve_capture_cognize(runtime, data.cognize)
    result = get_dispatcher().memory_capture(
        data.role,
        data.content,
        layer=data.layer,
        importance=data.importance,
    )
    if isinstance(result, str) and result.startswith("denied"):
        runtime_log("warn", "capture", "Write gate denied", reason=result)
        raise HTTPException(400, result)

    memory_id = str(result.get("episodic_id") if isinstance(result, dict) else result)
    cognition = None
    if cognize:
        try:
            cognition = get_dispatcher().capture_cognition(
                content=data.content,
                layer=data.layer,
                memory_id=memory_id,
                trigger_governance=cognize,
            )
        except Exception as exc:
            runtime_log(
                "warn",
                "capture",
                "Cognition side-effect failed — memory write kept",
                error=str(exc),
                memory_id=memory_id[:16],
            )

    runtime_log(
        "info",
        "capture",
        "Memory captured",
        layer=data.layer,
        id=memory_id[:16],
        cognize=cognize,
    )
    return CaptureResponse(memory_id=memory_id, status="success", cognition=cognition)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    layer: str = Form("episodic"),
    importance: float = Form(0.7),
    cognize: Optional[bool] = Form(None),
    goal: Optional[str] = Form(None),
):
    runtime = get_runtime()
    raw = await file.read()
    filename = file.filename or "upload"

    try:
        parsed = parse_document_bytes(filename, raw)
    except DocumentParseError as exc:
        runtime_log("warn", "ingest", "Document parse failed", filename=filename, code=exc.code)
        raise HTTPException(400, {"code": exc.code, "message": str(exc)}) from exc

    text = str(parsed.get("text") or "").strip()
    if goal and goal.strip():
        text = f"[goal:{goal.strip()}] {text}"

    cognize_resolved = _resolve_capture_cognize(runtime, cognize)
    result = await asyncio.to_thread(
        get_dispatcher().memory_capture,
        "user",
        text,
        layer=layer,
        importance=importance,
    )
    if isinstance(result, str) and result.startswith("denied"):
        runtime_log("warn", "ingest", "Write gate denied", reason=result, filename=filename)
        raise HTTPException(400, result)

    memory_id = str(result.get("episodic_id") if isinstance(result, dict) else result)
    cognition = None
    keywords = list(parsed.get("keywords") or [])
    if cognize_resolved:
        try:
            cognition = get_dispatcher().capture_cognition(
                content=text,
                layer=layer,
                memory_id=memory_id,
                trigger_governance=cognize_resolved,
            )
            traits = cognition.get("traits") if isinstance(cognition, dict) else None
            if traits:
                keywords = list(dict.fromkeys([*keywords, *[str(t) for t in traits]]))[:12]
        except Exception as exc:
            runtime_log(
                "warn",
                "ingest",
                "Cognition side-effect failed — memory write kept",
                error=str(exc),
                memory_id=memory_id[:16],
                filename=filename,
            )

    preview = text[:240]
    runtime_log(
        "info",
        "ingest",
        "Document ingested",
        filename=filename,
        format=parsed.get("format"),
        chars=parsed.get("char_count"),
        id=memory_id[:16],
        cognize=cognize_resolved,
    )
    return IngestResponse(
        memory_id=memory_id,
        status="success",
        filename=str(parsed.get("filename") or filename),
        format=str(parsed.get("format") or "unknown"),
        char_count=int(parsed.get("char_count") or len(text)),
        preview=preview,
        truncated=bool(parsed.get("truncated")),
        keywords=keywords,
        cognition=cognition,
    )


@router.get("/recall", response_model=RecallResponse)
async def recall(query: str):
    ctx = get_dispatcher().memory_recall(query)
    runtime_log("debug", "recall", "Recall query", query=query[:60], chars=len(ctx))
    return RecallResponse(context=ctx)


@router.get("/stats", response_model=MemoryStatsResponse)
async def memory_stats():
    from api.deps import get_runtime
    from core.runtime.event_loop_offload import offload_sync

    stats = await offload_sync(lambda: get_runtime().memory_stats())
    runtime_log("info", "memory_mgmt", "Stats collected", total=stats.get("total", 0))
    return MemoryStatsResponse(**stats)


@router.post("/maintenance", response_model=MaintenanceResponse)
async def memory_maintenance(force: bool = False):
    report = get_dispatcher().memory_maintenance(force=force)
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

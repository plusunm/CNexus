from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.deps import get_registry, get_runtime
from api.runtime_log import runtime_log

router = APIRouter(prefix="/execution", tags=["execution"])


class ProviderHealthResponse(BaseModel):
    state: str
    capabilities: List[str]
    reachable: bool
    issues: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class ExecutionStatusResponse(BaseModel):
    """Provider selection hint — not a cognition gate."""

    active_chat_provider: Optional[str] = None
    active_embed_provider: Optional[str] = None
    providers: Dict[str, ProviderHealthResponse]
    suggested_actions: List[str] = Field(default_factory=list)
    embedding: Dict[str, Any] = Field(default_factory=dict)
    ollama: Dict[str, Any] = Field(default_factory=dict)
    runtime_mode: Optional[str] = None
    runtime_envelope: Optional[str] = None
    compute_profile: Dict[str, Any] = Field(default_factory=dict)
    compute_policy: Dict[str, Any] = Field(default_factory=dict)
    inference_scheduler: Dict[str, Any] = Field(default_factory=dict)


class BootstrapRequest(BaseModel):
    models: Optional[List[str]] = None


class BootstrapResponse(BaseModel):
    ok: bool
    detail: str
    results: List[Dict[str, Any]] = Field(default_factory=list)


@router.get("/status", response_model=ExecutionStatusResponse)
async def execution_status():
    import asyncio

    from api.deps import peek_runtime
    from core.ollama_manager import get_ollama_status

    runtime = peek_runtime()
    if runtime is None:
        ollama = await asyncio.to_thread(get_ollama_status)
        return ExecutionStatusResponse(
            active_chat_provider=None,
            active_embed_provider=None,
            providers={},
            suggested_actions=[
                "Runtime 正在初始化，请等待约 1–2 分钟",
                "若长时间无响应：悬浮窗 → 连接服务 → 重新连接运行时",
            ],
            embedding={},
            ollama=ollama,
            runtime_mode="warming",
        )

    registry = get_registry()
    payload, embedding, ollama = await asyncio.gather(
        asyncio.to_thread(runtime.local_stack.readiness_dict, registry=registry),
        asyncio.to_thread(runtime.embedder.status_payload),
        asyncio.to_thread(runtime.local_stack.ollama_status),
    )
    return ExecutionStatusResponse(
        active_chat_provider=payload.get("active_chat_provider"),
        active_embed_provider=payload.get("active_embed_provider"),
        providers={
            pid: ProviderHealthResponse(**health)
            for pid, health in (payload.get("providers") or {}).items()
        },
        suggested_actions=list(payload.get("suggested_actions") or []),
        embedding=embedding,
        ollama=ollama,
        runtime_mode=str(runtime.config.get("runtime_mode") or "auto"),
        runtime_envelope=str(runtime.config.get("runtime_envelope") or ""),
        compute_profile=(runtime.compute_profile.to_dict() if runtime.compute_profile else {}),
        compute_policy=(runtime.compute_policy.to_dict() if runtime.compute_policy else {}),
        inference_scheduler=runtime.inference_scheduler.stats_payload(),
    )


@router.post("/bootstrap", response_model=BootstrapResponse)
async def execution_bootstrap(req: BootstrapRequest):
    runtime = get_runtime()
    runtime_log("info", "execution", "Model bootstrap requested", models=req.models)
    report = runtime.local_stack.ensure_models(req.models)
    return BootstrapResponse(
        ok=bool(report.get("ok")),
        detail=str(report.get("detail", "")),
        results=list(report.get("results") or []),
    )

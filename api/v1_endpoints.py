"""CNexus v0.1/v0.2 spec REST layer — thin facade over BrainMemoryRuntime."""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from brain_memory import BrainMemoryRuntime

RuntimeProvider = Callable[[], BrainMemoryRuntime]
LLMProvider = Callable[[], Any]
RegistryProvider = Callable[[], Any]

_runtime_provider: Optional[RuntimeProvider] = None
_llm_provider: Optional[LLMProvider] = None
_registry_provider: Optional[RegistryProvider] = None

router = APIRouter(tags=["v1-spec"])


def configure_v1_dependencies(
    *,
    get_runtime: RuntimeProvider,
    get_llm: Optional[LLMProvider] = None,
    get_registry: Optional[RegistryProvider] = None,
) -> None:
    global _runtime_provider, _llm_provider, _registry_provider
    _runtime_provider = get_runtime
    _llm_provider = get_llm
    _registry_provider = get_registry


def _resolve_runtime() -> BrainMemoryRuntime:
    if _runtime_provider is None:
        from brain_memory import create_runtime

        return create_runtime()
    return _runtime_provider()


def get_runtime() -> BrainMemoryRuntime:
    return _resolve_runtime()


class InteractRequest(BaseModel):
    user_id: str = Field(..., description="用户唯一标识")
    session_id: Optional[str] = Field(None, description="会话 ID")
    message: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InteractResponse(BaseModel):
    response: str
    enriched_context: Dict[str, Any] = Field(default_factory=dict)
    memory_blocks_updated: List[str] = Field(default_factory=list)
    governance_pass: bool = True
    reflection: Optional[str] = None
    provenance_id: str = Field(default_factory=lambda: f"prov_{uuid.uuid4().hex[:12]}")
    coherence_score: Optional[float] = None
    emotion_state: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class StateResponse(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    blocks_summary: Dict[str, Any] = Field(default_factory=dict)
    attention_state: Dict[str, Any] = Field(default_factory=dict)
    governance: Dict[str, Any] = Field(default_factory=dict)
    full_status: Dict[str, Any] = Field(default_factory=dict)


class RecallRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(8, ge=1, le=50)
    include_episodic: bool = True


class RecallResponse(BaseModel):
    query: str
    context: str
    recall_stats: Dict[str, Any] = Field(default_factory=dict)


class GovernanceCheckResponse(BaseModel):
    governance_pass: bool = True
    report: Dict[str, Any] = Field(default_factory=dict)
    audit_hint: Optional[str] = None


def _format_reflection(result: Dict[str, Any]) -> Optional[str]:
    if result.get("reflection"):
        return str(result["reflection"])
    meta = result.get("meta_reflection")
    if isinstance(meta, dict):
        for key in ("inner_thought", "scene", "summary"):
            if meta.get(key):
                return str(meta[key])
    return None


def _infer_memory_blocks_updated(result: Dict[str, Any]) -> List[str]:
    labels: List[str] = []
    if result.get("emotion_state"):
        labels.append("emotion")
    if result.get("active_intent"):
        labels.append("intent")
    if result.get("meta_reflection"):
        labels.append("reflective_trace")
    if result.get("value_alignment"):
        labels.append("value_alignment_history")
    if result.get("ok", True):
        labels.extend(["persona", "working_memory", "attention_state"])
    return sorted(set(labels))


def _build_enriched_context(result: Dict[str, Any], req: InteractRequest) -> Dict[str, Any]:
    return {
        "context_preview": (result.get("context") or "")[:2000],
        "working_self": result.get("working_self"),
        "self_model": result.get("self_model"),
        "user_id": req.user_id,
        "session_id": req.session_id,
        "request_context": req.context or {},
    }


def _provenance_id(result: Dict[str, Any]) -> str:
    for key in ("capture_id", "grounding_event_id"):
        value = result.get(key)
        if value:
            return str(value)
    cdg = result.get("cdg") or {}
    if cdg.get("event_id"):
        return str(cdg["event_id"])
    return f"prov_{uuid.uuid4().hex[:12]}"


def _map_interact_response(result: Dict[str, Any], req: InteractRequest) -> InteractResponse:
    governance_pass = bool(result.get("ok", True))
    return InteractResponse(
        response=result.get("reply") or result.get("response") or "",
        enriched_context=_build_enriched_context(result, req),
        memory_blocks_updated=_infer_memory_blocks_updated(result),
        governance_pass=governance_pass,
        reflection=_format_reflection(result),
        provenance_id=_provenance_id(result),
        coherence_score=result.get("coherence_score"),
        emotion_state=result.get("emotion_state"),
        meta={
            "active_intent": result.get("active_intent"),
            "value_alignment": result.get("value_alignment"),
            "proactive": result.get("proactive"),
            "cdg": result.get("cdg"),
            "reason": result.get("reason"),
        },
    )


@router.post("/interact", response_model=InteractResponse)
async def v1_interact(
    req: InteractRequest,
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """POST /v1/interact — canonical interaction entry."""
    options = req.options or {}
    use_memory = bool(options.get("use_memory", options.get("enable_memory", True)))
    temperature = float(options.get("temperature", 0.7))
    allow_proactive = options.get("governance_level", "normal") != "strict"
    if options.get("governance_strict") is True:
        allow_proactive = False

    llm_client = None
    llm_profile = None
    if _llm_provider and _registry_provider:
        registry = _registry_provider()
        llm_profile = registry.get_default()
        if llm_profile is None or not llm_profile.enabled:
            raise HTTPException(status_code=400, detail="No LLM model configured for /v1/interact")
        llm_client = _llm_provider()

    try:
        result = runtime.process_interaction(
            req.message,
            use_memory=use_memory,
            temperature=temperature,
            llm_client=llm_client,
            llm_profile=llm_profile,
            allow_proactive=allow_proactive,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "runtime_error",
                "code": "INTERNAL_ERROR",
                "safe_response": "抱歉，处理请求时出现错误。",
                "audit_id": f"audit_{uuid.uuid4().hex[:8]}",
                "detail": str(exc),
            },
        ) from exc

    response = _map_interact_response(result, req)
    if not response.governance_pass:
        response.meta["governance_violation"] = {
            "error": "governance_violation",
            "code": "GOVERNANCE_BLOCKED",
            "safe_response": response.response,
            "audit_id": response.provenance_id,
            "reason": result.get("reason"),
        }
    return response


@router.get("/state", response_model=StateResponse)
async def v1_state(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """GET /v1/state — read-only SubjectSelf + block/governance summary."""
    try:
        full_status = runtime.get_full_status()
        current = runtime.get_current_state()
        blocks_summary = full_status.get("layers", {}).get("memory_blocks", {})
        if not blocks_summary:
            blocks_summary = runtime.memory_manager.block_stats()
        attention_state = runtime.memory_manager.get_attention_snapshot()
        governance = full_status.get("layers", {}).get("governance", {})
        if not governance:
            governance = {
                "stability_metrics": current.get("stability_metrics", {}),
                "cdg": current.get("cdg"),
            }
        return StateResponse(
            user_id=user_id,
            session_id=session_id,
            blocks_summary=blocks_summary,
            attention_state=attention_state,
            governance=governance,
            full_status=full_status,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@router.get("/memory/blocks")
async def v1_memory_blocks(
    label: Optional[str] = None,
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """GET /v1/memory/blocks — list active MemoryBlocks."""
    manager = runtime.memory_manager
    if label:
        block = manager.get_active_block(label, touch=False)
        blocks = [block] if block else []
    else:
        blocks = manager.blocks.list_blocks(active_only=True, label=label)

    return {
        "blocks": [
            {
                "block_id": block.block_id,
                "label": block.label,
                "description": block.description,
                "content": block.content[:500],
                "importance": block.importance,
                "version": block.version,
                "category": block.category,
                "governance_status": block.governance_status,
                "updated_at": block.updated_at.isoformat(),
            }
            for block in blocks
        ],
        "stats": manager.block_stats(),
        "label_filter": label,
    }


@router.post("/memory/recall", response_model=RecallResponse)
async def v1_memory_recall(
    req: RecallRequest,
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """POST /v1/memory/recall — hierarchical recall debug endpoint."""
    context = runtime.recall(req.query, top_k=req.top_k)
    stats = {}
    if hasattr(runtime, "router") and hasattr(runtime.router, "get_stats"):
        stats = runtime.router.get_stats()
    return RecallResponse(query=req.query, context=context, recall_stats=stats)


@router.get("/governance/audit")
async def v1_governance_audit(
    last_n: int = 20,
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """GET /v1/governance/audit — CDG trajectory + provenance hint (read-only)."""
    trajectory = runtime.cdg.trajectory_report(last_n=last_n)
    audit_path = getattr(runtime.cdg, "audit_log_path", None)
    return {
        "trajectory": trajectory,
        "audit_log_path": str(audit_path) if audit_path else None,
        "read_only": True,
    }


@router.post("/governance/check", response_model=GovernanceCheckResponse)
async def v1_governance_check(
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """POST /v1/governance/check — run stability governance cycle."""
    report = runtime.run_governance_cycle()
    score = report.get("stability_metrics", {}).get("overall_stability_score", 1.0)
    governance_pass = float(score or 0.0) >= 0.5
    return GovernanceCheckResponse(
        governance_pass=governance_pass,
        report=report,
        audit_hint=str(getattr(runtime.cdg, "audit_log_path", "")) or None,
    )

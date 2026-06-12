"""CNexus v1.0/v1.1 spec REST layer — thin facade over BrainMemoryRuntime."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

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
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(None, description="会话 ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("session_id"):
            meta = data.get("metadata") or {}
            if isinstance(meta, dict) and meta.get("session_id"):
                data["session_id"] = meta["session_id"]
        return data


class InteractResponse(BaseModel):
    response: str
    enriched_context: Dict[str, Any] = Field(default_factory=dict)
    memory_blocks_updated: List[str] = Field(default_factory=list)
    governance_pass: bool = True
    reflection: Optional[str] = None
    reflection_triggered: bool = False
    provenance_id: str = Field(default_factory=lambda: f"prov_{uuid.uuid4().hex[:12]}")
    provenance: Dict[str, Any] = Field(default_factory=dict)
    attention_state: Dict[str, Any] = Field(default_factory=dict)
    coherence_score: Optional[float] = None
    emotion_state: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class StatusV11Response(BaseModel):
    layers: Dict[str, Any] = Field(default_factory=dict)
    attention: Dict[str, Any] = Field(default_factory=dict)
    stability: str = "healthy"


class CaptureRequest(BaseModel):
    user_id: str
    role: str = "user"
    content: str = Field(..., min_length=1)
    layer: str = "episodic"
    importance: float = Field(0.5, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CaptureResponse(BaseModel):
    memory_id: str
    status: str = "success"
    block_label: Optional[str] = None


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
    attention = result.get("attention_state") or {}
    focus_scores = attention.get("focus_scores") or {}
    if "user_profile" in focus_scores:
        labels.append("user_profile")
    if result.get("ok", True):
        labels.extend(["persona", "working_memory", "attention_state"])
    return sorted(set(labels))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _provenance_id(result: Dict[str, Any], user_id: Optional[str] = None) -> str:
    for key in ("capture_id", "grounding_event_id"):
        value = result.get(key)
        if value:
            return str(value)
    cdg = result.get("cdg") or {}
    if cdg.get("event_id"):
        return str(cdg["event_id"])
    suffix = user_id or "anon"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"trace_{ts}_{suffix}"


def _build_governance_provenance(result: Dict[str, Any]) -> Dict[str, Any]:
    ok = bool(result.get("ok", True))
    cdg = result.get("cdg") or {}
    cdg_intercept = bool(cdg) and not cdg.get("approved", True)
    deliberation_revised = not ok and bool(result.get("reason")) and not cdg_intercept
    if ok and not cdg_intercept:
        values_check = "passed"
        revision_note = None
    else:
        values_check = "revised"
        revision_note = result.get("reason")
    return {
        "values_check": values_check,
        "cdg_intercept": cdg_intercept,
        "revision_note": revision_note,
        "reason": result.get("reason") if values_check == "revised" else None,
        "deliberation_revised": deliberation_revised,
    }


def _infer_episodic_layers(runtime: BrainMemoryRuntime, result: Dict[str, Any]) -> List[int]:
    layers: List[int] = []
    router = getattr(runtime, "router", None)
    if router is not None and hasattr(router, "get_stats"):
        sources = router.get_stats().get("sources") or {}
        if sources.get("block") or sources.get("memory_block"):
            layers.extend([1, 2])
        storage_sources = {"vector", "graph", "storage", "lance", "kuzu", "episodic"}
        if storage_sources & set(sources.keys()):
            layers.extend([3, 4, 5, 6, 7, 8])
    if not layers and result.get("context"):
        layers = [3, 5]
    return sorted(set(layers))


def _build_attention_state(runtime: BrainMemoryRuntime, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if result and result.get("attention_state"):
        return dict(result["attention_state"])
    snapshot = runtime.memory_manager.get_attention_snapshot()
    if not snapshot:
        return {}
    block = runtime.attention_state_block
    priority = int(getattr(block, "priority", 4)) if block is not None else 4
    focus_scores = snapshot.get("focus_scores") or {}
    top_focus = snapshot.get("top_focus") or list(focus_scores.keys())[:3]
    return {
        "focus": " + ".join(str(item) for item in top_focus) or "balanced",
        "priority": priority,
        "focus_scores": focus_scores,
        "dynamic_field": {
            "recent_topics": [str(item).replace("_", " ") for item in top_focus[:5]],
        },
        "last_sync_turn": snapshot.get("last_sync_turn"),
    }


def _build_provenance(
    result: Dict[str, Any],
    blocks_used: List[str],
    *,
    runtime: BrainMemoryRuntime,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "trace_id": _provenance_id(result, user_id=user_id),
        "blocks_used": blocks_used,
        "episodic_layers": _infer_episodic_layers(runtime, result),
        "governance": _build_governance_provenance(result),
        "timestamp": _utc_now_iso(),
    }


def _build_enriched_context(result: Dict[str, Any], req: InteractRequest) -> Dict[str, Any]:
    return {
        "context_preview": (result.get("context") or "")[:2000],
        "working_self": result.get("working_self"),
        "self_model": result.get("self_model"),
        "user_id": req.user_id,
        "session_id": req.session_id,
        "request_context": req.context or {},
    }


def _map_interact_response(
    result: Dict[str, Any],
    req: InteractRequest,
    runtime: BrainMemoryRuntime,
) -> InteractResponse:
    governance_pass = bool(result.get("ok", True))
    blocks_used = _infer_memory_blocks_updated(result)
    provenance_id = _provenance_id(result, user_id=req.user_id)
    return InteractResponse(
        response=result.get("reply") or result.get("response") or "",
        enriched_context=_build_enriched_context(result, req),
        memory_blocks_updated=blocks_used,
        governance_pass=governance_pass,
        reflection=_format_reflection(result),
        reflection_triggered=bool(result.get("reflection_triggered")),
        provenance_id=provenance_id,
        provenance=_build_provenance(
            result,
            blocks_used,
            runtime=runtime,
            user_id=req.user_id,
        ),
        attention_state=_build_attention_state(runtime, result),
        coherence_score=result.get("coherence_score"),
        emotion_state=result.get("emotion_state"),
        meta={
            "active_intent": result.get("active_intent"),
            "value_alignment": result.get("value_alignment"),
            "proactive": result.get("proactive"),
            "cdg": result.get("cdg"),
            "reason": result.get("reason"),
            "user_id": req.user_id,
            "session_id": req.session_id,
        },
    )


@router.post("/interact", response_model=InteractResponse)
async def v1_interact(
    req: InteractRequest,
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """POST /v1/interact — canonical interaction entry."""
    options = req.options or {}
    meta = dict(req.metadata or {})
    if req.session_id:
        meta.setdefault("session_id", req.session_id)
    use_memory = bool(
        options.get("use_memory", options.get("enable_memory", meta.get("enable_memory", True)))
    )
    temperature = float(options.get("temperature", 0.7))
    allow_proactive = options.get("governance_level", "normal") != "strict"
    if options.get("governance_strict") is True:
        allow_proactive = False
    strict_error = bool(options.get("strict_governance_error", False))

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
            user_id=req.user_id,
            metadata=meta,
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

    response = _map_interact_response(result, req, runtime)
    if not response.governance_pass:
        if strict_error:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "governance_intercept",
                    "message": "请求被 L5 ValuesGovernance 修订",
                    "revised_response": response.response,
                    "provenance": response.provenance,
                },
            )
        response.meta["governance_violation"] = {
            "error": "governance_violation",
            "code": "GOVERNANCE_BLOCKED",
            "safe_response": response.response,
            "audit_id": response.provenance_id,
            "reason": result.get("reason"),
        }
    return response


def _build_status_v11(runtime: BrainMemoryRuntime) -> StatusV11Response:
    full_status = runtime.get_full_status()
    current = runtime.get_current_state()
    block_stats = full_status.get("layers", {}).get("memory_blocks") or runtime.memory_manager.block_stats()
    by_label = dict(block_stats.get("by_label") or {})
    store_stats = {}
    blocks = runtime.memory_manager.blocks
    if hasattr(blocks, "stats"):
        store_stats = blocks.stats()

    memory_blocks = {label: count for label, count in by_label.items()}
    if runtime.attention_state_block is not None or store_stats.get("has_attention_snapshot"):
        memory_blocks.setdefault("attention_state", "dynamic")

    episodic_counts = store_stats.get("episodic_counts") or {}
    active_layers = len([count for count in episodic_counts.values() if count > 0]) or 8
    mem_stats = runtime.memory_stats() if hasattr(runtime, "memory_stats") else {}
    total_events = mem_stats.get("total_memories") or mem_stats.get("episodic_count") or sum(
        episodic_counts.values()
    )

    gov_layer = full_status.get("layers", {}).get("governance") or {}
    stability_metrics = current.get("stability_metrics") or {}
    drift_score = round(1.0 - float(stability_metrics.get("overall_stability_score", 0.98)), 4)
    score = float(stability_metrics.get("overall_stability_score", gov_layer.get("overall_stability", 0.98)))
    if score >= 0.75:
        stability = "healthy"
    elif score >= 0.5:
        stability = "degraded"
    else:
        stability = "critical"

    attention_payload = _build_attention_state(runtime)
    return StatusV11Response(
        layers={
            "memory_blocks": memory_blocks,
            "episodic": {
                "active_layers": active_layers,
                "total_events": total_events,
            },
            "governance": {
                "drift_score": drift_score,
                "last_values_check": _utc_now_iso(),
            },
        },
        attention={
            "current_focus": attention_payload.get("focus", "balanced"),
            "priority": attention_payload.get("priority", 4),
            "dynamic_field": attention_payload.get("dynamic_field", {}),
        },
        stability=stability,
    )


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


@router.get("/status", response_model=StatusV11Response)
async def v1_status(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """GET /v1/status — v1.1 runtime summary (CLI parity)."""
    try:
        return _build_status_v11(runtime)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@router.post("/capture", response_model=CaptureResponse)
async def v1_capture(
    req: CaptureRequest,
    runtime: BrainMemoryRuntime = Depends(get_runtime),
):
    """POST /v1/capture — metadata-aware capture entry."""
    meta = dict(req.metadata or {})
    meta.update({"user_id": req.user_id, "session_id": meta.get("session_id")})
    result = runtime.capture(
        req.role,
        req.content,
        layer=req.layer,
        importance=req.importance,
        return_detail=True,
        **meta,
    )
    if isinstance(result, str):
        if result.startswith("denied"):
            raise HTTPException(status_code=400, detail=result)
        return CaptureResponse(memory_id=result, status="success")
    return CaptureResponse(
        memory_id=str(result.get("episodic_id") or result.get("capture_id") or ""),
        status="success",
        block_label=result.get("block_label"),
    )


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

import asyncio
import time

from typing import Any, Dict, List, Literal, Optional



from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field



from api.deps import get_dispatcher, get_llm, get_registry, get_runtime

from api.runtime_log import runtime_log

from core.governance.cdg import snapshot_cdg_state

from core.observation.adapters.chat_adapter import record_chat_observation


def _resolve_full_cognitive_loop(runtime, requested: bool) -> bool:
    if requested:
        return True
    return bool(runtime.config.get("chat_default_full_cognitive_loop", False))


router = APIRouter(prefix="/chat", tags=["chat"])





class ChatRequest(BaseModel):

    message: str

    model_id: Optional[str] = None

    use_memory: bool = True

    temperature: float = Field(0.7, ge=0.0, le=2.0)

    stream: bool = False

    full_cognitive_loop: bool = False

    allow_proactive: bool = True





class ChatPrepareRequest(BaseModel):

    message: str

    model_id: Optional[str] = None

    use_memory: bool = True

    full_cognitive_loop: bool = False





class ChatPrepareResponse(BaseModel):

    prepare_id: str

    user_message: str

    memory_context: str

    governance_injection: str

    system_prompt: str

    outbound_preview: str

    has_injection: bool

    chat_governance_notes: List[Dict[str, Any]] = Field(default_factory=list)

    expires_in_seconds: int





class ChatConfirmRequest(BaseModel):

    prepare_id: str

    authorized: bool = True

    model_id: Optional[str] = None

    temperature: float = Field(0.7, ge=0.0, le=2.0)

    allow_proactive: bool = True

    full_cognitive_loop: bool = False

    send_mode: Literal["with_injection", "user_only"] = "with_injection"





class ChatResponse(BaseModel):

    reply: str

    model_id: str

    model_name: str

    requested_model_id: Optional[str] = None

    fallback_used: bool = False

    fallback_reason: Optional[str] = None

    coherence_score: Optional[float] = None

    meta_reflection: Optional[Dict[str, Any]] = None

    emotion_state: Optional[Dict[str, Any]] = None

    active_intent: Optional[str] = None

    value_alignment: Optional[Dict[str, Any]] = None

    proactive: Optional[Dict[str, Any]] = None

    latency_ms: float

    memory_capture: Optional[Dict[str, Any]] = None

    observation_meta: Optional[Dict[str, Any]] = None

    cognitive_loop: bool = True

    human_authorized: bool = False





class ChatCancelResponse(BaseModel):

    ok: bool

    cancelled: bool





def _resolve_profile(registry, model_id: Optional[str]):

    profile = registry.get(model_id) if model_id else registry.get_default()

    if not profile:

        raise HTTPException(400, "No model configured")

    fallback_used = False
    fallback_reason = None
    resolved = profile

    if profile.provider != "ollama" and not (profile.api_key or "").strip():

        fallback = registry.get("ollama-local")

        if fallback and fallback.enabled:
            fallback_used = True
            fallback_reason = "model_no_key"
            resolved = fallback

        if not fallback or not fallback.enabled:
            raise HTTPException(
                400,
                "云端模型 API Key 未配置或无效 — 请在「大模型 API」重新保存 Key，或先使用 Ollama 本地",
            )

    return resolved, fallback_used, fallback_reason





def _build_chat_response(
    *,
    result: Dict[str, Any],
    profile,
    req_message: str,
    use_memory: bool,
    pipeline: str,
    start: float,
    full_cognitive_loop: bool,
    human_authorized: bool,
    runtime,
    pre_state=None,
    requested_model_id: Optional[str] = None,
    fallback_used: bool = False,
    fallback_reason: Optional[str] = None,
) -> ChatResponse:

    reply = result.get("reply") or result.get("response", "")

    memory_context = result.get("context") or ""

    capture = {

        "pipeline": pipeline,

        "ok": result.get("ok", True),

        "capture_id": result.get("capture_id"),

        "assistant_capture_id": result.get("assistant_capture_id"),

        "chat_governance_notes": result.get("chat_governance_notes"),

        "intercepted": result.get("intercepted"),

        "llm_reply_pristine": result.get("llm_reply_pristine"),

        "cognition_deferred": result.get("cognition_deferred"),

        "human_authorized": human_authorized,

    }



    if not reply.strip():

        runtime_log("warn", "chat", "Empty LLM reply", model=profile.name, model_id=profile.id)

        raise HTTPException(

            502,

            "模型返回空回复 — 请确认已保存 API Key、模型可用，且账户有余额",

        )



    latency_ms = round((time.time() - start) * 1000, 2)

    observation_meta = record_chat_observation(

        runtime,

        message=req_message,

        use_memory=use_memory,

        memory_context_chars=len(memory_context),

        capture=capture,

        model_name=profile.name,

        pre_state=pre_state if pre_state is not None else (snapshot_cdg_state(runtime) if use_memory else None),

        pipeline=pipeline,

    )



    return ChatResponse(

        reply=reply,

        model_id=profile.id,

        model_name=profile.name,

        requested_model_id=requested_model_id,

        fallback_used=fallback_used,

        fallback_reason=fallback_reason,

        coherence_score=result.get("coherence_score"),

        meta_reflection=result.get("meta_reflection"),

        emotion_state=result.get("emotion_state"),

        active_intent=result.get("active_intent"),

        value_alignment=result.get("value_alignment"),

        proactive=result.get("proactive"),

        latency_ms=latency_ms,

        memory_capture=capture,

        observation_meta=observation_meta,

        cognitive_loop=full_cognitive_loop,

        human_authorized=human_authorized,

    )





@router.post("/prepare", response_model=ChatPrepareResponse)

async def chat_prepare(req: ChatPrepareRequest):

    runtime = get_runtime()
    full_loop = _resolve_full_cognitive_loop(runtime, req.full_cognitive_loop)

    runtime_log(

        "info",

        "chat",

        "Prepare outbound payload",

        preview=req.message[:80],

        use_memory=req.use_memory,

    )

    try:
        payload = await asyncio.to_thread(
            get_dispatcher().chat_prepare,
            message=req.message,
            use_memory=req.use_memory,
            chat_mode=True,
            metadata={"full_cognitive_loop": full_loop},
        )

    except ValueError as exc:

        raise HTTPException(400, str(exc)) from exc

    except Exception as exc:

        runtime_log("error", "chat", "Prepare failed", error=str(exc))

        raise HTTPException(502, str(exc)) from exc



    return ChatPrepareResponse(**payload)





@router.post("/confirm", response_model=ChatResponse)

async def chat_confirm(req: ChatConfirmRequest):

    runtime = get_runtime()

    registry = get_registry()



    if not req.authorized:

        get_dispatcher().chat_cancel(req.prepare_id)

        raise HTTPException(400, "发送已取消：未授权注入内容")



    profile, fallback_used, fallback_reason = _resolve_profile(registry, req.model_id)

    start = time.time()

    pre_state = snapshot_cdg_state(runtime)

    runtime_log(

        "info",

        "chat",

        "Authorized send",

        prepare_id=req.prepare_id[:12],

        model=profile.name,

    )



    try:
        result = await asyncio.to_thread(
            get_dispatcher().chat_confirm,
            req.prepare_id,
            temperature=req.temperature,
            llm_client=get_llm(),
            llm_profile=profile,
            allow_proactive=req.allow_proactive,
            send_mode=req.send_mode,
        )

    except ValueError as exc:

        raise HTTPException(400, str(exc)) from exc

    except Exception as exc:

        runtime_log("error", "chat", "Authorized send failed", error=str(exc))

        raise HTTPException(502, str(exc)) from exc



    user_message = result.get("user_input") or req.prepare_id

    response = _build_chat_response(
        result=result,
        profile=profile,
        req_message=str(result.get("user_message") or user_message),

        use_memory=True,

        pipeline="chat_confirm",

        start=start,

        full_cognitive_loop=bool(result.get("full_cognitive_loop") or _resolve_full_cognitive_loop(runtime, req.full_cognitive_loop)),

        human_authorized=True,

        runtime=runtime,

        pre_state=pre_state,

        requested_model_id=req.model_id,

        fallback_used=fallback_used,

        fallback_reason=fallback_reason,

    )

    runtime_log(

        "info",

        "chat",

        "Authorized reply sent",

        model=profile.name,

        reply_len=len(response.reply),

    )

    return response





@router.post("/cancel", response_model=ChatCancelResponse)

async def chat_cancel(req: ChatConfirmRequest):

    runtime = get_runtime()

    cancelled = get_dispatcher().chat_cancel(req.prepare_id)

    return ChatCancelResponse(ok=True, cancelled=cancelled)





@router.post("", response_model=ChatResponse)

async def chat(req: ChatRequest):

    """Legacy direct send — UI should use /prepare + /confirm for human authorization."""

    start = time.time()

    registry = get_registry()

    profile = _resolve_profile(registry, req.model_id)

    runtime = get_runtime()
    full_loop = _resolve_full_cognitive_loop(runtime, req.full_cognitive_loop)

    runtime_log(

        "info",

        "chat",

        "Incoming message",

        preview=req.message[:80],

        use_memory=req.use_memory,

        full_cognitive_loop=full_loop,

    )



    pre_state = snapshot_cdg_state(runtime) if req.use_memory else None

    pipeline = "process_interaction"



    try:
        result = await asyncio.to_thread(
            get_dispatcher().chat_send,
            message=req.message,
            use_memory=req.use_memory,
            temperature=req.temperature,
            llm_client=get_llm(),
            llm_profile=profile,
            allow_proactive=req.allow_proactive,
            chat_mode=True,
            metadata={"full_cognitive_loop": full_loop},
        )

    except Exception as exc:

        runtime_log("error", "chat", "Full cognitive loop failed", error=str(exc))

        raise HTTPException(502, str(exc)) from exc



    if not result.get("ok", True) and not result.get("chat_mode"):

        runtime_log(

            "warn",

            "chat",

            "Cognitive loop gated",

            reason=result.get("reason"),

            preview=(result.get("reply") or "")[:80],

        )



    response = _build_chat_response(

        result=result,

        profile=profile,

        req_message=req.message,

        use_memory=req.use_memory,

        pipeline=pipeline,

        start=start,

        full_cognitive_loop=bool(result.get("full_cognitive_loop") or _resolve_full_cognitive_loop(runtime, req.full_cognitive_loop)),

        human_authorized=False,

        runtime=runtime,

        pre_state=pre_state,

    )

    runtime_log(

        "info",

        "chat",

        "Reply sent",

        model=profile.name,

        reply_len=len(response.reply),

        pipeline=pipeline,

    )

    return response



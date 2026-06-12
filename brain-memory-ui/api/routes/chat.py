import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_llm, get_registry, get_runtime
from api.runtime_log import runtime_log
from core.governance.cdg import snapshot_cdg_state
from core.observation.adapters.chat_adapter import record_chat_observation

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    model_id: Optional[str] = None
    use_memory: bool = True
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    stream: bool = False
    full_cognitive_loop: bool = True
    allow_proactive: bool = True


class ChatResponse(BaseModel):
    reply: str
    model_id: str
    model_name: str
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


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.time()
    registry = get_registry()
    profile = registry.get(req.model_id) if req.model_id else registry.get_default()
    if not profile:
        raise HTTPException(400, "No model configured")

    runtime = get_runtime()
    runtime_log(
        "info",
        "chat",
        "Incoming message",
        preview=req.message[:80],
        use_memory=req.use_memory,
        full_cognitive_loop=req.full_cognitive_loop,
    )

    pre_state = snapshot_cdg_state(runtime) if req.use_memory else None
    memory_context = ""
    capture: Dict[str, Any] = {}
    pipeline = "process_interaction" if req.full_cognitive_loop else "chat_recall_llm_capture"

    if req.full_cognitive_loop:
        try:
            result = runtime.process_interaction(
                req.message,
                use_memory=req.use_memory,
                temperature=req.temperature,
                llm_client=get_llm(),
                llm_profile=profile,
                allow_proactive=req.allow_proactive,
            )
        except Exception as exc:
            runtime_log("error", "chat", "Full cognitive loop failed", error=str(exc))
            raise HTTPException(502, str(exc)) from exc

        reply = result.get("reply") or result.get("response", "")
        memory_context = result.get("context") or ""
        coherence_score = result.get("coherence_score")
        meta_reflection = result.get("meta_reflection")
        emotion_state = result.get("emotion_state")
        active_intent = result.get("active_intent")
        value_alignment = result.get("value_alignment")
        proactive = result.get("proactive")
        capture = {
            "pipeline": pipeline,
            "ok": result.get("ok", True),
            "capture_id": result.get("capture_id"),
        }
        if not result.get("ok", True):
            runtime_log(
                "warn",
                "chat",
                "Cognitive loop gated",
                reason=result.get("reason"),
                preview=reply[:80],
            )
    else:
        memory_context = runtime.recall(req.message) if req.use_memory else ""
        if req.use_memory:
            runtime_log(
                "debug",
                "recall",
                "Memory context assembled",
                query=req.message[:60],
                chars=len(memory_context),
            )

        system = "You are a long-lived AI powered by CNexus.\n"
        if memory_context:
            system += f"\n--- Persistent Memory ---\n{memory_context}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": req.message},
        ]

        try:
            reply = get_llm().chat(profile, messages, temperature=req.temperature)
        except Exception as exc:
            runtime_log("error", "chat", "LLM call failed", error=str(exc))
            raise HTTPException(502, str(exc)) from exc

        if req.use_memory:
            capture = {
                "pipeline": pipeline,
                "user": runtime.capture("user", req.message, importance=0.65),
                "assistant": runtime.capture("assistant", reply, importance=0.55),
            }
            runtime_log(
                "info",
                "capture",
                "Chat memories stored",
                user_id=str(capture.get("user"))[:20],
            )

        coherence_score = None
        meta_reflection = None
        emotion_state = None
        active_intent = None
        value_alignment = None
        proactive = None

    latency_ms = round((time.time() - start) * 1000, 2)
    runtime_log("info", "chat", "Reply sent", model=profile.name, reply_len=len(reply), pipeline=pipeline)

    observation_meta = record_chat_observation(
        runtime,
        message=req.message,
        use_memory=req.use_memory,
        memory_context_chars=len(memory_context),
        capture=capture,
        model_name=profile.name,
        pre_state=pre_state,
        pipeline=pipeline,
    )
    runtime_log("debug", "observation", "Chat turn recorded", stream=observation_meta.get("observation_stream"))

    return ChatResponse(
        reply=reply,
        model_id=profile.id,
        model_name=profile.name,
        coherence_score=coherence_score,
        meta_reflection=meta_reflection,
        emotion_state=emotion_state,
        active_intent=active_intent,
        value_alignment=value_alignment,
        proactive=proactive,
        latency_ms=latency_ms,
        memory_capture=capture,
        observation_meta=observation_meta,
        cognitive_loop=req.full_cognitive_loop,
    )

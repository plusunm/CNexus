"""OpenAI-compatible /v1 endpoints for external agent clients."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_legacy_adapter, get_llm, get_registry, get_skill_registry
from core.openai_compat.handler import create_chat_completion, list_model_cards
from core.openai_compat.models import ChatCompletionRequest, ChatCompletionResponse

router = APIRouter(prefix="/v1", tags=["openai-compatible"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    legacy_adapter=Depends(get_legacy_adapter),
    registry=Depends(get_registry),
    llm=Depends(get_llm),
    skills=Depends(get_skill_registry),
):
    try:
        return await create_chat_completion(
            request,
            runtime=legacy_adapter.runtime,
            registry=registry,
            llm_client=llm,
            skills=skills,
            legacy_adapter=legacy_adapter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/models")
async def list_models(registry=Depends(get_registry)):
    cards = list_model_cards()
    for profile in registry.list_public():
        cards.append(
            {
                "id": profile.id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": profile.provider,
            }
        )
    return {"object": "list", "data": cards}


@router.get("/skills")
async def list_skills(skills=Depends(get_skill_registry)):
    return {"object": "list", "data": skills.list_openai_tools()}

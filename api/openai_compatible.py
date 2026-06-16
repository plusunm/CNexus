"""Root-level OpenAI-compatible router (legacy api/server.py entry)."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

PROJECT_ROOT = Path(os.environ.get("BRAIN_MEMORY_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(PROJECT_ROOT))

from brain_memory import BrainMemoryRuntime  # noqa: E402
from core.model_registry import ModelRegistry  # noqa: E402
from core.openai_compat.handler import create_chat_completion, list_model_cards  # noqa: E402
from core.openai_compat.models import ChatCompletionRequest, ChatCompletionResponse  # noqa: E402
from core.skill.skill_registry import SkillRegistry, build_default_skill_registry  # noqa: E402

router = APIRouter(prefix="/v1", tags=["openai-compatible"])

_runtime: Optional[BrainMemoryRuntime] = None
_registry: Optional[ModelRegistry] = None
_skills: Optional[SkillRegistry] = None


def _get_runtime() -> BrainMemoryRuntime:
    global _runtime
    if _runtime is None:
        _runtime = BrainMemoryRuntime(project_root=str(PROJECT_ROOT))
    return _runtime


def _get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry(str(PROJECT_ROOT / "config"))
    return _registry


def _get_skills() -> SkillRegistry:
    global _skills
    if _skills is None:
        _skills = build_default_skill_registry(_get_runtime())
    return _skills


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    from core.control_plane.exceptions import ControlDecisionRejected

    try:
        from api.server import get_legacy_adapter

        legacy_adapter = get_legacy_adapter()
    except Exception:
        legacy_adapter = None
    try:
        return await create_chat_completion(
            request,
            runtime=_get_runtime(),
            registry=_get_registry(),
            llm_client=_get_runtime().llm_client,
            skills=_get_skills(),
            legacy_adapter=legacy_adapter,
        )
    except ControlDecisionRejected as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "control_plane_rejected", "reason": exc.decision.reason},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/models")
async def list_models():
    cards = list_model_cards()
    for profile in _get_registry().list_public():
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
async def list_skills():
    return {"object": "list", "data": _get_skills().list_openai_tools()}

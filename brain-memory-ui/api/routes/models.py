from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import get_registry, get_runtime, get_llm
from core.model_registry import ModelProfile, to_public

router = APIRouter(prefix="/models", tags=["models"])


class ModelCreate(BaseModel):
    name: str
    provider: str = "openai_compatible"
    base_url: str
    api_key: str = ""
    model: str
    is_default: bool = False


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None


@router.get("")
async def list_models():
    return {"models": get_registry().list_public()}


@router.post("")
async def create_model(req: ModelCreate):
    p = ModelProfile(
        name=req.name,
        provider=req.provider,  # type: ignore
        base_url=req.base_url,
        api_key=req.api_key,
        model=req.model,
        is_default=req.is_default,
    )
    return {"model": to_public(get_registry().add(p))}


@router.put("/{model_id}")
async def update_model(model_id: str, req: ModelUpdate):
    updated = get_registry().update(model_id, req.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(404, "Not found")
    return {"model": to_public(updated)}


@router.delete("/{model_id}")
async def delete_model(model_id: str):
    if not get_registry().delete(model_id):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.post("/{model_id}/test")
async def test_model(model_id: str):
    profile = get_registry().get(model_id)
    if not profile:
        raise HTTPException(404, "Not found")
    ok, detail = get_llm().test_connection(profile)
    return {"success": ok, "detail": detail}

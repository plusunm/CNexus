from fastapi import APIRouter, Query

from api.deps import get_runtime
router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/state")
async def current_state():
    return get_runtime().get_current_state()


@router.post("/cycle")
async def governance_cycle():
    return get_runtime().run_governance_cycle()


@router.post("/validate")
async def validate(days: int = Query(30, ge=1, le=365)):
    return get_runtime().run_validation_suite(days=days)

from fastapi import APIRouter, Query

from api.deps import get_runtime
from api.runtime_log import runtime_log

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/state")
async def current_state():
    return get_runtime().get_current_state()


@router.post("/cycle")
async def governance_cycle():
    runtime_log("info", "governance", "Running stability cycle")
    report = get_runtime().run_governance_cycle()
    score = report.get("stability_metrics", {}).get("overall_stability_score")
    runtime_log("info", "governance", "Cycle complete", stability=score)
    return report


@router.post("/validate")
async def validate(days: int = Query(30, ge=1, le=365)):
    return get_runtime().run_validation_suite(days=days)

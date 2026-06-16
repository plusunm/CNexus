from fastapi import APIRouter, Query

from api.deps import get_dispatcher
from api.runtime_log import runtime_log
from core.runtime.event_loop_offload import offload_sync

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/state")
async def current_state():
    return await offload_sync(lambda: get_dispatcher().observe_read("governance_state"), timeout_s=15.0)


@router.post("/cycle")
async def governance_cycle():
    runtime_log("info", "governance", "Running stability cycle")

    def _run():
        report = get_dispatcher().governance_cycle()
        score = report.get("stability_metrics", {}).get("overall_stability_score")
        runtime_log("info", "governance", "Cycle complete", stability=score)
        return report

    return await offload_sync(_run, timeout_s=60.0)


@router.get("/trajectory")
async def trajectory(last_n: int = Query(20, ge=1, le=256)):
    return await offload_sync(
        lambda: get_dispatcher().observe_read("cdg_trajectory", last_n=last_n),
        timeout_s=15.0,
    )


@router.post("/validate")
async def validate(days: int = Query(30, ge=1, le=365)):
    return await offload_sync(lambda: get_dispatcher().governance_validate(days=days), timeout_s=60.0)

import os
import sys
import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
# brain-memory-ui first for routes/deps; repo root for api.v1_endpoints namespace merge
sys.path.insert(0, str(ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.routes import (  # noqa: E402
    chat,
    cse,
    execution,
    governance,
    gtbs,
    ir,
    kernel,
    license,
    logs,
    memory,
    models,
    ollama,
    openai_compatible,
    reflective,
    runtime,
    spine,
)
from api.runtime_log import runtime_log  # noqa: E402
from api.websocket import router as ws_router  # noqa: E402
from api.v1_endpoints import configure_v1_dependencies, router as v1_spec_router  # noqa: E402
from api.ws_routes import configure_ws_dependencies, router as ws_v1_router  # noqa: E402
from api.deps import RuntimeNotReady, get_legacy_adapter, get_llm, get_registry, get_runtime, peek_runtime, start_cognitive_warmup_background, warm_runtime_background  # noqa: E402
from api.license_guard import ApiTokenMiddleware, verify_license_or_exit  # noqa: E402
from api.system_ready import mark_app_started  # noqa: E402

app = FastAPI(
    title="CNexus Runtime API",
    description="Decoupled API for CNexus UI (Web / Desktop / Mobile)",
    version="0.1.0-alpha",
)

origins = os.environ.get("BM_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CNexus-Token"],
)
app.add_middleware(ApiTokenMiddleware)


@app.exception_handler(RuntimeNotReady)
async def runtime_not_ready_handler(_request, _exc: RuntimeNotReady):
    from api.system_ready import system_ready_warming_payload

    payload = system_ready_warming_payload()
    return JSONResponse(status_code=503, content={"detail": payload})


try:
    from core.kernel.enforce.exceptions import KernelViolation

    @app.exception_handler(KernelViolation)
    async def kernel_violation_handler(_request, exc: KernelViolation):
        return JSONResponse(
            status_code=403,
            content={"detail": {"code": exc.code, "message": str(exc)}},
        )
except ImportError:
    pass


app.include_router(openai_compatible.router)
app.include_router(v1_spec_router, prefix="/v1")
app.include_router(license.router, prefix="/v1")
configure_v1_dependencies(
    get_runtime=get_runtime,
    get_llm=get_llm,
    get_registry=get_registry,
    get_legacy_adapter=get_legacy_adapter,
)
configure_ws_dependencies(
    get_runtime=get_runtime,
    get_llm=get_llm,
    get_registry=get_registry,
    get_legacy_adapter=get_legacy_adapter,
)
app.include_router(ws_v1_router)
app.include_router(reflective.router)
app.include_router(memory.router)
app.include_router(memory.router, prefix="/v1")
app.include_router(chat.router)
app.include_router(chat.router, prefix="/v1")
app.include_router(execution.router)
app.include_router(execution.router, prefix="/v1")
app.include_router(cse.router)
app.include_router(cse.router, prefix="/v1")
app.include_router(ir.router)
app.include_router(ir.router, prefix="/v1")
app.include_router(models.router)
app.include_router(ollama.router)
app.include_router(ollama.router, prefix="/v1")
app.include_router(governance.router)
app.include_router(gtbs.router)
app.include_router(gtbs.router, prefix="/v1")
app.include_router(runtime.router, prefix="/v1")
app.include_router(spine.router, prefix="/v1")
app.include_router(kernel.router, prefix="/v1")
app.include_router(logs.router)
app.include_router(ws_router)


@app.on_event("startup")
async def on_startup():
    verify_license_or_exit()
    mark_app_started()
    try:
        from core.runtime.conflict_monitor import conflict_log_path, log_conflict_event

        log_conflict_event(
            "MONITOR_STARTED",
            force=True,
            path=str(conflict_log_path()),
            deploy=os.environ.get("CNEXUS_DEPLOY_LEVEL", "dev"),
        )
    except Exception:
        pass
    from api.deps import peek_runtime
    from api.control_plane_workers import start_control_plane_workers
    from core.runtime.control_plane_kernel import configure_runtime_peek

    configure_runtime_peek(peek_runtime)
    from core.runtime.system_guard import enforce_non_hang_event_loop

    enforce_non_hang_event_loop(peek_runtime())
    # Isolation Kernel v1: startup only wires pointers — workers run in daemon threads.
    start_control_plane_workers(
        warm_runtime=warm_runtime_background,
        start_cognitive_warm=start_cognitive_warmup_background,
    )
    runtime_log(
        "info",
        "system",
        "CNexus API started (control plane isolation v1)",
        port=8000,
        deploy_level=os.environ.get("CNEXUS_DEPLOY_LEVEL", "dev"),
    )


@app.get("/debug/event_loop")
async def debug_event_loop():
    """Probe event loop responsiveness — must return in <50ms if loop is healthy."""
    from core.runtime.control_plane_isolation import probe_event_loop

    return probe_event_loop()


@app.post("/v1/system/warm_runtime")
async def trigger_runtime_warm(force: bool = False):
    """Explicitly start runtime warm thread (deferred boot path)."""
    from api.deps import can_retry_runtime_warm, peek_runtime, runtime_warm_meta, warm_runtime_background

    if peek_runtime() is not None:
        return {"ok": True, "detail": "runtime already loaded", "meta": runtime_warm_meta()}
    if not can_retry_runtime_warm(force=force):
        meta = runtime_warm_meta()
        return {
            "ok": False,
            "detail": "runtime warm throttled (cooldown or already warming)",
            "meta": meta,
        }
    warm_runtime_background(force=force)
    return {"ok": True, "detail": "runtime warm thread started", "meta": runtime_warm_meta()}


@app.get("/health")
async def health():
    from core.runtime.boot_protocol import boot_status
    from core.runtime.control_plane_isolation import get_cached_health, isolation_enabled

    from api.deps import peek_runtime, runtime_warm_meta

    runtime = peek_runtime()
    warm_meta = runtime_warm_meta()
    if isolation_enabled():
        cached = get_cached_health()
        return {
            "status": "ok",
            "service": "cnexus-ui-api",
            "memory": cached["memory_status"],
            "runtime_pointer": runtime is not None,
            "runtime_warm": warm_meta,
            "boot": boot_status(),
            "isolation": True,
        }

    from core.runtime.boot_protocol import fast_health_payload

    payload = fast_health_payload(runtime)
    payload["boot"] = boot_status()
    payload["service"] = "cnexus-ui-api"
    payload["runtime_warm"] = warm_meta
    return payload


if __name__ == "__main__":
    import uvicorn

    from api.port_guard import ensure_runtime_port_free, port_has_healthy_cnexus

    port = int(os.environ.get("BM_API_PORT", "8000"))
    if port_has_healthy_cnexus(port):
        print(f"[port-guard] CNexus API already healthy on :{port} — exiting without bind")
        raise SystemExit(0)
    ensure_runtime_port_free(port)
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)

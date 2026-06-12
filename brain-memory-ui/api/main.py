import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))

from api.routes import (  # noqa: E402
    chat,
    governance,
    logs,
    memory,
    models,
    openai_compatible,
    reflective,
)
from api.runtime_log import runtime_log  # noqa: E402
from api.websocket import router as ws_router  # noqa: E402

app = FastAPI(
    title="CNexus Runtime API",
    description="Decoupled API for CNexus UI (Web / Desktop / Mobile)",
    version="1.0.0",
)

origins = os.environ.get("BM_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(openai_compatible.router)
app.include_router(reflective.router)
app.include_router(memory.router)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(governance.router)
app.include_router(logs.router)
app.include_router(ws_router)


@app.on_event("startup")
async def on_startup():
    runtime_log("info", "system", "CNexus API started", port=8000, mode="g2")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cnexus-ui-api", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("BM_API_PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)

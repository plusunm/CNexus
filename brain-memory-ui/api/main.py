import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))

from api.routes import chat, governance, memory, models, reflective  # noqa: E402
from api.websocket import router as ws_router  # noqa: E402

app = FastAPI(
    title="Brain-Memory G1 Runtime API",
    description="Decoupled API for brain-memory-ui (Web / Desktop / Mobile)",
    version="1.0.0-g1",
)

origins = os.environ.get("BM_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reflective.router)
app.include_router(memory.router)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(governance.router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "brain-memory-ui-api", "version": "1.0.0-g1"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("BM_API_PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)

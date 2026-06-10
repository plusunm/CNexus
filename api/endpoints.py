"""FastAPI endpoints for CNexus (optional)."""

try:
    from fastapi import FastAPI
    from pydantic import BaseModel

    app = FastAPI(title="CNexus API")
    _runtime = None

    class CaptureRequest(BaseModel):
        role: str
        content: str
        layer: str = "episodic"
        importance: float = 0.5

    class RecallRequest(BaseModel):
        query: str
        top_k: int = 12

    def get_runtime():
        global _runtime
        if _runtime is None:
            from brain_memory import BrainMemoryRuntime
            _runtime = BrainMemoryRuntime()
        return _runtime

    @app.post("/capture")
    def capture(req: CaptureRequest):
        rt = get_runtime()
        return {"result": rt.capture(req.role, req.content, layer=req.layer, importance=req.importance)}

    @app.post("/recall")
    def recall(req: RecallRequest):
        rt = get_runtime()
        return {"context": rt.recall(req.query, top_k=req.top_k)}

    @app.post("/governance")
    def governance():
        rt = get_runtime()
        return rt.run_governance_cycle()

except ImportError:
    app = None

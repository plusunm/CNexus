"""FastAPI endpoints for CNexus (optional)."""

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    from core.control_plane.exceptions import ControlDecisionRejected
    from core.control_plane.legacy_adapter import LegacyDispatchAdapter

    app = FastAPI(title="CNexus API")
    _runtime = None
    _legacy_adapter = None

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

    def get_legacy_adapter() -> LegacyDispatchAdapter:
        global _legacy_adapter
        if _legacy_adapter is None:
            _legacy_adapter = LegacyDispatchAdapter.from_runtime(get_runtime())
        return _legacy_adapter

    @app.post("/capture")
    def capture(req: CaptureRequest):
        try:
            return {
                "result": get_legacy_adapter().capture(
                    role=req.role,
                    content=req.content,
                    layer=req.layer,
                    importance=req.importance,
                )
            }
        except ControlDecisionRejected as exc:
            raise HTTPException(403, exc.decision.reason) from exc

    @app.post("/recall")
    def recall(req: RecallRequest):
        try:
            return {
                "context": get_legacy_adapter().memory_recall(
                    query=req.query,
                    top_k=req.top_k,
                )
            }
        except ControlDecisionRejected as exc:
            raise HTTPException(403, exc.decision.reason) from exc

    @app.post("/governance")
    def governance():
        try:
            return get_legacy_adapter().governance_cycle()
        except ControlDecisionRejected as exc:
            raise HTTPException(403, exc.decision.reason) from exc

except ImportError:
    app = None

"""CNexus Runtime API contract tests — Product-facing REST/WS surface."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BMUI = os.path.join(ROOT, "brain-memory-ui")
# Repo root first — api.v1_endpoints lives under /api, not brain-memory-ui/api
sys.path.insert(0, BMUI)
sys.path.insert(0, ROOT)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


MIND_OVERVIEW_KEYS = {
    "schema_version",
    "generated_at",
    "cards",
    "feeds",
    "system",
    "chat_context",
    "memory_items",
}


def _sample_mind_overview() -> dict:
    return {
        "schema_version": "1.0.0-test",
        "generated_at": "2026-06-12T00:00:00Z",
        "cards": {
            "goal": {"title": "t", "progress": 0.1},
            "identity": {"summary": "s"},
            "belief": {"content": "b"},
            "focus": {"title": "f"},
        },
        "feeds": {"episodic": [], "reflections": [], "changes": []},
        "system": {
            "health_score": 0.9,
            "health_label": "OK",
            "memory_capacity_pct": 10,
            "governance_label": "stable",
            "last_update_ago": "now",
        },
        "chat_context": {"goal": "g", "belief": "b", "identity": "i"},
        "memory_items": [],
    }


def _assert_mind_overview(body: dict) -> None:
    missing = MIND_OVERVIEW_KEYS - set(body.keys())
    assert not missing, f"missing keys: {missing}"
    for card in ("goal", "identity", "belief", "focus"):
        assert card in body["cards"], f"cards.{card} missing"
    for feed in ("episodic", "reflections", "changes"):
        assert feed in body["feeds"], f"feeds.{feed} missing"
    ctx = body["chat_context"]
    assert ctx.get("goal") and ctx.get("belief") and ctx.get("identity")
    assert isinstance(body["memory_items"], list)


class TestCnexusRuntimeContract(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        os.environ["BM_MEMORY_DIR"] = self._tmpdir
        os.environ["BRAIN_MEMORY_ROOT"] = ROOT

        self.mock_runtime = MagicMock()
        overview = _sample_mind_overview()
        self.mock_runtime.get_current_state.return_value = {"mind_overview": overview}
        self.mock_runtime.capture.return_value = "mem-rc-1"
        self.mock_runtime.recall.return_value = "recalled context"
        self.mock_runtime.process_interaction.return_value = {
            "ok": True,
            "reply": "contract reply",
            "capture_id": "cap-1",
        }
        self.mock_runtime.config.get.side_effect = lambda key, default=None: default
        self.mock_runtime.process_capture_cognition.return_value = None

        from core.control_plane.dispatch import AuthorityDispatcher

        self.mock_dispatcher = AuthorityDispatcher(self.mock_runtime)

        mock_profile = MagicMock()
        mock_profile.id = "default"
        mock_profile.name = "Default"
        mock_registry = MagicMock()
        mock_registry.get_default.return_value = mock_profile
        mock_registry.get.return_value = mock_profile

        from api.v1_endpoints import configure_v1_dependencies, router as v1_router
        from api.routes.chat import router as chat_router
        from api.routes.memory import router as memory_router
        from api.websocket import router as ws_router

        self.app = FastAPI()
        self.app.include_router(v1_router, prefix="/v1")
        self.app.include_router(memory_router, prefix="/v1")
        self.app.include_router(chat_router)
        self.app.include_router(ws_router)
        configure_v1_dependencies(get_runtime=lambda: self.mock_runtime)

        @self.app.get("/health")
        async def health():
            return {"status": "ok", "service": "cnexus-ui-api", "version": "1.0.0"}

        self._patches = [
            patch("api.deps.get_runtime", return_value=self.mock_runtime),
            patch("api.deps.get_dispatcher", return_value=self.mock_dispatcher),
            patch("api.deps.get_registry", return_value=mock_registry),
            patch("api.deps.get_llm", return_value=MagicMock()),
            patch("api.routes.chat.get_runtime", return_value=self.mock_runtime),
            patch("api.routes.chat.get_dispatcher", return_value=self.mock_dispatcher),
            patch("api.routes.chat.get_registry", return_value=mock_registry),
            patch("api.routes.chat.get_llm", return_value=MagicMock()),
            patch("api.routes.memory.get_runtime", return_value=self.mock_runtime),
            patch("api.routes.memory.get_dispatcher", return_value=self.mock_dispatcher),
            patch("api.websocket.get_runtime", return_value=self.mock_runtime),
            patch("api.websocket.get_dispatcher", return_value=self.mock_dispatcher),
        ]
        import api.deps as deps_module

        deps_module._dispatcher = None
        for p in self._patches:
            p.start()
        deps_module._dispatcher = self.mock_dispatcher

        self.client = TestClient(self.app)

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()
        import api.deps as deps_module

        deps_module._dispatcher = None
        from api.v1_endpoints import configure_v1_dependencies

        configure_v1_dependencies(get_runtime=lambda: __import__("brain_memory").create_runtime())

    def test_health(self):
        resp = self.client.get("/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "ok")

    def test_system_ready(self):
        from api.system_ready import mark_app_started

        mark_app_started()
        runtime = __import__("brain_memory").create_runtime()
        with patch("api.deps.peek_runtime", return_value=runtime), patch(
            "api.system_ready.deep_health_payload",
            return_value={"status": "ready", "checks": {}},
        ):
            resp = self.client.get("/v1/system/ready")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("status"), "ready")
        self.assertEqual(body.get("ws"), "alive")
        self.assertIn("boot_id", body)
        self.assertTrue(body.get("token_valid"))

    def test_system_ready_warming(self):
        from api.system_ready import mark_app_started

        mark_app_started()
        with patch("api.deps.peek_runtime", return_value=None):
            resp = self.client.get("/v1/system/ready")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("status"), "warming")
        self.assertEqual(body.get("memory"), "warming")

    def test_v1_memory_capture(self):
        resp = self.client.post(
            "/v1/memory/capture",
            json={"role": "user", "content": "rc test", "layer": "episodic", "importance": 0.5},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("memory_id", resp.json())

    def test_v1_memory_recall(self):
        resp = self.client.get("/v1/memory/recall", params={"query": "hello"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("context"), "recalled context")
        self.mock_runtime.recall.assert_called_once()
        _, kwargs = self.mock_runtime.recall.call_args
        self.assertFalse(kwargs.get("mutate_state", True))

    def test_v1_mind_overview(self):
        resp = self.client.get("/v1/mind/overview")
        self.assertEqual(resp.status_code, 200)
        _assert_mind_overview(resp.json())

    def test_chat_post(self):
        with patch("api.routes.chat.snapshot_cdg_state", return_value=None), patch(
            "api.routes.chat.record_chat_observation", return_value={}
        ):
            resp = self.client.post("/chat", json={"message": "hello", "use_memory": False})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("reply", body)
        self.assertIn("latency_ms", body)

    def test_ws_state_first_frame(self):
        with self.client.websocket_connect("/ws/state") as ws:
            raw = ws.receive_text()
            state = json.loads(raw)
            self.assertIn("mind_overview", state)
            _assert_mind_overview(state["mind_overview"])


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BMUI = os.path.join(ROOT, "brain-memory-ui")
sys.path.insert(0, BMUI)
sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestIrApiRoutes(unittest.TestCase):
    def setUp(self):
        self.mock_runtime = MagicMock()
        self.mock_runtime.config = {"chat_recall_top_k": 4, "chat_max_context_chars": 4000}
        self.mock_runtime.recall_pipeline.recall.return_value = ""
        self.mock_runtime.recall_pipeline.last_explain = {}
        self.mock_runtime._build_chat_governance_injection.return_value = ""
        self.mock_runtime._compose_chat_llm_messages.return_value = ("sys", [])
        self.mock_runtime._format_chat_outbound_preview.return_value = "preview"

        from api.routes import ir as ir_routes

        app = FastAPI()
        app.include_router(ir_routes.router, prefix="/v1")
        self.client = TestClient(app)
        self.ir_routes = ir_routes

    @patch("api.routes.ir.get_runtime")
    def test_ir_templates(self, get_runtime):
        get_runtime.return_value = self.mock_runtime
        resp = self.client.get("/v1/ir/templates")
        self.assertEqual(resp.status_code, 200)
        names = resp.json()["templates"]
        self.assertIn("chat_single_turn", names)

    @patch("api.routes.ir.get_runtime")
    def test_ir_compile(self, get_runtime):
        get_runtime.return_value = self.mock_runtime
        resp = self.client.post(
            "/v1/ir/compile",
            json={"message": "hello", "template": "chat_single_turn", "use_memory": False},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["trace_id"].startswith("tr_"))
        self.assertEqual(body["template"], "chat_single_turn")
        self.assertIn("graph", body)


if __name__ == "__main__":
    unittest.main()

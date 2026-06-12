import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


class TestV1Endpoints(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.mock_runtime = MagicMock()

        from api.v1_endpoints import configure_v1_dependencies, router as v1_router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(v1_router, prefix="/v1")
        configure_v1_dependencies(get_runtime=lambda: self.mock_runtime)
        self.client = TestClient(app)

    def tearDown(self):
        from api.v1_endpoints import configure_v1_dependencies

        configure_v1_dependencies(get_runtime=lambda: __import__("brain_memory").create_runtime())

    def test_state_endpoint(self):
        self.mock_runtime.get_full_status.return_value = {
            "version": "1.0.0-g1",
            "layers": {
                "memory_blocks": {"total_active": 2, "by_label": {"persona": 1}},
                "governance": {"overall_stability": 0.9},
            },
        }
        self.mock_runtime.get_current_state.return_value = {"stability_metrics": {}}
        self.mock_runtime.memory_manager.block_stats.return_value = {"total_active": 2}
        self.mock_runtime.memory_manager.get_attention_snapshot.return_value = {
            "focus_scores": {"persona": 0.8},
        }

        resp = self.client.get("/v1/state?user_id=u1&session_id=s1")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["user_id"], "u1")
        self.assertEqual(body["blocks_summary"]["total_active"], 2)
        self.assertIn("persona", body["attention_state"]["focus_scores"])

    def test_memory_blocks_endpoint(self):
        block = MagicMock()
        block.block_id = "blk-1"
        block.label = "persona"
        block.description = "人格"
        block.content = "稳定自我"
        block.importance = 0.95
        block.version = 1
        block.category = "core"
        block.governance_status = "approved"
        block.updated_at.isoformat.return_value = "2026-06-12T00:00:00"
        self.mock_runtime.memory_manager.blocks.list_blocks.return_value = [block]
        self.mock_runtime.memory_manager.block_stats.return_value = {"total_active": 1}

        resp = self.client.get("/v1/memory/blocks")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["blocks"]), 1)
        self.assertEqual(body["blocks"][0]["label"], "persona")

    def test_interact_maps_process_interaction(self):
        self.mock_runtime.process_interaction.return_value = {
            "ok": True,
            "reply": "稳定、专注。",
            "context": "persona context",
            "capture_id": "cap-123",
            "coherence_score": 0.91,
            "emotion_state": {"primary_emotion": "calm"},
            "reflection": "情感连续性良好",
            "active_intent": "协助用户",
        }

        resp = self.client.post(
            "/v1/interact",
            json={
                "user_id": "user_123",
                "session_id": "sess_456",
                "message": "今天心情如何？",
                "options": {"use_memory": True},
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["response"], "稳定、专注。")
        self.assertTrue(body["governance_pass"])
        self.assertEqual(body["provenance_id"], "cap-123")
        self.assertIn("emotion", body["memory_blocks_updated"])

    def test_governance_check_endpoint(self):
        self.mock_runtime.run_governance_cycle.return_value = {
            "stability_metrics": {"overall_stability_score": 0.88},
        }
        self.mock_runtime.cdg.audit_log_path = "/tmp/audit.jsonl"

        resp = self.client.post("/v1/governance/check")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["governance_pass"])


if __name__ == "__main__":
    unittest.main()

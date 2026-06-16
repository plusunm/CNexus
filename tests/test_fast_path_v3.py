"""Fast-Path v3 — UI-driven predictive compute graph tests."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.system_ready import mark_app_started, system_ready_payload
from core.runtime.boot_protocol import BootPhase, mark_cognitive_warmup_done, set_boot_phase
from core.runtime.compute_plans import chat_compute_plan, status_compute_plan
from core.runtime.fast_path_v3 import fast_path_v3_enabled, should_use_ui_driven_ready
from core.runtime.frontend_compute_driver import FrontendComputeDriver, get_frontend_compute_driver
from core.runtime.predictive_compute_graph import PredictiveComputeGraph
from core.runtime.runtime_kernel import RuntimeKernel


class TestFastPathV3(unittest.TestCase):
    def test_v3_enabled_default(self):
        with patch.dict(os.environ, {"CNEXUS_FAST_PATH_V3": "1"}, clear=False):
            self.assertTrue(fast_path_v3_enabled())

    def test_should_use_ui_driven_default(self):
        with patch.dict(os.environ, {"CNEXUS_FAST_PATH_V3": "1"}, clear=False):
            self.assertTrue(should_use_ui_driven_ready(mode="default", runtime=None))
        self.assertFalse(should_use_ui_driven_ready(mode="full", runtime=None))

    def test_system_ready_unified_capability(self):
        mark_app_started()
        set_boot_phase(BootPhase.BOOT_4_READY)
        mark_cognitive_warmup_done()
        with patch.dict(
            os.environ,
            {"CNEXUS_FAST_PATH_V3": "1", "CNEXUS_FAST_PATH_V2": "1", "CNEXUS_FAST_PATH_V1": "1"},
            clear=False,
        ):
            payload = system_ready_payload(MagicMock(), mode="default")
        self.assertIn("capabilities", payload)
        self.assertIn("operational_ready", payload)
        self.assertIn("full_ready", payload)
        self.assertEqual(payload.get("render_mode"), "capability_v1")
        self.assertTrue(payload.get("full_ready"))

    def test_graph_register_and_execute(self):
        graph = PredictiveComputeGraph(MagicMock())

        async def plan(runtime, payload):
            return {"type": "test", "ok": True}

        graph.register_intent("test", plan)
        result = asyncio.run(graph.execute_from_ui("test", {}))
        self.assertEqual(result["type"], "test")
        result2 = asyncio.run(graph.execute_from_ui("missing", {}))
        self.assertEqual(result2["status"], "no_plan")

    def test_status_compute_plan(self):
        result = asyncio.run(status_compute_plan(MagicMock(), {"source": "test"}))
        self.assertEqual(result["type"], "status")
        self.assertIn("l3", result)
        self.assertIn("cluster", result)

    def test_chat_compute_plan(self):
        result = asyncio.run(chat_compute_plan(None, {"input": "hello"}))
        self.assertEqual(result["type"], "chat_result")
        self.assertIn("hello", str(result["data"]))

    def test_frontend_compute_driver(self):
        driver = get_frontend_compute_driver(MagicMock())
        result = asyncio.run(driver.on_user_event("status", {"source": "unit"}))
        self.assertEqual(result["type"], "status")

    def test_runtime_kernel_offload_named(self):
        kernel = RuntimeKernel(None)
        kernel.offload("crdt.merge_async")
        self.assertEqual(kernel.l3_queue_length(), 0)


if __name__ == "__main__":
    unittest.main()

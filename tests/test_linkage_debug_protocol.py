"""Linkage Debug Protocol v1 + Self-Healing Runtime Layer tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.boot_protocol import BootPhase, mark_runtime_spawned, set_boot_phase
from core.runtime.execution_trace import append_execution_trace, trace_stats
from core.runtime.linkage_debug import (
    build_linkage_debug_payload,
    collect_linkage_snapshot,
    resolve_diagnosis,
    resolve_root_cause,
)
from core.runtime.self_healing_runtime import (
    FaultClassifier,
    RepairPlanner,
    SelfHealingRuntimeLayer,
    configure_self_healing,
)


class TestLinkageDebugProtocol(unittest.TestCase):
    def setUp(self):
        set_boot_phase(BootPhase.BOOT_0_API)

    def test_boot_injection_failure_when_no_pointer(self):
        snapshot = collect_linkage_snapshot(app_started=True, peek_runtime=lambda: None)
        self.assertEqual(resolve_root_cause(snapshot), "BOOT_INJECTION_FAILURE")
        diagnosis = resolve_diagnosis(snapshot)
        self.assertEqual(diagnosis["status"], "BROKEN")
        self.assertEqual(diagnosis["layer"], "BOOT")

    def test_boot_in_progress_while_runtime_warming(self):
        snapshot = {
            "control": {"ok": True, "ready": "warming"},
            "runtime": {
                "pointer": False,
                "thread_alive": True,
                "runtime_warming": True,
            },
            "l3": {"required": False, "ticks": 0, "queue_length": 0},
            "event": {"no_flow": False},
        }
        self.assertEqual(resolve_root_cause(snapshot), "BOOT_IN_PROGRESS")

    def test_system_healthy_at_boot_4(self):
        mark_runtime_spawned()
        runtime = MagicMock()
        runtime.base_dir = tempfile.mkdtemp()
        snapshot = collect_linkage_snapshot(app_started=True, peek_runtime=lambda: runtime)
        snapshot["control"]["ready"] = "ready"
        self.assertEqual(resolve_root_cause(snapshot), "SYSTEM_HEALTHY")

    def test_trace_stats_detects_l3_ticks(self):
        base = tempfile.mkdtemp()
        append_execution_trace(
            base,
            {"type": "l3_tick", "ticks": 1, "remaining": 0, "executed": ["cdg_init"]},
        )
        stats = trace_stats(base)
        self.assertEqual(stats["l3_tick_count"], 1)
        self.assertTrue(stats["flow_active"])

    def test_payload_shape(self):
        payload = build_linkage_debug_payload(app_started=True, peek_runtime=lambda: None)
        self.assertIn("control", payload)
        self.assertIn("runtime", payload)
        self.assertIn("l3", payload)
        self.assertIn("cognition", payload)
        self.assertIn("event", payload)
        self.assertIn("diagnosis", payload)
        self.assertEqual(payload["schema_version"], "linkage-debug-v1")


class TestSelfHealingRuntime(unittest.TestCase):
    def test_planner_maps_l3_not_started(self):
        actions = RepairPlanner.plan("L3_HEARTBEAT_NOT_STARTED")
        self.assertEqual(actions, ["start_l3_tick_loop"])

    def test_runtime_init_failed_during_cooldown(self):
        snapshot = {
            "control": {"ok": True, "ready": "warming"},
            "runtime": {
                "pointer": False,
                "thread_alive": False,
                "runtime_warming": False,
                "init_error": "ValueError: EmbeddingService requires plane or scheduler",
                "warm_cooldown": True,
            },
            "l3": {"required": False, "ticks": 0, "queue_length": 0},
            "event": {"no_flow": False},
        }
        self.assertEqual(resolve_root_cause(snapshot), "RUNTIME_INIT_FAILED")
        actions = RepairPlanner.plan("RUNTIME_INIT_FAILED")
        self.assertEqual(actions, [])

    def test_healing_skips_reinject_when_init_failed_cooldown(self):
        calls: list[str] = []

        def handler(action: str) -> bool:
            calls.append(action)
            return True

        configure_self_healing(recovery_handler=handler)
        snapshot = {
            "control": {"ok": True, "ready": "warming"},
            "runtime": {
                "pointer": False,
                "thread_alive": False,
                "runtime_warming": False,
                "init_error": "ValueError: EmbeddingService requires plane or scheduler",
                "warm_cooldown": True,
            },
            "l3": {"required": False, "ticks": 0, "queue_length": 0},
            "event": {"no_flow": False},
        }
        result = SelfHealingRuntimeLayer().tick(snapshot)
        self.assertEqual(result["fault"], "RUNTIME_INIT_FAILED")
        self.assertEqual(calls, [])

    def test_classifier_healthy(self):
        snapshot = {
            "control": {"ok": True, "ready": "ready"},
            "runtime": {"pointer": True, "thread_alive": True, "runtime_warming": False, "stale": False},
            "l3": {"required": False, "ticks": 2, "queue_length": 0, "queue_stuck": False, "tick_latency_overload": False},
            "event": {"no_flow": False, "l3_tick_count": 2, "flow_active": True},
        }
        self.assertEqual(FaultClassifier.classify(snapshot), "HEALTHY")


class TestLinkageDebugEndpoint(unittest.TestCase):
    def test_linkage_debug_route(self):
        from api.v1_endpoints import configure_v1_dependencies, router as v1_router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(v1_router, prefix="/v1")
        configure_v1_dependencies(get_runtime=lambda: MagicMock())
        client = TestClient(app)

        resp = client.get("/v1/system/linkage_debug")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["schema_version"], "linkage-debug-v1")
        self.assertIn("diagnosis", body)


if __name__ == "__main__":
    unittest.main()

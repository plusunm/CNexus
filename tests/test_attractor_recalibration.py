"""L3-2 — Attractor recalibration delta clamp and Σ.S domain isolation."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evolved.cognitive_hooks import apply_attractor_recalibration_step
from core.governance.cdg.stability_monitor import RecalibrationSignal, StabilityMonitor
from core.personality.attractor.delta_constraint import clamp_scalar_step
from core.personality.attractor.recalibration_loop import (
    parse_recalibration_response,
    run_attractor_recalibration,
)
from core.runtime.l3_scheduler import L3GovernanceScheduler, L3TaskKind
from core.self_model import SelfModel, SelfModelStore
from core.self_model.domain_storage import DomainStorageAdapter


class TestAttractorDeltaConstraint(unittest.TestCase):
    def test_clamp_scalar_step_hard_cap(self) -> None:
        value, delta = clamp_scalar_step(0.5, 0.99, max_step=0.1)
        self.assertAlmostEqual(delta, 0.1)
        self.assertAlmostEqual(value, 0.6)

    def test_attractor_step_clamps_llm_overshoot(self) -> None:
        tmp = tempfile.mkdtemp()
        store = SelfModelStore(tmp)
        store.model.coherence_score = 0.5
        store.save_domain("cognize")

        raw = json.dumps({"coherence_delta": 0.5, "relational_patch": {"user": {"trust": 0.7}}})
        proposal = parse_recalibration_response(raw, current_coherence=0.5)
        result = apply_attractor_recalibration_step(store, **proposal)

        self.assertAlmostEqual(result["coherence_delta_applied"], 0.1)
        self.assertAlmostEqual(result["coherence_after"], 0.6)
        self.assertAlmostEqual(store.model.coherence_score, 0.6)

    def test_proposed_coherence_also_clamped(self) -> None:
        tmp = tempfile.mkdtemp()
        store = SelfModelStore(tmp)
        store.model.coherence_score = 0.4
        result = apply_attractor_recalibration_step(store, proposed_coherence=0.95)
        self.assertAlmostEqual(result["coherence_delta_applied"], 0.1)
        self.assertAlmostEqual(result["coherence_after"], 0.5)


class TestAttractorDomainIsolation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = SelfModelStore(self.tmp)
        self.adapter = DomainStorageAdapter(self.tmp)
        self.store.model.identity_summary = "长期身份锚点"
        self.store.model.core_beliefs = {"稳定性优先": 0.93}
        self.store.model.coherence_score = 0.55
        self.store.save()

    def test_only_cognize_mtime_changes(self) -> None:
        decide_path = self.adapter.domain_path("decide")
        meta_path = self.adapter.domain_path("store_meta")
        cognize_path = self.adapter.domain_path("cognize")
        decide_before = json.loads(decide_path.read_text(encoding="utf-8"))
        meta_before = json.loads(meta_path.read_text(encoding="utf-8"))
        decide_mtime = decide_path.stat().st_mtime
        meta_mtime = meta_path.stat().st_mtime
        time.sleep(0.05)

        signal = RecalibrationSignal(overall_stability_score=0.45, reason="test")
        run_attractor_recalibration(self.store, signal, base_dir=self.tmp)

        self.assertGreater(cognize_path.stat().st_mtime, decide_mtime)
        self.assertEqual(decide_path.stat().st_mtime, decide_mtime)
        self.assertEqual(meta_path.stat().st_mtime, meta_mtime)

        decide_after = json.loads(decide_path.read_text(encoding="utf-8"))
        meta_after = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual(decide_after, decide_before)
        self.assertEqual(meta_after, meta_before)
        self.assertEqual(decide_after["identity_summary"], "长期身份锚点")


class TestStabilityMonitorObserveBoundary(unittest.TestCase):
    def test_probe_uses_observe_read_only(self) -> None:
        monitor = StabilityMonitor(threshold=0.6, volatility_threshold=0.15)
        observe_read = MagicMock(
            return_value={"stability_metrics": {"overall_stability_score": 0.45}}
        )
        signal = monitor.probe(observe_read)
        self.assertIsNotNone(signal)
        observe_read.assert_called_once_with("governance_state")
        self.assertIn("below_threshold", signal.reason)  # type: ignore[union-attr]

    def test_volatility_triggers_signal(self) -> None:
        monitor = StabilityMonitor(threshold=0.3, volatility_threshold=0.12)
        observe_read = MagicMock(
            side_effect=[
                {"stability_metrics": {"overall_stability_score": 0.8}},
                {"stability_metrics": {"overall_stability_score": 0.65}},
            ]
        )
        self.assertIsNone(monitor.probe(observe_read))
        signal = monitor.probe(observe_read)
        self.assertIsNotNone(signal)
        self.assertIn("volatility", signal.reason)  # type: ignore[union-attr]

    def test_enqueue_runs_on_l3_scheduler(self) -> None:
        tmp = tempfile.mkdtemp()
        store = SelfModelStore(tmp)
        store.model.coherence_score = 0.5
        store.save_domain("cognize")

        runtime = MagicMock()
        runtime.base_dir = tmp
        runtime.self_model_store = store

        scheduler = L3GovernanceScheduler()
        monitor = StabilityMonitor(threshold=0.6)
        observe_read = MagicMock(
            return_value={"stability_metrics": {"overall_stability_score": 0.5}}
        )

        from core.runtime.attractor_background import enqueue_attractor_recalibration

        signal = monitor.probe(observe_read)
        self.assertIsNotNone(signal)
        enqueue_attractor_recalibration(runtime, signal, scheduler)  # type: ignore[arg-type]

        while scheduler.queue_length():
            scheduler.run_tick()

        self.assertGreater(store.model.coherence_score, 0.5)


if __name__ == "__main__":
    unittest.main()

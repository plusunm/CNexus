"""Goal Layer verification — capture integrity, governance observe, BeliefMeta boundary."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime
from core.goal.goal_manager import GoalManager
from core.personality.belief.belief_meta import (
    BeliefMeta,
    attach_meta_to_belief_payload,
    meta_write_allowed,
)
from core.personality.intent_engine import IntentEngine
from memory.manager import MemoryManager
from memory.runtime_guard import runtime_write_context


class TestGoalBlockIntegrity(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir)

    def test_double_goal_capture_preserves_structured_json(self):
        with runtime_write_context():
            self.runtime.capture(
                "user",
                "我的长期目标是构建稳定认知系统架构",
                layer="goal",
                importance=0.9,
            )
            self.runtime.capture(
                "user",
                "我还希望推进 IntentEngine 与 Goal Layer 验证",
                layer="goal",
                importance=0.85,
            )

        block = self.runtime.memory_manager.get_active_block("intent", touch=False)
        self.assertIsNotNone(block)
        self.assertTrue(str(block.content).strip().startswith("{"), block.content[:80])
        payload = json.loads(block.content)
        self.assertIn("active_goals", payload)
        self.assertGreaterEqual(len(payload["active_goals"]), 1)

        goals = self.runtime.goal_manager.active_goals(top_k=5)
        self.assertGreaterEqual(len(goals), 1)

    def test_goal_manager_mount_on_capture_syncs_narrative(self):
        with runtime_write_context():
            self.runtime.goal_manager.mount_on_capture(
                "user",
                "我的目标是维护身份连续性",
                "goal",
                0.88,
            )
        self.assertGreaterEqual(len(self.runtime.narrative.narrative.long_term_goals), 1)


class TestGoalGovernanceObserve(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir)

    def test_governance_cycle_records_goal_layer(self):
        with runtime_write_context():
            self.runtime.capture(
                "user",
                "长期目标：维护系统稳定性与连续性",
                layer="goal",
                importance=0.88,
            )
            report = self.runtime.run_governance_cycle()

        self.assertIn("goal_layer", report)
        goal_layer = report["goal_layer"]
        self.assertGreaterEqual(goal_layer.get("active_goal_count", 0), 1)
        self.assertTrue(goal_layer.get("reconciled") or goal_layer.get("projected"))
        self.assertIn("synthesis_generation", goal_layer)


class TestBeliefMetaBoundary(unittest.TestCase):
    def test_episodic_layers_reject_meta(self):
        self.assertFalse(meta_write_allowed(layer="episodic"))
        self.assertFalse(meta_write_allowed(layer="semantic"))
        self.assertFalse(meta_write_allowed(block_label="episodic_event"))

    def test_belief_store_accepts_meta(self):
        payload = {"beliefs": {}, "count": 0}
        meta = BeliefMeta(belief_id="b1", goal_id="g1", alignment_score=0.8, source="governance")
        enriched = attach_meta_to_belief_payload(payload, meta, block_label="belief_store")
        self.assertEqual(len(enriched["meta"]), 1)

    def test_episodic_attach_raises(self):
        meta = BeliefMeta(belief_id="b1", source="reflection")
        with self.assertRaises(ValueError):
            attach_meta_to_belief_payload(
                {"beliefs": {}},
                meta,
                layer="episodic",
                block_label="episodic_event",
            )


class TestGoalManagerUnit(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None, bypass_runtime_guard=True)
        self.engine = IntentEngine(self.manager)
        self.goals = GoalManager(self.engine)

    def test_observe_governance_without_values(self):
        with runtime_write_context():
            self.goals.mount_on_capture("user", "我的目标是完成 Goal Layer 验证", "goal", 0.8)
        snapshot = self.goals.observe_governance()
        self.assertGreaterEqual(snapshot["active_goal_count"], 1)


if __name__ == "__main__":
    unittest.main()

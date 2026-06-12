"""Goal Synthesis Layer — unify intent / narrative / working_self + BeliefMeta."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime
from core.goal.synthesis import GoalSynthesizer
from core.personality.belief.belief_meta import attach_meta_to_belief_payload, meta_write_allowed
from core.personality.intent_engine import Goal, GoalStatus, IntentEngine
from memory.manager import MemoryManager
from memory.runtime_guard import runtime_write_context


class TestGoalSynthesisUnifiesSources(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None, bypass_runtime_guard=True)
        self.intent = IntentEngine(self.manager)

        class _Narrative:
            def __init__(self):
                self.narrative = type("NS", (), {"long_term_goals": ["叙事层：维护连续性"]})()

        class _WorkingSelf:
            goal_focus = "identity"

        self.synth = GoalSynthesizer(
            self.intent,
            narrative_builder=_Narrative(),
            working_self=_WorkingSelf(),
        )

    def test_synthesize_merges_three_sources(self):
        with runtime_write_context():
            self.synth.ingest_capture(
                "user",
                "我的长期目标是构建稳定认知系统",
                "goal",
                0.9,
            )
            state = self.synth.synthesize()
            self.synth.project()

        descriptions = " ".join(g.description for g in state.canonical_goals)
        self.assertIn("稳定", descriptions)
        self.assertIn("连续性", descriptions)

        block = self.manager.get_active_block("intent", touch=False)
        payload = json.loads(block.content)
        self.assertGreaterEqual(
            int(payload.get("metadata", {}).get("synthesis_generation", 0)), 1
        )


class TestGoalSynthesisRuntime(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir)

    def test_capture_projects_working_self_and_narrative(self):
        with runtime_write_context():
            self.runtime.capture(
                "user",
                "长期目标：维护系统稳定性",
                layer="goal",
                importance=0.88,
            )
        self.assertIn("稳定", " ".join(self.runtime.narrative.narrative.long_term_goals))
        self.assertIn(self.runtime.working_self.goal_focus, {"goal", "identity"})

    def test_governance_reconcile_pauses_conflict(self):
        with runtime_write_context():
            self.runtime.capture(
                "user",
                "长期目标：维护系统稳定性与连续性",
                layer="goal",
                importance=0.9,
            )
            self.runtime.capture(
                "user",
                "短期目标：优先快速交付与效率",
                layer="goal",
                importance=0.85,
            )
            report = self.runtime.goal_manager.reconcile_governance(self.runtime.values_governance)

        self.assertTrue(report.get("reconciled"))
        active = self.runtime.goal_manager.active_goals(top_k=5)
        paused = [
            g
            for g in self.runtime.goal_manager.synthesizer.state.canonical_goals
            if g.status == GoalStatus.PAUSED
        ]
        self.assertTrue(active)
        self.assertGreaterEqual(len(paused), 1)


class TestBeliefMetaClosedLoop(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir)

    def test_belief_store_gets_meta_after_reconcile(self):
        with runtime_write_context():
            self.runtime.belief_engine.add_or_update_belief(
                "稳定性对认知系统至关重要", confidence=0.88
            )
            self.runtime.capture(
                "user",
                "长期目标：维护系统稳定性",
                layer="goal",
                importance=0.9,
            )
            self.runtime.goal_manager.reconcile_governance(self.runtime.values_governance)

        block = self.runtime.memory_manager.get_active_block("belief_store", touch=False)
        self.assertIsNotNone(block)
        payload = json.loads(block.content)
        self.assertGreaterEqual(len(payload.get("meta") or []), 1)

    def test_episodic_still_forbidden_for_meta(self):
        self.assertFalse(meta_write_allowed(layer="episodic", block_label="episodic_event"))


if __name__ == "__main__":
    unittest.main()

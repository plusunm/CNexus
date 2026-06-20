"""L4-3 — Reasoning trace injection, chunked streaming, and assumption_seed consistency."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.conscious_flow import (
    CandidateResponse,
    EvaluationReport,
    EvaluatedCandidate,
    SimulationBudget,
    SimulationEngine,
    build_reasoning_trace_from_report,
    build_stream_payload,
    iter_reasoning_enhanced_chunks,
)
from core.runtime.conscious_flow.reasoning_trace import (
    ReasoningTrace,
    format_reasoning_prompt_block,
    resolve_reasoning_trace_for_query,
)
from core.self_model import SelfModelStore
from core.self_model.domain_storage import DomainStorageAdapter


class TestReasoningTraceConsistency(unittest.TestCase):
    def test_assumption_seed_from_selected_branch(self) -> None:
        report = EvaluationReport(trace_id="sim-abc")
        report.kept = [
            EvaluatedCandidate(
                candidate=CandidateResponse(
                    branch_id="b0",
                    response_text="直接回应",
                    expected_stability_score=0.88,
                    assumption_seed="helpful_direct",
                ),
                eval_path="fast_track",
                final_score=0.88,
            ),
            EvaluatedCandidate(
                candidate=CandidateResponse(
                    branch_id="b1",
                    response_text="谨慎回应",
                    expected_stability_score=0.72,
                    assumption_seed="cautious_contextual",
                ),
                eval_path="reflective_pass",
                final_score=0.72,
            ),
        ]
        trace = build_reasoning_trace_from_report(report)
        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertEqual(trace.assumption_seed, "helpful_direct")
        self.assertEqual(trace.branch_id, "b0")
        self.assertEqual(trace.eval_path, "fast_track")

    def test_prompt_block_contains_seed(self) -> None:
        trace = ReasoningTrace(
            assumption_seed="reflective_deep",
            trace_id="sim-x",
            eval_path="reflective_pass",
            final_score=0.78,
            summary="深度反思路径",
        )
        block = format_reasoning_prompt_block(trace, verbose=True)
        self.assertIn("reflective_deep", block)
        self.assertIn("深度反思路径", block)


class TestChunkedResponse(unittest.TestCase):
    def test_stream_phases_reasoning_then_decision(self) -> None:
        trace = ReasoningTrace(
            assumption_seed="cautious_contextual",
            trace_id="sim-y",
            eval_path="fast_track",
            final_score=0.9,
            summary="结合上下文思考",
        )
        chunks = list(
            iter_reasoning_enhanced_chunks(
                reasoning_trace=trace,
                final_content="最终决定内容",
            )
        )
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].meta.phase, "reasoning")
        self.assertEqual(chunks[0].meta.reasoning_trace["assumption_seed"], "cautious_contextual")
        self.assertEqual(chunks[1].meta.phase, "decision")
        self.assertEqual(chunks[1].content, "最终决定内容")

    def test_build_stream_payload_shape(self) -> None:
        payload = build_stream_payload(
            reasoning_trace=ReasoningTrace(
                assumption_seed="helpful_direct",
                trace_id="t",
                eval_path="fast_track",
                final_score=0.91,
                summary="s",
            ),
            final_content="answer",
        )
        self.assertEqual(payload[0]["meta"]["phase"], "reasoning")
        self.assertIn("reasoning_trace", payload[0]["meta"])
        self.assertEqual(payload[1]["meta"]["phase"], "decision")


class TestRecallPipelineInjection(unittest.TestCase):
    def test_recall_includes_reasoning_trace_in_explain(self) -> None:
        os.environ["CNEXUS_REASONING_TRACE"] = "1"
        tmp = tempfile.mkdtemp()
        store = SelfModelStore(tmp)
        store.model.core_beliefs = {"稳定性优先": 0.93}
        store.save()

        runtime = MagicMock()
        runtime.base_dir = tmp
        runtime.self_model_store = store
        runtime.recall_top_k = 3
        runtime.runtime_mode = "legacy"
        runtime.memory_manager = None
        runtime.router = MagicMock(hybrid_recall=lambda q, top_k: [])
        runtime.context_engine = MagicMock(assemble=lambda *a, **k: "ctx")
        runtime.emotion_engine = MagicMock(format_context_block=lambda: "")
        runtime.intent_engine = MagicMock(format_context_block=lambda: "")
        runtime.reflective_engine = MagicMock(format_context_block=lambda limit=2: "")
        runtime.values_governance = MagicMock(format_context_block=lambda limit=2: "")
        runtime.narrative = MagicMock(
            generate_identity_anchor=lambda: "anchor",
            get_current_narrative_summary=lambda: "summary",
        )
        runtime.self_model = store.model
        runtime.working_self = MagicMock(
            goal_focus="g",
            cumulative_coherence=0.8,
            prediction_error=0.1,
        )
        runtime.attention = MagicMock(focus_scores_by_label=lambda: {})
        runtime.goal_manager = MagicMock(motivation_boost=lambda: 0.0, active_goals=lambda top_k=1: [])

        from runtime.recall_pipeline import RecallPipeline

        pipeline = RecallPipeline(runtime)
        text = pipeline.recall("如何保持长期稳定？", use_attention=False)
        self.assertIn("Reasoning Trace", text)
        self.assertTrue(pipeline.last_explain.get("reasoning_trace_present"))
        seed = (pipeline.last_explain.get("reasoning_trace") or {}).get("assumption_seed")
        self.assertIn(seed, ("helpful_direct", "cautious_contextual", "reflective_deep"))


class TestReasoningTraceIsolation(unittest.TestCase):
    def test_resolve_trace_does_not_touch_decide(self) -> None:
        tmp = tempfile.mkdtemp()
        store = SelfModelStore(tmp)
        store.save()
        adapter = DomainStorageAdapter(tmp)
        decide_mtime = adapter.domain_path("decide").stat().st_mtime
        time.sleep(0.05)

        runtime = MagicMock()
        runtime.base_dir = tmp
        runtime.self_model_store = store

        trace = resolve_reasoning_trace_for_query(runtime, "测试查询")
        self.assertIsNotNone(trace)
        self.assertEqual(adapter.domain_path("decide").stat().st_mtime, decide_mtime)


if __name__ == "__main__":
    unittest.main()

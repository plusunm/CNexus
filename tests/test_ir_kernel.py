import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.pipeline import UnifiedGovernanceDecision
from ir_kernel.adapters.runtime_facade import RuntimeFacade
from ir_kernel.compiler.registry import compile_template
from ir_kernel.engine import available_templates, compile_and_execute, compile_graph
from ir_kernel.runtime.executor import ExecContext
from ir_kernel.schema.graph import IRGraph, IRNode, IROp
from ir_kernel.verifier.graph_verifier import GraphVerifier


def _mock_runtime() -> MagicMock:
    rt = MagicMock()
    rt.config = {"chat_recall_top_k": 4, "chat_max_context_chars": 4000}
    rt.recall_pipeline.recall.return_value = "recalled context"
    rt.recall_pipeline.last_explain = {"top_labels": ["blk-1"]}
    rt._build_chat_governance_injection.return_value = ""
    rt._compose_chat_llm_messages.return_value = ("system", [{"role": "user", "content": "hi"}])
    rt._format_chat_outbound_preview.return_value = "outbound preview"
    rt._generate_llm_response.return_value = "mock assistant reply"
    rt.governance_pipeline.check_output.return_value = UnifiedGovernanceDecision(
        action="ALLOW",
        reason="ok",
    )
    rt.capture.return_value = "cap-mock"
    return rt


class TestIrKernel(unittest.TestCase):
    def test_available_templates(self):
        names = available_templates()
        self.assertIn("chat_single_turn", names)
        self.assertIn("cognitive_chat_full", names)

    def test_compile_graph_chat_template(self):
        graph, sigma = compile_graph("hello", template="chat_single_turn", use_memory=True)
        self.assertTrue(graph.graph_id.startswith("g_"))
        self.assertEqual(sigma.input["user_message"], "hello")
        self.assertTrue(sigma.trace_id.startswith("tr_"))
        self.assertEqual(len(graph.nodes), 7)

    def test_graph_verifier_accepts_v1_template(self):
        graph = compile_template("chat_single_turn", use_memory=True)
        result = GraphVerifier().verify_graph(graph)
        self.assertTrue(result.ok, msg=result.errors)

    def test_graph_verifier_rejects_cycle(self):
        graph = IRGraph(
            version="cnexus-ir-1.0",
            graph_id="g_cycle",
            template_name="bad",
            template_version="0",
            nodes={
                "a": IRNode("a", IROp.INPUT.value),
                "b": IRNode("b", IROp.FILTER.value),
            },
            edges=[("a", "b"), ("b", "a")],
        )
        result = GraphVerifier().verify_graph(graph)
        self.assertFalse(result.ok)
        self.assertIn("cycle_detected", result.errors)

    def test_execute_graph_with_mock_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BM_MEMORY_DIR"] = tmp
            rt = _mock_runtime()
            facade = RuntimeFacade(rt)
            ctx = ExecContext(use_memory=True, llm_client=MagicMock(), llm_profile=MagicMock())
            result = compile_and_execute(
                "user says hello",
                facade,
                template="chat_single_turn",
                use_memory=True,
                ctx=ctx,
                commit=False,
            )
            self.assertTrue(result.ok, msg=result.error)
            self.assertEqual(result.reply, "mock assistant reply")
            self.assertEqual(len(result.sigma_exec.get("steps") or []), 7)
            rt._generate_llm_response.assert_called_once()

    def test_cognitive_template_distinct_graph_id(self):
        chat = compile_template("chat_single_turn", use_memory=True)
        cognitive = compile_template("cognitive_chat_full", use_memory=True)
        self.assertNotEqual(chat.graph_id, cognitive.graph_id)
        self.assertEqual(cognitive.template_name, "cognitive_chat_full")


if __name__ == "__main__":
    unittest.main()

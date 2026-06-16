"""Learn Mode v2 interpreter tests."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.context import ExecutionContext
from core.kernel.intent import ExecutionIntent
from core.kernel.kernel import ExecutionKernel
from core.kernel.learn.interpreter import interpret_v2
from core.kernel.record import ExecutionRecord, LazyExecutionRecord
from core.runtime.execution_tap import reset_execution_tap


class TestLearnInterpreter(unittest.TestCase):
    def test_t0_fast_narrative(self):
        record = LazyExecutionRecord.materialize_lazy(
            intent=ExecutionIntent(type="chat", payload={"message": "hello"}),
            ctx=ExecutionContext(trace_id="t-learn-1"),
            result={"reply": "hi", "ok": True},
            tier="T0",
        )
        learn = interpret_v2(record)
        self.assertEqual(learn.execution_tier, "T0")
        self.assertEqual(learn.mode, "fast")
        self.assertIn("理解", learn.beginner_view)
        self.assertIn("极快", learn.why_it_feels_fast_or_slow)

    def test_t3_graph_steps(self):
        record = ExecutionRecord(
            trace_id="t-learn-2",
            intent_type="chat",
            result={"reply": "ok"},
            nodes=[
                {
                    "node_id": "n1",
                    "label": "recall_prefetch",
                    "intent": {"type": "recall", "payload": {"query": "q"}},
                },
                {
                    "node_id": "n2",
                    "label": "chat_send",
                    "intent": {"type": "chat", "payload": {"message": "q"}},
                },
            ],
            edges=[{"from_id": "n1", "to_id": "n2", "kind": "join"}],
            derivation={"execution_tier": "T3"},
            audit={"execution_tier": "T3"},
        )
        learn = interpret_v2(record)
        self.assertEqual(learn.mode, "deep")
        self.assertTrue(len(learn.reasoning_trace) >= 2)
        self.assertTrue(learn.memory_view)
        self.assertIn("记忆", learn.memory_view[0])

    def test_api_learn_endpoint(self):
        reset_execution_tap()
        os.environ["KERNEL_TAP_SYNC"] = "1"
        runtime = MagicMock()
        runtime.process_interaction.return_value = {"reply": "done"}
        kernel = ExecutionKernel(runtime)
        with unittest.mock.patch.dict(os.environ, {"USE_EXECUTION_GRAPH": "1", "KERNEL_ENFORCE_MODE": "0"}):
            record = kernel.execute(
                ExecutionIntent(type="chat", payload={"message": "test", "fast": True})
            )
        from core.kernel.observe.learn_view import read_learn_dict

        data = read_learn_dict(record.trace_id, kernel)
        self.assertEqual(data["version"], "learn-explanation-v2")
        self.assertEqual(data["trace_id"], record.trace_id)
        self.assertIn("beginner_view", data)
        os.environ.pop("KERNEL_TAP_SYNC", None)


if __name__ == "__main__":
    unittest.main()

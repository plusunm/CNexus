"""CP-2 soft commit gate tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.gtbs.exceptions import WriteIntentRejected
from core.governance.gtbs.soft_commit_gate import SoftCommitGate
from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.adapters.capture_adapter import build_capture_write_intent
from core.governance.gtbs.write_intent import MutabilityLevel, WriteProvenance
from core.governance.gtbs.write_intent_bus import WriteIntentBus
from memory.runtime_guard import runtime_write_context


class TestSoftCommitGate(unittest.TestCase):
    def test_explicit_requires_lineage(self):
        intent = build_capture_write_intent(
            role="user",
            content="x",
            layer="episodic",
            importance=0.5,
            emotional_weight=0.5,
        )
        verdict = SoftCommitGate.validate(intent)
        self.assertFalse(verdict.allowed)

    def test_explicit_ok_with_runtime_token(self):
        intent = build_capture_write_intent(
            role="user",
            content="x",
            layer="episodic",
            importance=0.5,
            emotional_weight=0.5,
            provenance=WriteProvenance(runtime_token="tok-1"),
        )
        self.assertTrue(SoftCommitGate.validate(intent).allowed)

    def test_bus_rejects_when_soft_gate_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = WriteIntentBus(GTBSTransactionLog(tmp))
            intent = build_capture_write_intent(
                role="user",
                content="x",
                layer="episodic",
                importance=0.5,
                emotional_weight=0.5,
            )
            config = {"gtbs": {"enable_write_intent_soft_gate": True}}
            with self.assertRaises(WriteIntentRejected):
                bus.emit(intent, config=config)
            rows = GTBSTransactionLog(tmp).read_all()
            self.assertEqual(rows[0]["event_type"], "rejection")

    def test_bus_allows_with_runtime_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = WriteIntentBus(GTBSTransactionLog(tmp))
            intent = build_capture_write_intent(
                role="user",
                content="x",
                layer="episodic",
                importance=0.5,
                emotional_weight=0.5,
            )
            config = {"gtbs": {"enable_write_intent_soft_gate": True}}
            with runtime_write_context(token="rt-1"):
                intent_id = bus.emit(intent, config=config)
            self.assertTrue(intent_id.startswith("prop-"))


if __name__ == "__main__":
    unittest.main()

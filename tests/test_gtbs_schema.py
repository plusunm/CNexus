"""GTBS v1.0 schema freeze tests — types only, no runtime wiring."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.governance.gtbs import (
    GTBS_STATUS,
    GTBS_VERSION,
    GovernanceProposal,
    GovernanceTransaction,
    OperationType,
    StateDelta,
    TransactionState,
)


class TestGTBSSchemaFreeze(unittest.TestCase):
    def test_version_constants(self):
        self.assertEqual(GTBS_VERSION, "1.0.0")
        self.assertEqual(GTBS_STATUS, "SCHEMA_FROZEN")

    def test_proposal_audit_event_shape(self):
        proposal = GovernanceProposal(
            operation_type=OperationType.INGEST,
            source="interaction",
            deltas=[
                StateDelta(
                    target_store="storage",
                    payload={"role": "user", "content": "hello"},
                    description="user capture",
                )
            ],
            justification={"source": "interaction", "risk_level": "low"},
        )
        event = proposal.to_audit_event()
        self.assertEqual(event["event_type"], "proposal")
        self.assertEqual(event["gtbs_version"], "1.0.0")
        self.assertEqual(event["operation_type"], "INGEST")
        self.assertEqual(event["target_stores"], ["storage"])

    def test_transaction_state_machine_records(self):
        proposal = GovernanceProposal(
            operation_type=OperationType.HOLD,
            deltas=[],
            justification={"source": "test"},
        )
        tx = GovernanceTransaction(proposal=proposal)
        self.assertEqual(tx.state, TransactionState.PROPOSED)

        tx.transition_to(TransactionState.APPROVED, {"by": "runtime"})
        self.assertEqual(tx.state, TransactionState.APPROVED)
        self.assertEqual(tx.approval["by"], "runtime")

        tx.transition_to(
            TransactionState.COMMITTED,
            {"executed_stores": ["storage"], "delta_applied": True},
        )
        self.assertEqual(tx.state, TransactionState.COMMITTED)
        self.assertIsNotNone(tx.commit_receipt)


if __name__ == "__main__":
    unittest.main()

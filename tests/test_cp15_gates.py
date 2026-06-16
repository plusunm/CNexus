"""CP-1.5 acceptance gates G1–G5 tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.gtbs.cp15_gates import run_cp15_gates


class TestCP15Gates(unittest.TestCase):
    def test_static_gates_pass_on_repo(self):
        report = run_cp15_gates()
        failed = [g for g in report.results if not g.passed]
        self.assertFalse(
            failed,
            msg=f"failed gates: {[f'{g.gate_id}: {g.detail}' for g in failed]}",
        )

    def test_g2_fails_when_lineage_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = os.path.join(tmp, "observability")
            os.makedirs(log_dir)
            log_path = os.path.join(log_dir, "gtbs_transactions.jsonl")
            with open(log_path, "w", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "event_type": "proposal",
                            "transaction_id": "prop-1",
                            "payload": {
                                "write_intent_kind": "capture",
                                "provenance": {},
                            },
                        }
                    )
                    + "\n"
                )
            report = run_cp15_gates(base_dir=tmp)
            g2 = next(r for r in report.results if r.gate_id == "G2")
            self.assertFalse(g2.passed)


if __name__ == "__main__":
    unittest.main()

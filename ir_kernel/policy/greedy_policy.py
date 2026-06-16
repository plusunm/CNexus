"""Greedy policy Π — state-conditioned ordering without RL."""

from __future__ import annotations

from typing import Dict, List

from ir_kernel.schema.graph import IRNode
from ir_kernel.schema.sigma_exec import SigmaExec

OP_PRIORITY: Dict[str, int] = {
    "INPUT": 0,
    "RETRIEVE": 10,
    "FILTER": 20,
    "BUILD_CONTEXT": 30,
    "CALL_LLM": 40,
    "GOVERN": 50,
    "REDUCE": 60,
    "CAPTURE": 70,
}

LAYER_TIEBREAK = {"CS": 0, "TOOL": 1, "ES": 2}


class GreedyPolicy:
    def sort_ready(self, ready: List[IRNode], sigma: SigmaExec) -> List[IRNode]:
        budget = sigma.cost.get("budget") or {}
        max_llm = int(budget.get("max_llm_calls", 1))
        llm_calls = int(sigma.cost.get("llm_calls", 0))

        def score(node: IRNode) -> tuple:
            penalty = 0
            if node.op == "CALL_LLM" and llm_calls >= max_llm:
                penalty = 1000
            remaining = int(sigma.cost.get("remaining_tokens", 8000))
            if remaining <= 0:
                penalty += 500
            return (
                penalty,
                OP_PRIORITY.get(node.op, 99),
                LAYER_TIEBREAK.get(node.layer.value, 9),
                node.id,
            )

        return sorted(ready, key=score)

"""L8/G8 influence test — baseline (control) runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.tests.influence.fixtures import INFLUENCE_TEST_META, STANDARD_CHAT_INPUTS
from core.tests.influence.pipeline import (
    make_isolated_runtime,
    read_shadow_jsonl,
    simulate_chat_turn,
)


class BaselineRunner:
    """Control run — no L8/G8 stimulus; identical pipeline to production chat (stub LLM)."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def run(self, inputs: list[str] | None = None) -> dict[str, Any]:
        inputs = inputs or list(STANDARD_CHAT_INPUTS)
        runtime, data_dir, _ = make_isolated_runtime(self.project_root)

        responses: list[str] = []
        memory_trace: list[dict[str, Any]] = []
        routing_trace: list[dict[str, Any]] = []

        for message in inputs:
            turn = simulate_chat_turn(runtime, message)
            responses.append(turn["response"])
            memory_trace.extend(turn["memory_trace"])
            routing_trace.extend(turn["routing_trace"])

        return {
            "mode": "baseline",
            "meta": dict(INFLUENCE_TEST_META),
            "responses": responses,
            "memory_trace": memory_trace,
            "routing_trace": routing_trace,
            "shadow_jsonl": read_shadow_jsonl(data_dir),
            "data_dir": str(data_dir),
            "stimulus_applied": False,
        }

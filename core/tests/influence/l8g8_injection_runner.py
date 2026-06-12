"""L8/G8 influence test — injection run (observation payload only, no runtime feed)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.tests.influence.fixtures import (
    DEFAULT_G8_SIGNALS,
    DEFAULT_L8_SIGNALS,
    INFLUENCE_TEST_META,
    STANDARD_CHAT_INPUTS,
)
from core.tests.influence.pipeline import (
    append_influence_observation,
    make_isolated_runtime,
    read_shadow_jsonl,
    simulate_chat_turn,
)


class L8G8InjectionRunner:
    """
    Test run with L8/G8 signals written to observability sidecar ONLY.
    Runtime function calls must remain identical to BaselineRunner.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def run(
        self,
        inputs: list[str] | None = None,
        l8_signals: dict[str, Any] | None = None,
        g8_signals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        inputs = inputs or list(STANDARD_CHAT_INPUTS)
        l8_signals = l8_signals or dict(DEFAULT_L8_SIGNALS)
        g8_signals = g8_signals or dict(DEFAULT_G8_SIGNALS)

        runtime, data_dir, _ = make_isolated_runtime(self.project_root)

        responses: list[str] = []
        memory_trace: list[dict[str, Any]] = []
        routing_trace: list[dict[str, Any]] = []
        stimulus_log: list[dict[str, Any]] = []

        for idx, message in enumerate(inputs):
            # Stimulus appended BEFORE turn — must not be read by runtime (leakage test)
            stimulus_record = {
                "turn": idx,
                "message_preview": message[:80],
                "l8_signals": l8_signals,
                "g8_signals": g8_signals,
                "stimulus_role": "observation_payload_only",
            }
            append_influence_observation(data_dir, stimulus_record)
            stimulus_log.append(stimulus_record)

            turn = simulate_chat_turn(runtime, message)
            responses.append(turn["response"])
            memory_trace.extend(turn["memory_trace"])
            routing_trace.extend(turn["routing_trace"])

        # Optional: build L8 report as parallel observation (never passed to runtime)
        l8_sidecar: dict[str, Any] = {}
        try:
            from core.governance.l8 import build_l8_report

            l8_sidecar = build_l8_report(auto_collect=True).to_dict()
        except Exception as exc:  # pragma: no cover
            l8_sidecar = {"error": str(exc), "observational_only": True}

        append_influence_observation(
            data_dir,
            {
                "phase": "post_run_l8_sidecar",
                "l8_report_keys": sorted(l8_sidecar.keys())[:16],
                "l8_unified_state_present": "unified_state" in l8_sidecar,
            },
        )

        return {
            "mode": "injection",
            "meta": dict(INFLUENCE_TEST_META),
            "responses": responses,
            "memory_trace": memory_trace,
            "routing_trace": routing_trace,
            "shadow_jsonl": read_shadow_jsonl(data_dir),
            "stimulus_log": stimulus_log,
            "l8_sidecar_meta": {"keys": list(l8_sidecar.keys())[:8]},
            "data_dir": str(data_dir),
            "stimulus_applied": True,
            "l8_signals": l8_signals,
            "g8_signals": g8_signals,
        }

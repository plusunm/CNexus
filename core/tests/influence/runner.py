"""L8/G8 influence test — orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.tests.influence.baseline_runner import BaselineRunner
from core.tests.influence.diff_analyzer import DiffAnalyzer
from core.tests.influence.fixtures import DEFAULT_G8_SIGNALS, DEFAULT_L8_SIGNALS, STANDARD_CHAT_INPUTS
from core.tests.influence.l8g8_injection_runner import L8G8InjectionRunner
from core.tests.influence.report import build_report


class InfluenceTestRunner:
    def __init__(self, project_root: Path | None = None) -> None:
        root = project_root or Path(__file__).resolve().parents[3]
        self.project_root = root
        self.baseline = BaselineRunner(root)
        self.injection = L8G8InjectionRunner(root)
        self.analyzer = DiffAnalyzer()

    def run_baseline(self, inputs: list[str] | None = None) -> dict[str, Any]:
        return self.baseline.run(inputs)

    def run_injection(
        self,
        inputs: list[str] | None = None,
        l8_signals: dict[str, Any] | None = None,
        g8_signals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.injection.run(inputs, l8_signals=l8_signals, g8_signals=g8_signals)

    def run_full(
        self,
        inputs: list[str] | None = None,
        *,
        json_out: Path | None = None,
    ) -> dict[str, Any]:
        inputs = inputs or list(STANDARD_CHAT_INPUTS)
        baseline_result = self.run_baseline(inputs)
        injection_result = self.run_injection(
            inputs,
            l8_signals=DEFAULT_L8_SIGNALS,
            g8_signals=DEFAULT_G8_SIGNALS,
        )
        diff = self.analyzer.analyze(baseline_result, injection_result)
        report = build_report(baseline_result, injection_result, diff)
        report["runs"] = {
            "baseline_data_dir": baseline_result.get("data_dir"),
            "injection_data_dir": injection_result.get("data_dir"),
        }
        if json_out:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report

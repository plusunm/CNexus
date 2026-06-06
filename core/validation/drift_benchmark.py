from typing import Dict


class DriftBenchmark:
    def __init__(self, runtime_components):
        self.runtime = runtime_components

    def run_benchmark(self) -> Dict:
        report = self.runtime.run_governance_cycle()
        drift = report["drift_report"]["drift_score"]
        return {"stability_score": max(0.5, 1.0 - drift), "drift_score": drift}

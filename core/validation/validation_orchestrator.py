from datetime import datetime
from typing import Dict
import uuid

from core.validation.drift_benchmark import DriftBenchmark
from core.validation.identity_regression import IdentityRegressionTest
from core.validation.long_term_simulator import LongTermSimulator
from core.validation.memory_corruption_test import MemoryCorruptionTest
from core.validation.narrative_coherence_scorer import NarrativeCoherenceScorer
from core.validation.observability_dashboard import ObservabilityDashboard
from core.validation.portability_evaluator import PortabilityEvaluator


class StabilityValidationOrchestrator:
    """Stability Validation Program 总控器"""

    def __init__(self, runtime_components):
        self.simulator = LongTermSimulator(runtime_components)
        self.drift_bench = DriftBenchmark(runtime_components)
        self.identity_test = IdentityRegressionTest(runtime_components)
        self.corruption_test = MemoryCorruptionTest(runtime_components)
        self.coherence_scorer = NarrativeCoherenceScorer(runtime_components)
        self.portability = PortabilityEvaluator(runtime_components)
        self.dashboard = ObservabilityDashboard()

    def run_full_validation_suite(self, simulation_days: int = 90) -> Dict:
        reports = {}

        reports["long_term_simulation"] = self.simulator.run_simulation(simulation_days)
        reports["drift_benchmark"] = self.drift_bench.run_benchmark()
        reports["identity_regression"] = self.identity_test.run_regression_test()
        reports["memory_corruption"] = self.corruption_test.run_corruption_test()
        reports["narrative_coherence"] = self.coherence_scorer.compute_coherence_score()
        reports["portability"] = self.portability.evaluate_portability()

        self.dashboard.generate_dashboard(reports)

        return {
            "validation_id": f"val_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now().isoformat(),
            "overall_stability_score": self._compute_overall_score(reports),
            "reports": reports,
            "status": "completed",
        }

    def _compute_overall_score(self, reports: Dict) -> float:
        scores = [
            reports.get("long_term_simulation", {}).get("overall_maturity_score", 0.7),
            reports.get("drift_benchmark", {}).get("stability_score", 0.8),
            reports.get("identity_regression", {}).get("pass_rate", 0.85),
            reports.get("narrative_coherence", {}).get("coherence_score", 0.8),
        ]
        return sum(scores) / len(scores)

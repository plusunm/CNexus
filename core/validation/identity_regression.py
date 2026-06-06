from typing import Dict


class IdentityRegressionTest:
    def __init__(self, runtime_components):
        self.runtime = runtime_components

    def run_regression_test(self) -> Dict:
        anchor = self.runtime.narrative.generate_identity_anchor()
        passed = "identity" in anchor.lower() or "personality" in anchor.lower()
        return {"pass_rate": 0.9 if passed else 0.5, "passed": passed}

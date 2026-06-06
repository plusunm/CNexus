from typing import Dict


class ObservabilityDashboard:
    def generate_dashboard(self, reports: Dict) -> Dict:
        return {
            "summary": {
                "overall": reports.get("long_term_simulation", {}).get("overall_maturity_score", 0.8),
                "tests_run": len(reports),
            },
            "reports": list(reports.keys()),
        }

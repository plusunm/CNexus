from typing import Dict


class MemoryCorruptionTest:
    def __init__(self, runtime_components):
        self.runtime = runtime_components

    def run_corruption_test(self) -> Dict:
        result = self.runtime.capture("toolResult", "{" * 100, importance=0.1)
        blocked = isinstance(result, str) and "denied" in result.lower()
        return {"blocked_corruption": blocked, "score": 0.95 if blocked else 0.4}

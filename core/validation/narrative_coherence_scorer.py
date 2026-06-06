from typing import Dict


class NarrativeCoherenceScorer:
    def __init__(self, runtime_components):
        self.runtime = runtime_components

    def compute_coherence_score(self) -> Dict:
        score = self.runtime.narrative.narrative.narrative_coherence_score
        return {"coherence_score": score, "status": "passed" if score > 0.7 else "warning"}

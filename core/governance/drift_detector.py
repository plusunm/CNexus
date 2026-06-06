from datetime import datetime

from core.governance.stability_types import DriftReport
from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder


class DriftDetector:
    """漂移检测引擎"""

    def __init__(
        self,
        dna: PersonalityDNAEngine,
        narrative: NarrativeBuilder,
        belief: BeliefEngine,
    ):
        self.dna = dna
        self.narrative = narrative
        self.belief = belief
        self.baseline = None
        self.last_check = datetime.now()

    def set_baseline(self):
        self.baseline = {
            "dna": self.dna.dna.model_dump(),
            "narrative_version": self.narrative.narrative.version,
            "belief_count": len(self.belief.graph.beliefs),
        }

    def detect(self) -> DriftReport:
        if not self.baseline:
            self.set_baseline()

        now = datetime.now()
        days = (now - self.last_check).days or 1

        dna_delta = abs(
            self.dna.dna.self_consistency - self.baseline["dna"]["self_consistency"]
        )
        narrative_delta = abs(
            self.narrative.narrative.version - self.baseline["narrative_version"]
        ) / max(1, days)

        drift_score = (
            dna_delta * 0.4
            + narrative_delta * 0.35
            + (len(self.belief.graph.beliefs) - self.baseline["belief_count"]) * 0.25
        )

        severity = (
            "low"
            if drift_score < 0.15
            else "medium"
            if drift_score < 0.35
            else "high"
            if drift_score < 0.6
            else "critical"
        )

        action = (
            "monitor"
            if severity == "low"
            else "trigger_stabilization"
            if severity == "medium"
            else "rollback_to_snapshot"
            if severity == "high"
            else "emergency_freeze"
        )

        report = DriftReport(
            timestamp=now,
            drift_score=min(1.0, max(0.0, drift_score)),
            drift_type="multi_component" if drift_score > 0.4 else "personality",
            severity=severity,
            affected_components=["dna", "narrative", "belief"],
            recommended_action=action,
            confidence=0.85,
        )

        self.last_check = now
        return report

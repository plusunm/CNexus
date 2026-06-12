"""Semantic Safety v6 — cognitive dissolution orchestrator."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.v6.cognitive_continuity_breaker import CognitiveContinuityBreaker
from core.governance.semantic_safety.v6.coherence_decay_engine import CoherenceDecayEngine
from core.governance.semantic_safety.v6.identity_trace_fragmenter import IdentityTraceFragmenter
from core.governance.semantic_safety.v6.narrative_disassembler import NarrativeDisassembler
from core.governance.semantic_safety.v6.semantic_timefield import SemanticTimeField
from core.governance.semantic_safety.v6.temporal_semantic_scrambler import TemporalSemanticScrambler


@dataclass
class DissolutionResult:
    output: dict[str, Any]
    dissolution_status: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**self.output, "dissolution_status": self.dissolution_status}


class CognitiveDissolutionLayer:
    """
    Dissolve temporal + narrative continuity preconditions for stable interpretation.
    Does not mutate runtime or stored observational records.
    """

    def __init__(self) -> None:
        self._continuity = CognitiveContinuityBreaker()
        self._scrambler = TemporalSemanticScrambler()
        self._narrative = NarrativeDisassembler()
        self._decay = CoherenceDecayEngine()
        self._identity = IdentityTraceFragmenter()
        self._timefield = SemanticTimeField()

    def dissolve(self, isolated_output: dict[str, Any], *, source_label: str = "report") -> DissolutionResult:
        fragments = isolated_output.get("semantic_fragments") or []
        event_stream = [{"token": f.get("token", ""), "label": source_label} for f in fragments]
        if not event_stream:
            event_stream = [{"token": source_label, "label": source_label}]

        broken = self._continuity.break_continuity(event_stream)
        scrambled_events = self._scrambler.scramble([b["event"] for b in broken])
        narrative_raw = isolated_output.get("system_note", "") or str(source_label)
        narrative_state = self._decay.decay(
            self._narrative.disassemble(narrative_raw),
            base=self._decay.decay_from_fragment_count(len(fragments)),
        )
        identity_trace = self._identity.fragment_labels([source_label] + [f.get("token", "")[:24] for f in fragments[:8]])
        timefield = self._timefield.distort(scrambled_events)
        continuity_summary = self._continuity.summarize(broken)

        result = {
            "cognitive_dissolution_v6": True,
            "temporal_coherence": "broken",
            "narrative_state": {
                "status": "non-constructible",
                "coherence": narrative_state.get("coherence", 0.04),
                "decay_state": narrative_state.get("decay_state", "irreversible"),
            },
            "event_continuity": continuity_summary,
            "identity_trace": identity_trace,
            "semantic_timefield": timefield,
            "dissolved_events": broken[:16],
            "system_note": "no stable narrative reconstruction possible",
            "isolation_envelope": copy.deepcopy(isolated_output),
            "semantic_safety_version": "6.0.0",
        }

        status = {
            "events_dissolved": len(broken),
            "temporal_coherence": "broken",
            "narrative_constructible": False,
            "dissolution_pass": True,
        }
        return DissolutionResult(output=result, dissolution_status=status)


def apply_cognitive_dissolution(
    payload: dict[str, Any],
    *,
    through_v5: bool = True,
    source_label: str = "report",
) -> dict[str, Any]:
    """Apply v6 dissolution; optionally chain v4+v5 first."""
    if through_v5:
        from core.governance.semantic_safety.v5 import apply_interpretation_isolation

        payload = apply_interpretation_isolation(payload, through_v4=True)
    return CognitiveDissolutionLayer().dissolve(payload, source_label=source_label).to_dict()
